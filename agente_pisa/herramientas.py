"""
Herramientas (Tool Calling) del agente PISA, organizadas en tres vías:

  a) Estadísticas descriptivas en vivo (Pandas sobre los alumnos del modelo, salida JSON compacta):
     get_math_stats, calculate_correlation
  b) Contexto estático (PNG pre-generados, sin cálculo):
     get_context_chart
  c) Resultados de los modelos (etapa 2, pendiente del modelado), sin cargar ningún modelo: coeficientes de la
     regresión (peso de cada variable y simulación lineal), SHAP del XGBoost por alumno (interacciones y
     diferencias por estrato) y métricas. Cada una se añadirá a `pisa_tools` cuando exista su tabla (datos.regresion_disponible(), etc.).

Todas las cifras son de matemáticas, la nota del alumno en este TFM, en los 12 países del panel común.
Las medias se ponderan con SENWT: dentro de un país y edición equivale al peso del alumno, y en el panel
da el mismo peso a cada país y edición.

Las herramientas que muestran una imagen devuelven su referencia en la clave "imagen" del JSON;
la app la recoge de los ToolMessage, por lo que el LLM no necesita repetirla en su respuesta.
"""
import difflib
import json
import unicodedata
from typing import Literal, Optional, Union

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from config import (
    AVISO_2018_CORTO, AVISO_POCO_REPRESENTATIVO, NOMBRES_PAISES, PAISES_PANEL, PISA_YEARS, VARIABLES_NUMERICAS, etiqueta,
)
from datos import cargar_alumnos, cargar_catalogo_graficos

# ==========================================================
#  NORMALIZADORES Y UTILIDADES
# ==========================================================

MINIMO_ALUMNOS = 30   # por debajo, el grupo se marca como "pocos datos"

# Sinónimos para que el usuario pueda preguntar de forma genérica ("privados", "rurales", "chicas"...)
SINONIMOS = {
    "tipo_centro": {
        "Público": ["publico", "publicos", "public", "estatal", "pub"],
        "Concertado": ["concertado", "concertados", "charter", "con", "privado concertado"],
        "Privado": ["privado", "privados", "private", "pri", "privado independiente"],
    },
    "ubicacion": {
        "Urbano": ["urbano", "urbanos", "urbana", "ciudad", "urban", "urb"],
        "Rural": ["rural", "rurales", "pueblo", "rur"],
    },
    "tamano": {
        "Pequeño": ["pequeno", "pequenos", "pequena", "small", "peq", "escuela pequena"],
        "Mediano": ["mediano", "medianos", "mediana", "medium", "med", "instituto mediano"],
        "Grande": ["grande", "grandes", "large", "macro", "macroinstituto", "macro-instituto"],
    },
    "nivel_compromiso": {
        "Bajo": ["bajo", "baja", "low", "poco"],
        "Medio": ["medio", "media", "medium", "intermedio"],
        "Alto": ["alto", "alta", "high", "mucho"],
    },
    "nivel_recursos": {
        "Hasta 4": ["hasta 4", "bajo", "bajos", "pocos", "low", "4"],
        "5 de 6": ["5 de 6", "medio", "medios", "5", "medium"],
        "Los 6": ["los 6", "alto", "altos", "todos", "completos", "6", "high", "all"],
    },
    "sexo": {
        "Chica": ["chica", "chicas", "mujer", "mujeres", "femenino", "girl", "girls", "female"],
        "Chico": ["chico", "chicos", "hombre", "hombres", "masculino", "boy", "boys", "male"],
    },
    "origen": {
        "Nativo": ["nativo", "nativos", "native", "autoctono"],
        "Inmigrante": ["inmigrante", "inmigrantes", "immigrant", "extranjero", "extranjeros"],
    },
}

# Nombres de los parámetros de la herramienta -> columna de alumnos_modelo
GRUPOS = {
    "tipo_centro": "tipo_centro", "ubicacion": "ubicacion", "tamano": "tamano", "compromiso": "nivel_compromiso",
    "recursos": "nivel_recursos", "sexo": "sexo", "origen": "origen", "pais": "CNT", "edicion": "year",
}

