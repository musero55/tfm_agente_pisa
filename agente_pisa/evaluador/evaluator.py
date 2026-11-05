"""
evaluator.py
============

Batería de evaluación del agente PISA. Cada caso de `reference_test.py` se pregunta al agente en un hilo nuevo y se
evalúa de tres formas:

    * herramientas: si llamó a las imprescindibles del caso (comprobación automática);
    * estilo: si la respuesta contiene tecnicismos que el System Prompt prohíbe (comprobación automática);
    * fidelidad, calidad y completitud: un LLM juez compara la respuesta con la referencia (`judge_prompt.md`).

Uso (desde `agente_pisa/` o desde el notebook `evaluator.ipynb`):

    from agente import construir_agente
    from evaluador import ejecutar_bateria_evaluacion, guardar_resultados, resumen_evaluacion
    resultados = ejecutar_bateria_evaluacion(construir_agente(), etiqueta="tras cambiar la nota de modelos")
    guardar_resultados(resultados)          # evaluador/resultados/evaluacion_<fecha>.csv
    resumen_evaluacion(resultados)

En LangSmith, cada caso deja una traza llamada «eval · <id del caso>» con las etiquetas «evaluacion» y el
identificador de la ejecución, y el juez otra llamada «juez · <id del caso>». Las puntuaciones solo están en la
tabla de resultados.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import groq
import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DIR_ACTUAL = Path(__file__).resolve().parent
if str(DIR_ACTUAL.parent) not in sys.path:
    sys.path.insert(0, str(DIR_ACTUAL.parent))   # para importar config aunque se ejecute desde evaluador/
from config import LIMITE_RECURSION, PAISES_PANEL  # noqa: E402

try:
    from .reference_test import CASOS_TEST_PISA   # import evaluador.evaluator (notebook)
except ImportError:
    from reference_test import CASOS_TEST_PISA    # ejecución desde la carpeta evaluador

__all__ = ["CASOS_TEST_PISA", "MODELO_JUEZ", "ejecutar_bateria_evaluacion", "guardar_resultados", "cargar_resultados",
           "resumen_evaluacion", "comparar_ejecuciones"]

RUTA_PROMPT_JUEZ = DIR_ACTUAL / "judge_prompt.md"
DIR_RESULTADOS = DIR_ACTUAL / "resultados"
# Juez de otra familia que el agente (gpt-oss), para que no se evalúe a sí mismo
MODELO_JUEZ = "qwen/qwen3.8-27b"
CRITERIOS = ["Tools OK", "Fidelidad OK", "Estilo Limpio"]
PUNTUACIONES = ["Calidad (1-5)", "Completitud (1-5)"]


class VeredictoJuez(BaseModel):
    """Salida estructurada del juez: así no devuelve texto libre que haya que interpretar."""
    sin_alucinaciones: bool = Field(
        description="True si las cifras y conclusiones coinciden con la referencia. False si inventa datos, "
                    "atribuye una cifra a otra edición, perfil o variable, o contradice una conclusión esperada."
    )
    puntuacion_calidad: int = Field(
        ge=1, le=5,
        description="Del 1 al 5: rigor y alineación con la referencia (1 = la contradice, 5 = perfectamente alineada).",
    )
    completitud: int = Field(
        ge=1, le=5,
        description="Del 1 al 5: si responde a todo lo que pregunta el usuario y recoge las conclusiones esperadas.",
    )
    motivo: str = Field(description="Justificación breve, en una frase, del veredicto.")


# ==========================================================
#  Comprobaciones automáticas
# ==========================================================
# Lo que el System Prompt prohíbe nombrar: nombres de variables, columnas, herramientas y claves JSON (todos con
# guion bajo), códigos de perfil (PUB_URB_MED) y de país (AUS), y siglas internas como el peso SENWT.
# Nombrar los modelos (regresión, XGBoost, SHAP) sí está permitido.
PATRON_GUION_BAJO = re.compile(r"\b[A-Za-z]+_[A-Za-z0-9_]+\b")
SIGLAS_PROHIBIDAS = ["SENWT", "HISEI", "PAREDINT", "HEDRES", "ESCS", *PAISES_PANEL]
PATRON_SIGLAS = re.compile(r"\b(" + "|".join(SIGLAS_PROHIBIDAS) + r")\b")   # en mayúsculas, como aparecen en los datos


def _tecnicismos(texto: str) -> list[str]:
    """Tecnicismos prohibidos que aparecen en `texto`, sin repetir y en el orden en que aparecen."""
    encontrados = PATRON_GUION_BAJO.findall(texto) + PATRON_SIGLAS.findall(texto)
    return list(dict.fromkeys(encontrados))


def _herramientas_usadas(mensajes: list) -> list[str]:
    """Nombres de las herramientas que llamó el agente, en orden y con repeticiones."""
    return [llamada["name"] for mensaje in mensajes if isinstance(mensaje, AIMessage) for llamada in (mensaje.tool_calls or [])]


def _modelos_usados(mensajes: list) -> tuple[list[str], bool]:
    """Modelos de Groq que generaron los mensajes del agente (`agente.invocar_con_respaldo` lo anota en cada uno) y
    si alguno fue el de respaldo."""
    metadatos = [mensaje.response_metadata for mensaje in mensajes if isinstance(mensaje, AIMessage)]
    modelos = list(dict.fromkeys(m.get("modelo_usado") for m in metadatos if m.get("modelo_usado")))
    return modelos, any(m.get("modelo_respaldo") for m in metadatos)


def _herramientas_ok(usadas: list[str], esperadas: list[str], minimo: int) -> bool:
    """Lista vacía de esperadas = no debe llamar a ninguna; si no, todas presentes y al menos `minimo` llamadas."""
    if not esperadas:
        return not usadas
    return all(herramienta in usadas for herramienta in esperadas) and len(usadas) >= minimo


# ==========================================================
#  Juez
# ==========================================================
PROMPT_JUEZ = RUTA_PROMPT_JUEZ.read_text(encoding="utf-8")


@retry(retry=retry_if_exception_type(groq.RateLimitError), wait=wait_exponential(multiplier=2, min=5, max=30),
       stop=stop_after_attempt(3), reraise=True)
def _juzgar(prompt: str, modelo_juez: str, config: dict) -> VeredictoJuez:
    """Veredicto del juez; ante un límite de cuota de Groq, espera y lo reintenta hasta tres veces."""
    juez = ChatGroq(temperature=0.0, model=modelo_juez, max_retries=0).with_structured_output(VeredictoJuez)
    return juez.invoke([HumanMessage(content=prompt)], config=config)


def _prompt_juez(caso: dict[str, Any], respuesta: str) -> str:
    referencia = caso["referencia"]
    return PROMPT_JUEZ.format(
        pregunta=caso["pregunta"],
        datos_clave="\n".join(f"- {dato}" for dato in referencia.get("datos_clave", [])),
        conclusiones_esperadas="\n".join(f"- {conclusion}" for conclusion in referencia.get("conclusiones_esperadas", [])),
        respuesta_agente=respuesta or "(respuesta vacía)",
    )


# ==========================================================
#  Evaluación de un caso y de la batería
# ==========================================================
def _evaluar_caso_estudio(agente, caso: dict[str, Any], modelo_juez: str, ejecucion: str) -> dict[str, Any]:
    """Pregunta el caso al agente en un hilo nuevo y lo evalúa. Si falla el agente, el caso queda como «ERROR»; si
    falla solo el juez, se conservan la respuesta y las comprobaciones automáticas."""
    test_id, categoria = caso["id"], caso.get("categoria", "General")
    esperadas = caso.get("herramientas_imprescindibles", [])
    minimo = caso.get("min_llamadas_herramienta", len(esperadas))
    metadatos = {"caso": test_id, "categoria": categoria, "ejecucion": ejecucion}
    fila = {"Ejecución": ejecucion, "ID": test_id, "Categoría": categoria, "Pregunta": caso["pregunta"],
            "Tools Esperadas": ", ".join(esperadas) or "Ninguna"}
    print(f" Ejecutando caso: {test_id} -> {caso['pregunta']}")

    # 1. El agente, en un hilo aislado y con su traza etiquetada en LangSmith
    inicio = time.time()
    config_agente = {"configurable": {"thread_id": f"eval_{test_id}_{int(inicio)}"}, "recursion_limit": LIMITE_RECURSION,
                     "run_name": f"eval · {test_id}", "tags": ["evaluacion", ejecucion], "metadata": metadatos}
    try:
        mensajes = agente.invoke({"messages": [("user", caso["pregunta"])]}, config=config_agente)["messages"]
    except Exception as error:
        return {**fila, "Tools OK": "ERROR", "Fidelidad OK": "ERROR", "Estilo Limpio": "ERROR", "Calidad (1-5)": None,
                "Completitud (1-5)": None, "Tiempo (s)": round(time.time() - inicio, 2), "Modelo": "", "Respaldo": False,
                "Tools Usadas": "", "Tecnicismos": "", "Dictamen Juez": f"Error del agente: {type(error).__name__}: {error}",
                "Respuesta Agente": ""}
    tiempo = round(time.time() - inicio, 2)
    respuesta = mensajes[-1].content if isinstance(mensajes[-1].content, str) else str(mensajes[-1].content)
    usadas = _herramientas_usadas(mensajes)
    modelos, respaldo = _modelos_usados(mensajes)
    tecnicismos = _tecnicismos(respuesta)
    fila.update({"Tools OK": "OK" if _herramientas_ok(usadas, esperadas, minimo) else "FALLO",
                 "Estilo Limpio": "OK" if not tecnicismos else "AVISO", "Tiempo (s)": tiempo,
                 "Modelo": ", ".join(modelos), "Respaldo": respaldo, "Tools Usadas": ", ".join(usadas) or "Ninguna",
                 "Tecnicismos": ", ".join(tecnicismos), "Respuesta Agente": respuesta})

    # 2. El juez, aparte: si falla, no se pierde la respuesta del agente
    config_juez = {"run_name": f"juez · {test_id}", "tags": ["evaluacion", "juez", ejecucion], "metadata": metadatos}
    try:
        veredicto = _juzgar(_prompt_juez(caso, respuesta), modelo_juez, config_juez)
        fila.update({"Fidelidad OK": "OK" if veredicto.sin_alucinaciones else "FALLO",
                     "Calidad (1-5)": veredicto.puntuacion_calidad, "Completitud (1-5)": veredicto.completitud,
                     "Dictamen Juez": veredicto.motivo})
    except Exception as error:
        fila.update({"Fidelidad OK": "ERROR", "Calidad (1-5)": None, "Completitud (1-5)": None,
                     "Dictamen Juez": f"Error del juez: {type(error).__name__}: {error}"})
    return fila


COLUMNAS = ["Ejecución", "Etiqueta", "ID", "Categoría", "Tools OK", "Fidelidad OK", "Estilo Limpio", "Calidad (1-5)",
            "Completitud (1-5)", "Tiempo (s)", "Modelo", "Respaldo", "Tools Esperadas", "Tools Usadas", "Tecnicismos",
            "Dictamen Juez", "Pregunta", "Respuesta Agente"]


def ejecutar_bateria_evaluacion(agente, casos: list[dict[str, Any]] = CASOS_TEST_PISA, modelo_juez: str = MODELO_JUEZ,
                                etiqueta: str = "", pausa_seg: float = 0.0) -> pd.DataFrame:
    """Evalúa `casos` (por defecto, todos los de `reference_test.py`) y devuelve una fila por caso. `etiqueta`
    describe la ejecución (por ejemplo, qué se cambió antes) para compararla con otras; `pausa_seg` espera entre
    casos si Groq limita la cuota."""
    ejecucion = datetime.now().strftime("%Y%m%d_%H%M%S")
    filas = []
    for posicion, caso in enumerate(casos):
        if posicion and pausa_seg:
            time.sleep(pausa_seg)
        filas.append(_evaluar_caso_estudio(agente, caso, modelo_juez, ejecucion))
    resultados = pd.DataFrame(filas).assign(Etiqueta=etiqueta)
    resultados[PUNTUACIONES] = resultados[PUNTUACIONES].astype("Float64")
    print(f"\nEvaluación {ejecucion} finalizada: {len(resultados)} casos.")
    return resultados[COLUMNAS]


# ==========================================================
#  Guardar, resumir y comparar ejecuciones
# ==========================================================
def guardar_resultados(resultados: pd.DataFrame, carpeta: Path = DIR_RESULTADOS) -> Path:
    """Guarda una ejecución en `carpeta/evaluacion_<ejecución>.csv` (UTF-8 con BOM, para abrirlo en Excel)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"evaluacion_{resultados['Ejecución'].iloc[0]}.csv"
    resultados.to_csv(ruta, index=False, encoding="utf-8-sig")
    return ruta


