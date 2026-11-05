"""
Interfaz Streamlit del agente PISA.

    streamlit run agente_pisa/app.py

Izquierda: chat con el agente IA (consume tokens de Groq).
Derecha: panel visual con el gráfico arriba y la explicación debajo. Sus vistas "Exploración manual"
y "Galería de gráficos" se calculan con Python puro (0 tokens); "Respuesta del agente" muestra el último resultado.
"""
import json
import re
import uuid

import altair as alt
import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage, ToolMessage

from agente import construir_agente, listar_modelos_groq
from config import (
    AVISO_2018, DIMENSIONES, LIMITE_RECURSION, NOMBRES_PAISES, PAISES_PANEL, PISA_YEARS, VENTANA_MENSAJES,
    resolver_imagen,
)
from datos import cargar_alumnos, cargar_catalogo_graficos, precargar_artefactos
from herramientas import media_ponderada

st.set_page_config(page_title="PISA", layout="wide")
with st.spinner("Cargando datos..."):
    precargar_artefactos()

VISTAS = ["Exploración manual", "Galería de gráficos", "Respuesta del agente"]
ESTRATOS_FIJOS = ["tipo_centro", "ubicacion", "tamano"]
COMPARABLES = ESTRATOS_FIJOS + ["nivel_compromiso", "nivel_recursos", "sexo", "origen"]
PLURALES = {"Público": "públicos", "Concertado": "concertados", "Privado": "privados", "Urbano": "urbanos",
            "Rural": "rurales", "Pequeño": "pequeños", "Mediano": "medianos", "Grande": "grandes"}
DESCRIPCION_TOOLS = {
    "get_math_stats": "Calculando medias por grupo",
    "calculate_correlation": "Calculando correlación",
    "get_context_chart": "Recuperando gráfico de contexto",
    "get_methodology": "Consultando la metodología",
    "get_regression_weights": "Consultando el modelo de regresión",
    "get_xgboost_patterns": "Consultando los patrones del XGBoost",
}


# ==========================================================
#  RECURSOS CACHEADOS
# ==========================================================
@st.cache_resource(show_spinner=False)
def obtener_agente():
    return construir_agente()


@st.cache_data(ttl=3600, show_spinner=False)
def modelos_disponibles() -> tuple[list[str], list[str]]:
    return listar_modelos_groq()


# ==========================================================
#  ESTADO DE SESIÓN
# ==========================================================
st.session_state.setdefault("thread_id", str(uuid.uuid4()))
st.session_state.setdefault("historial", [])        # [{"role", "content", "imagenes", "modelo"}]
st.session_state.setdefault("panel_agente", None)   # último resultado mostrado en el panel
st.session_state.setdefault("vista", "Exploración manual")
if "vista_pendiente" in st.session_state:           # cambio de vista solicitado antes del rerun
    st.session_state["vista"] = st.session_state.pop("vista_pendiente")


def mostrar_en_panel(mensaje: dict) -> None:
    st.session_state["panel_agente"] = mensaje
    st.session_state["vista_pendiente"] = "Respuesta del agente"


def nueva_conversacion() -> None:
    st.session_state["thread_id"] = str(uuid.uuid4())
    st.session_state["historial"] = []
    st.session_state["panel_agente"] = None


# ==========================================================
#  BARRA LATERAL: CONFIGURACIÓN Y CONTROLES MANUALES
# ==========================================================
alumnos = cargar_alumnos()