SINONIMOS_VARIABLES = {
    "nota": ["nota", "matematicas", "rendimiento", "puntuacion", "math", "score"],
    "Indice_Compromiso_Competencia": ["compromiso", "indice", "indice de compromiso", "competencia", "engagement"],
    "recursos_estudio": ["recursos", "recursos de estudio", "recursos estudio"],
    "riqueza_hogar": ["riqueza", "riqueza del hogar", "wealth"],
    "libros": ["libros", "libros en casa", "books"],
    "HISEI_TREND": ["hisei", "ocupacion", "ocupacion de los padres", "estatus"],
    "PAREDINT_TREND": ["paredint", "estudios de los padres", "estudios padres", "educacion padres"],
    "composicion_social_centro": ["composicion social", "composicion social del centro", "escs del centro"],
    "dotacion_centro": ["dotacion", "dotacion del centro", "recursos del centro"],
}


def _sin_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c)).replace("_", " ")


def _json(datos: dict) -> str:
    """Serializa la salida de una herramienta en JSON compacto (menos tokens que texto o tablas)."""
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=str)


def _r(valor, decimales: Optional[int] = None):
    """Redondea según la magnitud (menos dígitos = menos tokens) y convierte NaN en None para el JSON."""
    if valor is None or (isinstance(valor, (float, np.floating)) and np.isnan(valor)):
        return None
    if not isinstance(valor, (int, float, np.number)):
        return valor
    valor = float(valor)
    if decimales is None:
        decimales = 0 if abs(valor) >= 1000 else 1 if abs(valor) >= 10 else 2
    redondeado = round(valor, decimales)
    return int(redondeado) if decimales == 0 else redondeado


def _error(mensaje: str) -> str:
    return _json({"error": mensaje})


def _years(year) -> list[int]:
    """'all' -> todas las ediciones; un año -> lista con ese año (validado)."""
    if str(year).lower().strip() in ("all", "todos", "todas"):
        return PISA_YEARS
    y = int(year)
    if y not in PISA_YEARS:
        raise ValueError(f"El año '{year}' no es válido. Usa {PISA_YEARS} o 'all'.")
    return [y]


def normalizar_valor(columna: str, valor: Optional[str]) -> Optional[str]:
    """Traduce términos genéricos ('privados', 'rural', 'chicas'...) a la categoría de la columna."""
    if valor is None or _sin_acentos(valor) in ("", "none", "todos", "todas", "all", "cualquiera"):
        return None
    texto = _sin_acentos(valor)
    todos = {}
    for categoria, sinonimos in SINONIMOS[columna].items():
        for s in [_sin_acentos(categoria)] + sinonimos:
            todos[s] = categoria
    if texto in todos:
        return todos[texto]
    parecido = difflib.get_close_matches(texto, list(todos), n=1, cutoff=0.75)
    if parecido:
        return todos[parecido[0]]
    raise ValueError(f"Valor '{valor}' no reconocido para {etiqueta(columna)}. Usa: {', '.join(SINONIMOS[columna])}.")


def normalizar_pais(pais: Optional[str]) -> Optional[str]:
    """Código ISO del país a partir del código o del nombre; solo países del panel común."""
    if pais is None or _sin_acentos(pais) in ("", "none", "todos", "all", "panel", "ocde", "oecd"):
        return None
    texto = _sin_acentos(pais)
    if texto.upper() in PAISES_PANEL:
        return texto.upper()
    nombres = {_sin_acentos(nombre): iso for iso, nombre in NOMBRES_PAISES.items()}
    parecido = difflib.get_close_matches(texto, list(nombres), n=1, cutoff=0.75)
    if parecido:
        return nombres[parecido[0]]
    raise ValueError(f"'{pais}' no está en el panel de 12 países: {', '.join(PAISES_PANEL)}.")


def normalizar_variable(variable: str) -> str:
    """Columna numérica a partir de su nombre o de un sinónimo."""
    if variable in VARIABLES_NUMERICAS:
        return variable
    texto = _sin_acentos(variable)
    todos = {s: col for col, lista in SINONIMOS_VARIABLES.items() for s in lista}
    if texto in todos:
        return todos[texto]
    parecido = difflib.get_close_matches(texto, list(todos), n=1, cutoff=0.6)
    if parecido:
        return todos[parecido[0]]
    raise ValueError(f"Variable '{variable}' no disponible. Usa: {', '.join(SINONIMOS_VARIABLES)}.")


