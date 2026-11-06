"""
Agente LangGraph del proyecto PISA (Groq + Tool Calling).

Lo importan app.py (Streamlit) y el evaluador.

    from agente import construir_agente, listar_modelos_groq
    agente = construir_agente()
    config = {"configurable": {"thread_id": "t1", "modelos": ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]},
              "recursion_limit": LIMITE_RECURSION}
    agente.invoke({"messages": [("user", "...")]}, config=config)
"""
import logging
import os
from functools import lru_cache
from typing import Annotated, TypedDict

import groq
from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import (
    DIR_AGENTE, MODELOS_GROQ_EXCLUIDOS, MODELOS_GROQ_PRIORIDAD, REINTENTOS_RATE_LIMIT, RUTA_SYSTEM_PROMPT, VENTANA_MENSAJES,
)
from herramientas import pisa_tools

logger = logging.getLogger("pisa.agente")

# El .env se carga al importar, antes de cualquier ejecución: LangSmith decide si traza al empezar la primera y guarda
# esa decisión, así que si LANGSMITH_TRACING llegara después, no se registraría nada en todo el proceso
load_dotenv(DIR_AGENTE / ".env")          # agente_pisa/.env aunque se lance desde la raíz del repo
load_dotenv(find_dotenv(usecwd=True))


#Carga de credenciales en el .env
def obtener_api_key() -> str:
    """Clave de Groq, leída de agente_pisa/.env (o de la variable de entorno GROQ_API_KEY)."""
    clave = os.getenv("GROQ_API_KEY")
    if not clave:
        raise ValueError("Falta GROQ_API_KEY: copia agente_pisa/.env.example como agente_pisa/.env y pon tu clave.")
    return clave


#Seleccion de modelos disponibles
def listar_modelos_groq() -> tuple[list[str], list[str]]:
    """
    Consulta client.models.list() y devuelve (validados, otros_activos):
      - validados: modelos de MODELOS_GROQ_PRIORIDAD que siguen activos, en orden de preferencia.
      - otros_activos: resto de modelos de texto activos (no verificados con Tool Calling).
    Si la consulta falla, devuelve la lista de prioridad sin verificar.
    """
    try:
        cliente = groq.Groq(api_key=obtener_api_key())
        activos = {m.id for m in cliente.models.list().data if getattr(m, "active", True)}
    except Exception as e:
        logger.warning("No se pudo consultar la lista de modelos de Groq (%s); se usa la lista de prioridad.", e)
        return list(MODELOS_GROQ_PRIORIDAD), []
    texto = {m for m in activos if not any(x in m.lower() for x in MODELOS_GROQ_EXCLUIDOS)}
    validados = [m for m in MODELOS_GROQ_PRIORIDAD if m in texto]
    otros = sorted(texto - set(validados))
    return validados, otros


@lru_cache(maxsize=None)
def _llm_con_herramientas(modelo: str):
    # max_retries=0: los reintentos los gestiona tenacity para poder saltar de modelo
    return ChatGroq(model=modelo, temperature=0.0, max_retries=0, api_key=obtener_api_key()).bind_tools(pisa_tools) #Asignamos las herramientas al LLM


