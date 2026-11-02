"""
Carga de artefactos con la caché de Streamlit.

- st.cache_data: tablas (Parquet / CSV). Cada llamada devuelve una copia, así que las herramientas pueden modificarlas.

El agente no carga ningún modelo: de la etapa 2 solo lee sus resultados (SHAP por alumno, coeficientes y métricas).

Fuera de `streamlit run` (notebook, evaluador) los decoradores siguen funcionando con una caché en memoria.
"""
import pandas as pd
import streamlit as st

from config import (
    DIR_ARTEFACTOS, RUTA_ALUMNOS, RUTA_CATALOGO_GRAFICOS, RUTA_COEFICIENTES, RUTA_CONDUCTAS, RUTA_METRICAS, RUTA_SHAP,
)

# Evita los avisos "No runtime found" cuando se importa desde el notebook o el evaluador
if not st.runtime.exists():
    from streamlit import logger as st_logger
    st_logger.set_log_level("error")


def _comprobar(ruta):
    if not ruta.exists():
        raise FileNotFoundError(f"Falta el artefacto {ruta.name}. Ejecuta: python agente_pisa/preparar_artefactos.py")


@st.cache_data(show_spinner=False)
def cargar_alumnos() -> pd.DataFrame:
    """Alumnos que entran en el modelo, con la nota de matemáticas y las variables en unidades originales."""
    _comprobar(RUTA_ALUMNOS)
    return pd.read_parquet(RUTA_ALUMNOS)


@st.cache_data(show_spinner=False)
def cargar_catalogo_graficos() -> pd.DataFrame:
    """Catálogo de imágenes estáticas (ruta relativa a artefactos/), solo con las que existen en disco."""
    _comprobar(RUTA_CATALOGO_GRAFICOS)
    catalogo = pd.read_csv(RUTA_CATALOGO_GRAFICOS, keep_default_na=False)
    return catalogo[catalogo["ruta"].map(lambda r: (DIR_ARTEFACTOS / r).exists())].reset_index(drop=True)


# Los resultados del modelado pueden llegar por separado: cada herramienta de la etapa 2 se activa con el suyo
def regresion_disponible() -> bool:
    return RUTA_COEFICIENTES.exists()


def shap_disponible() -> bool:
    return RUTA_SHAP.exists()


def metricas_disponibles() -> bool:
    return RUTA_METRICAS.exists()


def conductas_disponibles() -> bool:
    return RUTA_CONDUCTAS.exists()


@st.cache_data(show_spinner=False)   # sin spinner: las herramientas se ejecutan en hilos sin contexto de Streamlit
def cargar_shap() -> pd.DataFrame:
    """SHAP del XGBoost de cada alumno (medio entre valores plausibles), con valor base y predicción."""
    _comprobar(RUTA_SHAP)
    return pd.read_parquet(RUTA_SHAP)


@st.cache_data(show_spinner=False)
def cargar_coeficientes() -> pd.DataFrame:
    """Coeficientes de la regresión por edición y especificación, combinados con las reglas de Rubin."""
    _comprobar(RUTA_COEFICIENTES)
    return pd.read_csv(RUTA_COEFICIENTES)


@st.cache_data(show_spinner=False)
def cargar_metricas() -> pd.DataFrame:
    """R², RMSE y MAE de la regresión y del XGBoost por edición."""
    _comprobar(RUTA_METRICAS)
    return pd.read_csv(RUTA_METRICAS)


@st.cache_data(show_spinner=False)
def cargar_conductas() -> pd.DataFrame:
    """Coeficiente de cada conducta del compromiso (faltar, llegar tarde, deberes) en 2012 y 2022."""
    _comprobar(RUTA_CONDUCTAS)
    return pd.read_csv(RUTA_CONDUCTAS)


def precargar_artefactos() -> None:
    """Llena las cachés desde el hilo principal antes de que el agente las use desde sus hilos de herramientas."""
    cargar_alumnos()
    cargar_catalogo_graficos()
    for disponible, cargar in [(regresion_disponible, cargar_coeficientes), (shap_disponible, cargar_shap),
                               (metricas_disponibles, cargar_metricas), (conductas_disponibles, cargar_conductas)]:
        if disponible():
            cargar()