def media_ponderada(df: pd.DataFrame, columna: str) -> Optional[float]:
    """Media ponderada con SENWT ignorando los vacíos."""
    validos = df[columna].notna()
    pesos = df.loc[validos, "SENWT"]
    return float(np.average(df.loc[validos, columna], weights=pesos)) if pesos.sum() > 0 else None


def filtrar_alumnos(year="all", CNT: Optional[str] = None, **filtros) -> tuple[pd.DataFrame, dict, list[str]]:
    """Alumnos filtrados por edición, país y cualquier columna de SINONIMOS. Devuelve (datos, filtros, avisos)."""
    df = cargar_alumnos()
    years = _years(year)
    df = df[df["year"].isin(years)]
    aplicados = {}
    pais = normalizar_pais(CNT)
    if pais:
        df = df[df["CNT"] == pais]
        aplicados["pais"] = pais
    for columna, valor in filtros.items():
        categoria = normalizar_valor(columna, valor)
        if categoria:
            df = df[df[columna] == categoria]
            aplicados[columna] = categoria
    avisos = []
    if 2018 in years:
        avisos.append(AVISO_2018_CORTO)
    if df["perfil_poco_representativo"].any():
        avisos.append(AVISO_POCO_REPRESENTATIVO)
    return df, aplicados, avisos


# ==============================================================================
# a) ESTADÍSTICAS DESCRIPTIVAS EN VIVO
# ==============================================================================

@tool
def get_math_stats(
    year: Union[int, str] = 2022, CNT: Optional[str] = None, variable: str = "nota",
    tipo_centro: Optional[str] = None, ubicacion: Optional[str] = None, tamano: Optional[str] = None,
    compromiso: Optional[str] = None, recursos: Optional[str] = None, sexo: Optional[str] = None,
    origen: Optional[str] = None,
    group_by: Optional[Literal["tipo_centro", "ubicacion", "tamano", "compromiso", "recursos", "sexo", "origen",
                               "pais", "edicion"]] = None,
) -> str:
    """
    Weighted mean of a student variable (default 'nota' = math score) for any subgroup, optionally compared by group.
    - year: 2012, 2015, 2018, 2022 or 'all' (evolution by edition). CNT: ISO code or empty for the 12-country panel.
    - variable: 'nota', 'compromiso' (engagement index), 'recursos' (study resources), 'riqueza', 'libros',
      'ocupacion' or 'estudios padres' (parents), 'composicion social' or 'dotacion' (school).
    - Filters accept generic terms: tipo_centro publico|concertado|privado; ubicacion urbano|rural;
      tamano pequeño|mediano|grande (these three are the 'estratos fijos'); compromiso bajo|medio|alto;
      recursos bajo|medio|alto; sexo chica|chico; origen nativo|inmigrante.
    - group_by: compare categories (e.g. 'tipo_centro' public vs private, 'pais' for a country ranking).
    """
    try:
        columna = normalizar_variable(variable)
        df, aplicados, avisos = filtrar_alumnos(year, CNT, tipo_centro=tipo_centro, ubicacion=ubicacion,
                                                tamano=tamano, nivel_compromiso=compromiso, nivel_recursos=recursos,
                                                sexo=sexo, origen=origen)
        if df.empty:
            return _error("No hay alumnos con esos filtros.")

        varias_ediciones = df["year"].nunique() > 1 and group_by != "edicion"

        def resumen(bloque: pd.DataFrame):
            if varias_ediciones:
                return {int(y): _r(media_ponderada(g, columna)) for y, g in bloque.groupby("year")}
            return _r(media_ponderada(bloque, columna))

        salida = {"variable": etiqueta(columna), "ambito": aplicados.pop("pais", "panel de 12 países"),
                  "edicion": "2012-2022" if str(year).lower() in ("all", "todos", "todas") else int(year),
                  "filtros": aplicados, "n_alumnos": len(df), "media": resumen(df)}
        if group_by:
            col_grupo = GRUPOS[group_by]
            peso_total = df["SENWT"].sum()
            grupos, pocos = {}, []
            for categoria, g in df.groupby(col_grupo, observed=True):
                clave = int(categoria) if col_grupo == "year" else str(categoria)
                if col_grupo in ("CNT", "year"):   # cada país y edición pesa lo mismo: el % no aporta
                    grupos[clave] = resumen(g)
                else:
                    grupos[clave] = {"media": resumen(g), "pct": _r(100 * g["SENWT"].sum() / peso_total, 1)}
                if len(g) < MINIMO_ALUMNOS:
                    pocos.append(str(clave))
            salida[f"por_{group_by}"] = grupos
            if pocos:
                avisos.append(f"Pocos alumnos en: {', '.join(pocos)}")
        if avisos:
            salida["avisos"] = avisos
        return _json(salida)
    except Exception as e:
        return _error(f"Estadísticas: {e}")