with st.sidebar:
    st.header("Agente IA")
    validados, otros = modelos_disponibles()
    if not validados:
        st.error("Ningún modelo verificado de Groq está activo. Revisa MODELOS_GROQ_PRIORIDAD en config.py.")
    principal = st.selectbox("Modelo principal", validados, help="Modelos activos en Groq verificados con Tool Calling.")
    cadena_modelos = [principal] + [m for m in validados if m != principal] if principal else []
    if len(cadena_modelos) > 1:
        st.caption(f"Respaldo automático ante límite de cuota: {', '.join(cadena_modelos[1:])}")
    st.button("Nueva conversación", on_click=nueva_conversacion, width="stretch")

    st.divider()
    st.header("Exploración manual")
    edicion = st.selectbox("Edición", ["Todas"] + PISA_YEARS, index=len(PISA_YEARS))
    pais = st.selectbox("País", ["Panel"] + PAISES_PANEL,
                        format_func=lambda c: "Panel de 12 países" if c == "Panel" else f"{NOMBRES_PAISES[c]} ({c})")
    comparar = st.selectbox("Comparar por", COMPARABLES, format_func=DIMENSIONES.get)
    filtros = {}
    for dimension in ESTRATOS_FIJOS:
        if dimension != comparar:
            opciones = list(alumnos[dimension].cat.categories)
            filtros[dimension] = st.multiselect(DIMENSIONES[dimension], opciones, placeholder="Todos")

    with st.expander("Cómo funciona"):
        st.markdown(
            "💡 **Exploración manual y galería sin coste:** los filtros de esta barra y la galería se calculan "
            "con Python sobre los datos ya preparados, sin llamar a Groq, para reservar la cuota gratuita al chat.\n\n"
            f"💡 **Memoria acotada:** el agente recibe solo los últimos {VENTANA_MENSAJES} mensajes de la "
            "conversación más sus instrucciones, lo que mantiene estable el consumo de tokens por pregunta.\n\n"
            "💡 **Ponderación:** las medias usan el peso de senado, que equivale al peso del alumno dentro de "
            "cada país y edición. En el panel cada país pesa casi lo mismo (entre el 6 y el 12 %), según cuántos "
            "de sus alumnos entran en el modelo, igual que en la regresión y el XGBoost."
        )


# ==========================================================
#  PANEL VISUAL (DERECHA)
# ==========================================================
def describir(dimension: str, categoria: str) -> str:
    """Grupo en lenguaje natural para la explicación de la exploración manual."""
    if dimension in ESTRATOS_FIJOS:
        return f"los centros {PLURALES[categoria]}"
    return {
        "nivel_compromiso": f"los alumnos con compromiso {categoria.lower()}",
        "nivel_recursos": f"los alumnos con {categoria.lower()} recursos de estudio",
        "sexo": "las chicas" if categoria == "Chica" else "los chicos",
        "origen": f"los alumnos {categoria.lower()}s" if categoria == "Nativo" else "los alumnos inmigrantes",
    }[dimension]


def filtrar_manual() -> pd.DataFrame:
    df = alumnos[alumnos["year"].isin(PISA_YEARS if edicion == "Todas" else [edicion])]
    if pais != "Panel":
        df = df[df["CNT"] == pais]
    for dimension, valores in filtros.items():
        if valores:
            df = df[df[dimension].isin(valores)]
    return df


def vista_exploracion_manual() -> None:
    df = filtrar_manual()
    if df.empty:
        st.info("No hay alumnos con esa combinación de filtros.")
        return
    peso_por_edicion = df.groupby("year")["SENWT"].sum()
    filas = [{"edicion": y, "grupo": str(c), "nota": round(media_ponderada(g, "nota"), 1),
              "pct_alumnos": round(100 * g["SENWT"].sum() / peso_por_edicion[y], 1), "alumnos": len(g)}
             for (y, c), g in df.groupby(["year", comparar], observed=True)]
    tabla = pd.DataFrame(filas)
    ambito = "el panel de 12 países" if pais == "Panel" else NOMBRES_PAISES[pais]
    eje_nota = alt.Y("nota:Q", title="Nota media en matemáticas", scale=alt.Scale(zero=False))
    orden = [str(c) for c in alumnos[comparar].cat.categories]

    if edicion == "Todas":
        grafico = alt.Chart(tabla).mark_line(point=True).encode(
            x=alt.X("edicion:O", title="Edición"), y=eje_nota,
            color=alt.Color("grupo:N", title=DIMENSIONES[comparar], sort=orden),
            tooltip=["edicion", "grupo", "nota", "pct_alumnos", "alumnos"])
    else:
        grafico = alt.Chart(tabla).mark_bar().encode(
            x=alt.X("grupo:N", title=DIMENSIONES[comparar], sort=orden), y=eje_nota,
            color=alt.Color("grupo:N", legend=None, sort=orden), tooltip=["grupo", "nota", "pct_alumnos", "alumnos"])
    st.altair_chart(grafico.properties(height=360), width="stretch")

    # Explicación generada con Python (0 tokens)
    ultima = tabla[tabla["edicion"] == tabla["edicion"].max()].sort_values("nota", ascending=False)
    if len(ultima) >= 2:
        mejor, peor = ultima.iloc[0], ultima.iloc[-1]
        st.markdown(
            f"En **{int(mejor['edicion'])}**, en {ambito}, {describir(comparar, mejor['grupo'])} obtienen la nota "
            f"media más alta en matemáticas (**{mejor['nota']:.0f}** puntos) y {describir(comparar, peor['grupo'])} "
            f"la más baja (**{peor['nota']:.0f}**): una diferencia de **{mejor['nota'] - peor['nota']:.0f}** puntos. "
            "Son diferencias descriptivas, sin controlar por el origen social de los alumnos."
        )
    if 2018 in tabla["edicion"].values:
        st.caption(AVISO_2018)
    if (tabla["alumnos"] < 30).any():
        st.caption("Algún grupo tiene menos de 30 alumnos: su media es poco fiable.")
    with st.expander("Ver datos"):
        st.dataframe(tabla, hide_index=True)