def cargar_resultados(carpeta: Path = DIR_RESULTADOS) -> pd.DataFrame:
    """Todas las ejecuciones guardadas en `carpeta`, de la más antigua a la más reciente."""
    rutas = sorted(Path(carpeta).glob("evaluacion_*.csv"))
    if not rutas:
        return pd.DataFrame(columns=COLUMNAS)
    historico = pd.concat([pd.read_csv(ruta, dtype={"Ejecución": str}, keep_default_na=False, na_values=[""])
                           for ruta in rutas], ignore_index=True)
    historico[PUNTUACIONES] = historico[PUNTUACIONES].astype("Float64")
    # Una columna de texto vacía en todo el CSV (por ejemplo, Tecnicismos) se leería como número
    texto = [columna for columna in COLUMNAS if columna not in PUNTUACIONES + ["Tiempo (s)", "Respaldo"]]
    historico[texto] = historico[texto].fillna("").astype(str)
    historico["Respaldo"] = historico["Respaldo"].astype(str).eq("True")
    return historico


def resumen_evaluacion(resultados: pd.DataFrame) -> pd.DataFrame:
    """Por categoría y en total: casos, porcentaje de OK en cada comprobación, puntuaciones medias del juez (sin
    los casos con error), casos respondidos por el modelo de respaldo y casos con error."""
    def resumir(grupo: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "Casos": len(grupo),
            **{f"% {criterio}": round(100 * (grupo[criterio] == "OK").mean(), 1) for criterio in CRITERIOS},
            **{f"Media {puntuacion}": round(grupo[puntuacion].mean(), 2) for puntuacion in PUNTUACIONES},
            "Con respaldo": int(grupo["Respaldo"].astype(bool).sum()),
            "Con error": int(grupo[CRITERIOS].eq("ERROR").any(axis=1).sum()),
        })
    por_categoria = resultados.groupby("Categoría").apply(resumir, include_groups=False)
    por_categoria.loc["Total"] = resumir(resultados)
    return por_categoria.astype({"Casos": int, "Con respaldo": int, "Con error": int})


def comparar_ejecuciones(historico: pd.DataFrame, anterior: str, actual: str) -> pd.DataFrame:
    """Caso a caso, las comprobaciones y puntuaciones de dos ejecuciones de `historico` (las de `cargar_resultados`)
    y si algo ha cambiado. Solo los casos que están en las dos."""
    columnas = CRITERIOS + PUNTUACIONES + ["Respaldo"]
    antes = historico[historico["Ejecución"] == anterior].set_index("ID")[columnas]
    despues = historico[historico["Ejecución"] == actual].set_index("ID")[columnas]
    comunes = antes.index.intersection(despues.index)
    comparacion = pd.concat({"Antes": antes.loc[comunes], "Después": despues.loc[comunes]}, axis=1).swaplevel(axis=1)
    comparacion = comparacion[[(columna, momento) for columna in columnas for momento in ("Antes", "Después")]]
    cambia = pd.Series(False, index=comunes)
    for columna in columnas:
        cambia |= antes.loc[comunes, columna].astype(str) != despues.loc[comunes, columna].astype(str)
    comparacion[("Cambia", "")] = cambia
    return comparacion