@tool
def calculate_correlation(variable_a: str, variable_b: str = "nota", year: Union[int, str] = 2022,
                          CNT: Optional[str] = None, tipo_centro: Optional[str] = None,
                          ubicacion: Optional[str] = None, tamano: Optional[str] = None) -> str:
    """
    Weighted Pearson correlation between two student variables (same names as get_math_stats 'variable').
    Returns the mean r within each country-edition (the fair comparison, as in the project's EDA) and the pooled r.
    Optional filters by country and 'estratos fijos' (tipo_centro, ubicacion, tamano).
    """
    try:
        col_a, col_b = normalizar_variable(variable_a), normalizar_variable(variable_b)
        df, aplicados, avisos = filtrar_alumnos(year, CNT, tipo_centro=tipo_centro, ubicacion=ubicacion, tamano=tamano)
        df = df.dropna(subset=[col_a, col_b])
        if len(df) < MINIMO_ALUMNOS:
            return _error(f"Solo {len(df)} alumnos con datos en ambas variables.")

        def r_ponderada(g: pd.DataFrame) -> float:
            w = g["SENWT"].to_numpy(dtype=float)
            x, y = g[col_a].to_numpy(dtype=float), g[col_b].to_numpy(dtype=float)
            x, y = x - np.average(x, weights=w), y - np.average(y, weights=w)
            return float(np.sum(w * x * y) / np.sqrt(np.sum(w * x * x) * np.sum(w * y * y)))

        dentro = [r_ponderada(g) for _, g in df.groupby(["CNT", "year"], observed=True) if len(g) >= MINIMO_ALUMNOS]
        r = float(np.mean(dentro)) if dentro else r_ponderada(df)
        salida = {
            "a": etiqueta(col_a), "b": etiqueta(col_b), "ambito": aplicados.pop("pais", "panel de 12 países"),
            "filtros": aplicados, "n_alumnos": len(df),
            "r_dentro_pais_edicion": _r(r, 2), "r_global": _r(r_ponderada(df), 2),
            "fuerza": "fuerte" if abs(r) >= 0.5 else "moderada" if abs(r) >= 0.3 else "débil",
        }
        if avisos:
            salida["avisos"] = avisos
        return _json(salida)
    except Exception as e:
        return _error(f"Correlación: {e}")


# ==============================================================================
# b) CONTEXTO ESTÁTICO (imágenes pre-generadas)
# ==============================================================================

@tool
def get_context_chart(keyword: str = "") -> str:
    """
    Returns a pre-generated chart from the project's analysis (no computation). Use keyword to choose
    (e.g. 'recursos', 'centro', 'cobertura'). The answer lists the other available charts.
    """
    try:
        catalogo = cargar_catalogo_graficos()
        if catalogo.empty:
            return _error("No hay gráficos de contexto disponibles todavía.")
        elegido = catalogo.iloc[0]
        if keyword:
            texto = (catalogo["id"] + " " + catalogo["descripcion"]).map(_sin_acentos)
            clave = _sin_acentos(keyword)
            puntuacion = texto.map(lambda t: max(difflib.SequenceMatcher(None, clave, p).ratio() for p in t.split()))
            elegido = catalogo.loc[puntuacion.idxmax()]
        return _json({"imagen": elegido["ruta"], "descripcion": elegido["descripcion"],
                      "otros": [d for d in catalogo["descripcion"] if d != elegido["descripcion"]]})
    except Exception as e:
        return _error(f"Gráfico de contexto: {e}")


# ==============================================================================
# LISTA DE HERRAMIENTAS EXPORTADAS
# ==============================================================================
pisa_tools = [
    # a) Estadísticas descriptivas en vivo
    get_math_stats, calculate_correlation,
    # b) Contexto estático
    get_context_chart,
    # c) Simulación con los modelos: se añadirá en la etapa 2 (regresión + XGBoost)
]