def vista_galeria() -> None:
    catalogo = cargar_catalogo_graficos()
    if catalogo.empty:
        st.info("Todavía no hay gráficos en la galería.")
        return
    descripcion = st.selectbox("Gráfico", catalogo["descripcion"].tolist())
    fila = catalogo[catalogo["descripcion"] == descripcion].iloc[0]
    st.image(str(resolver_imagen(fila["ruta"])), width="stretch")
    st.markdown(f"**{fila['descripcion']}**")
    st.caption("Gráficos del análisis exploratorio y del modelado. Los de la regresión están en puntos por desviación típica.")


def grafico_estadistica(datos: dict):
    """Gráfico Altair a partir de la salida JSON de get_math_stats (se dibuja en la app: 0 tokens)."""
    clave_grupo = next((k for k in datos if k.startswith("por_")), None)
    filas = []
    if clave_grupo == "por_edicion":
        filas = [{"edicion": int(y), "grupo": datos["ambito"], "valor": v} for y, v in datos[clave_grupo].items()]
    elif clave_grupo:
        for grupo, valor in datos[clave_grupo].items():
            media = valor["media"] if isinstance(valor, dict) and "media" in valor else valor
            if isinstance(media, dict):
                filas += [{"edicion": int(y), "grupo": grupo, "valor": v} for y, v in media.items()]
            else:
                filas.append({"grupo": grupo, "valor": media})
    elif isinstance(datos.get("media"), dict):
        filas = [{"edicion": int(y), "grupo": datos["ambito"], "valor": v} for y, v in datos["media"].items()]
    tabla = pd.DataFrame(filas).dropna(subset=["valor"]) if filas else pd.DataFrame()
    if tabla.empty:
        return None
    eje = alt.Y("valor:Q", title=datos["variable"], scale=alt.Scale(zero=False))
    if "edicion" in tabla:
        grafico = alt.Chart(tabla).mark_line(point=True).encode(
            x=alt.X("edicion:O", title="Edición"), y=eje, color=alt.Color("grupo:N", title=None),
            tooltip=["edicion", "grupo", "valor"])
    else:
        grafico = alt.Chart(tabla).mark_bar().encode(
            x=alt.X("grupo:N", title=None, sort="-y"), y=eje, color=alt.Color("grupo:N", legend=None),
            tooltip=["grupo", "valor"])
    filtros = ", ".join(datos.get("filtros", {}).values())
    titulo = f"{datos['variable']}: {datos['ambito']}, {datos['edicion']}" + (f" ({filtros})" if filtros else "")
    return grafico.properties(height=320, title=titulo)


def vista_respuesta_agente() -> None:
    panel = st.session_state["panel_agente"]
    if not panel:
        st.info("Pregunta al agente en el chat: sus gráficos y su explicación aparecerán aquí.")
        return
    for referencia in panel["imagenes"]:
        ruta = resolver_imagen(referencia)
        if ruta.exists():
            st.image(str(ruta), width="stretch")
    for datos in panel.get("estadisticas", []):
        grafico = grafico_estadistica(datos)
        if grafico is not None:
            st.altair_chart(grafico, width="stretch")
    st.markdown(panel["content"])
    if panel.get("modelo"):
        st.caption(f"Respuesta generada con {panel['modelo']}")