@retry(
    retry=retry_if_exception_type(groq.RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(REINTENTOS_RATE_LIMIT),
    reraise=True,
)
def _invocar_con_reintentos(modelo: str, mensajes: list[BaseMessage]) -> AIMessage:
    return _llm_con_herramientas(modelo).invoke(mensajes)


def _error_saltable(error: Exception) -> bool:
    """Errores propios del modelo (cuota, retirado, fallo de tool calling) que justifican probar el siguiente."""
    if isinstance(error, (groq.RateLimitError, groq.NotFoundError, groq.InternalServerError, groq.APIConnectionError)):
        return True
    if isinstance(error, groq.BadRequestError):
        texto = str(error).lower()
        return any(x in texto for x in ("tool_use_failed", "decommissioned", "model_not_found", "does not support"))
    return False


def invocar_con_respaldo(mensajes: list[BaseMessage], modelos: list[str]) -> AIMessage:
    """Prueba los modelos en orden; ante un 429 persistente u otro error del modelo, salta al siguiente."""
    ultimo_error = None
    for modelo in modelos:
        try:
            respuesta = _invocar_con_reintentos(modelo, mensajes)
            respuesta.response_metadata["modelo_usado"] = modelo
            if modelo != modelos[0]:
                respuesta.response_metadata["modelo_respaldo"] = True
                logger.warning("Respuesta generada con el modelo de respaldo %s", modelo)
            return respuesta
        except Exception as e:
            if not _error_saltable(e):
                raise
            logger.warning("Modelo %s no disponible (%s): se prueba el siguiente.", modelo, type(e).__name__)
            ultimo_error = e
    raise RuntimeError(f"Ningún modelo de Groq disponible ahora mismo ({type(ultimo_error).__name__}). "
                       "Espera un minuto y vuelve a intentarlo.") from ultimo_error


#Configuración de la memoria del agente
def ventana_deslizante(mensajes: list[BaseMessage], n: int = VENTANA_MENSAJES) -> list[BaseMessage]:
    """
    Últimos n mensajes de conversación (preguntas y respuestas finales), empezando siempre por una pregunta
    del usuario, más los mensajes internos de herramientas del turno actual (que no cuentan en la ventana).
    Así nunca se separa un ToolMessage de la llamada que lo originó.
    """
    indices_humanos = [i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage)]
    if not indices_humanos:
        return mensajes[-n:]
    inicio_turno = indices_humanos[-1]
    previos = [m for m in mensajes[:inicio_turno]
               if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and not m.tool_calls and m.content)]
    ventana = (previos + [mensajes[inicio_turno]])[-n:]
    while not isinstance(ventana[0], HumanMessage):
        ventana = ventana[1:]
    return ventana + mensajes[inicio_turno + 1:]


#Grafo de la conexión del agente
class State(TypedDict):
    messages: Annotated[list, add_messages]


@lru_cache(maxsize=1)
def cargar_system_prompt() -> str:
    return RUTA_SYSTEM_PROMPT.read_text(encoding="utf-8")


def _registrar_uso(respuesta: AIMessage) -> None:
    uso = getattr(respuesta, "usage_metadata", None) or {}
    logger.info("[TOKENS %s] entrada=%s salida=%s total=%s", respuesta.response_metadata.get("modelo_usado"),
                uso.get("input_tokens", 0), uso.get("output_tokens", 0), uso.get("total_tokens", 0))
    for i, tc in enumerate(respuesta.tool_calls or [], start=1):
        logger.info("   [%s] %s %s", i, tc.get("name"), tc.get("args"))


def asistente(state: State, config: RunnableConfig):
    modelos = config.get("configurable", {}).get("modelos") or MODELOS_GROQ_PRIORIDAD
    mensajes = [SystemMessage(content=cargar_system_prompt())] + ventana_deslizante(state["messages"])
    respuesta = invocar_con_respaldo(mensajes, modelos)

    # Saneado defensivo: gpt-oss a veces filtra tokens de su canal de razonamiento en el nombre de la tool
    for tool_call in respuesta.tool_calls or []:
        if "<|" in tool_call["name"]:
            tool_call["name"] = tool_call["name"].split("<|")[0].strip()

    _registrar_uso(respuesta)
    return {"messages": [respuesta]}

#Construye las conexiones del agente a herramientas y nodos principales
def construir_agente():
    """Compila el grafo asistente <-> herramientas con memoria en RAM por thread_id."""
    workflow = StateGraph(State)
    workflow.add_node("asistente", asistente)
    workflow.add_node("tools", ToolNode(pisa_tools)) #Conexion a las herramientas
    workflow.add_edge(START, "asistente")
    workflow.add_conditional_edges("asistente", tools_condition)   # tools si hay tool_calls; si no, END
    workflow.add_edge("tools", "asistente")
    return workflow.compile(checkpointer=MemorySaver()) #Asignacion de la memoria -> Estado 