# ==========================================================
#  CHAT (IZQUIERDA)
# ==========================================================
def limpiar_texto(texto: str) -> str:
    """Quita imágenes Markdown/HTML y rutas de imagen que el modelo pudiera escribir pese a las instrucciones."""
    texto = re.sub(r"!\[.*?\]\([^)]*\)", "", texto)
    texto = re.sub(r"<img\s+[^>]*>", "", texto)
    texto = re.sub(r"\s*(?:como\s+)?[\"“«`']?(?:img|tmp)/[\w.-]+\.png[\"”»`']?", "", texto)   # «img/03_x.png»
    return texto.strip()


def imagenes_del_turno(mensajes: list) -> list[str]:
    """Referencias 'imagen' devueltas por las herramientas desde la última pregunta del usuario."""
    inicio = max(i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage))
    imagenes = []
    for mensaje in mensajes[inicio:]:
        if isinstance(mensaje, ToolMessage):
            try:
                referencia = json.loads(mensaje.content).get("imagen")
            except (json.JSONDecodeError, AttributeError):
                continue
            if referencia and referencia not in imagenes:
                imagenes.append(referencia)
    return imagenes


def estadisticas_del_turno(mensajes: list) -> list[dict]:
    """Salidas de get_math_stats desde la última pregunta del usuario, para dibujarlas en el panel."""
    inicio = max(i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage))
    salidas = []
    for mensaje in mensajes[inicio:]:
        if isinstance(mensaje, ToolMessage) and mensaje.name == "get_math_stats":
            try:
                datos = json.loads(mensaje.content)
            except json.JSONDecodeError:
                continue
            if "error" not in datos:
                salidas.append(datos)
    return salidas


def ejecutar_agente(pregunta: str, estado) -> dict:
    agente = obtener_agente()
    config = {"configurable": {"thread_id": st.session_state["thread_id"], "modelos": cadena_modelos},
              "recursion_limit": LIMITE_RECURSION}
    for evento in agente.stream({"messages": [("user", pregunta)]}, config=config, stream_mode="updates"):
        for mensaje in evento.get("asistente", {}).get("messages", []):
            for tool_call in getattr(mensaje, "tool_calls", None) or []:
                estado.write(DESCRIPCION_TOOLS.get(tool_call["name"], "Consultando datos"))
    mensajes = agente.get_state(config).values["messages"]
    final = mensajes[-1]
    return {"role": "assistant", "content": limpiar_texto(final.content or ""),
            "imagenes": imagenes_del_turno(mensajes), "estadisticas": estadisticas_del_turno(mensajes),
            "modelo": final.response_metadata.get("modelo_usado")}


# ==========================================================
#  MAQUETACIÓN
# ==========================================================
st.title("Estudio PISA")
st.caption(" PISA 2012-2022: exploración por estratos fijos y agente analítico")

col_chat, col_panel = st.columns([5, 7], gap="large")

with col_panel:
    vista = st.segmented_control("Vista", VISTAS, key="vista", label_visibility="collapsed") or VISTAS[0]
    {"Exploración manual": vista_exploracion_manual, "Galería de gráficos": vista_galeria,
     "Respuesta del agente": vista_respuesta_agente}[vista]()

with col_chat:
    st.subheader("Chat con el agente")
    historial = st.container(height=520)
    with historial:
        for i, mensaje in enumerate(st.session_state["historial"]):
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])
                if mensaje.get("imagenes") or mensaje.get("estadisticas"):
                    st.button("Ver gráfico en el panel", key=f"ver_{i}", on_click=mostrar_en_panel, args=(mensaje,))

    if pregunta := st.chat_input("Pregunta por centros, compromiso, recursos o países...", disabled=not cadena_modelos):
        st.session_state["historial"].append({"role": "user", "content": pregunta})
        with historial:
            with st.chat_message("user"):
                st.markdown(pregunta)
            with st.chat_message("assistant"):
                with st.status("Analizando la consulta...", expanded=False) as estado:
                    try:
                        respuesta = ejecutar_agente(pregunta, estado)
                        estado.update(label="Respuesta lista", state="complete")
                    except Exception as e:
                        estado.update(label="No se pudo completar la consulta", state="error")
                        respuesta = {"role": "assistant", "content": f"No se pudo completar la consulta: {e}",
                                     "imagenes": []}
        st.session_state["historial"].append(respuesta)
        if respuesta["imagenes"] or respuesta.get("modelo"):
            mostrar_en_panel(respuesta)
        st.rerun()
