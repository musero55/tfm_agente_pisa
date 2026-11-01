"""
Configuración central del agente PISA: rutas, constantes y catálogos.

Todos los módulos (preparar_artefactos.py, datos.py, herramientas.py, agente.py y app.py)
leen de aquí, de modo que cambiar una ruta o un modelo de Groq solo requiere tocar este fichero.
"""
from pathlib import Path
import tempfile

# ==========================================================
#  RUTAS
# ==========================================================
DIR_AGENTE = Path(__file__).resolve().parent
DIR_RAIZ = DIR_AGENTE.parent

# Artefactos que consume el agente (los genera preparar_artefactos.py y se suben a git para Streamlit Cloud)
DIR_ARTEFACTOS = DIR_AGENTE / "artefactos"
DIR_IMAGENES_MACRO = DIR_ARTEFACTOS / "img"

RUTA_ALUMNOS = DIR_ARTEFACTOS / "alumnos_modelo.parquet"          # alumnos en_modelo, legibles (sin codificar)
RUTA_CATALOGO_GRAFICOS = DIR_ARTEFACTOS / "catalogo_graficos.csv"
# Metodología (cómo se construye cada índice, marco teórico...): un .md por tema, escrito a mano
DIR_METODOLOGIA = DIR_AGENTE / "metodologia"
# Etapa 2 (pendiente del modelado): resultados de la regresión y del XGBoost, sin los modelos
RUTA_SHAP = DIR_ARTEFACTOS / "shap_alumnos.parquet"                # SHAP de cada alumno, medio entre valores plausibles
RUTA_COEFICIENTES = DIR_ARTEFACTOS / "coeficientes_regresion.csv"  # regresión por edición, combinada con Rubin
RUTA_METRICAS = DIR_ARTEFACTOS / "metricas_modelos.csv"            # R², RMSE y MAE por modelo y edición

# Imágenes generadas en vivo (waterfall, etapa 2). En Streamlit Cloud el disco es efímero, por eso van a temp.
DIR_IMAGENES_TEMP = Path(tempfile.gettempdir()) / "pisa_plots"

# Fuentes del proyecto que usa preparar_artefactos.py
FUENTES = {
    "tabla_modelo": DIR_RAIZ / "data" / "processed" / "tabla_modelo_alumno.parquet",
    "reports": DIR_RAIZ / "reports",
    # Etapa 2: resultados del modelado (formato en ENTREGA_MODELOS.md)
    "shap_alumnos": DIR_RAIZ / "models" / "shap_alumnos.parquet",
    "coeficientes_regresion": DIR_RAIZ / "models" / "coeficientes_regresion.csv",
    "metricas_modelos": DIR_RAIZ / "models" / "metricas_modelos.csv",
}

# ==========================================================
#  DOMINIO PISA (línea principal del TFM)
# ==========================================================
PISA_YEARS = [2012, 2015, 2018, 2022]
PAISES_PANEL = ["AUS", "DNK", "ESP", "GBR", "GRC", "HUN", "ISL", "ITA", "KOR", "POL", "SVK", "SVN"]
NOMBRES_PAISES = {
    "AUS": "Australia", "DNK": "Dinamarca", "ESP": "España", "GBR": "Reino Unido", "GRC": "Grecia",
    "HUN": "Hungría", "ISL": "Islandia", "ITA": "Italia", "KOR": "Corea del Sur", "POL": "Polonia",
    "SVK": "Eslovaquia", "SVN": "Eslovenia",
}

AVISO_2018 = (
    "En 2018 las horas de deberes proceden de un cuestionario opcional: solo el 64 % de los alumnos tiene "
    "índice de compromiso (en GBR, el 28 %). Interpretar esa edición con cautela."
)
AVISO_2018_CORTO = "2018: deberes de un cuestionario opcional (64 % con índice; GBR 28 %), interpretar con cautela"
AVISO_POCO_REPRESENTATIVO = "incluye perfiles de centro con pocos centros en esa edición (poco fiables)"

# Estratos fijos (Tipo / Ubicación / Tamaño del centro) a partir del código de perfil (p. ej. PUB_URB_MED)
TIPOS_CENTRO = {"PUB": "Público", "CON": "Concertado", "PRI": "Privado"}
UBICACIONES = {"URB": "Urbano", "RUR": "Rural"}
TAMANOS = {"PEQ": "Pequeño", "MED": "Mediano", "MACRO": "Grande"}

# Niveles descriptivos de las variables de interés (cortes fijos, iguales en todas las ediciones)
#TODO Cortes compromiso no seria hasta -1 , 1, infinito ?? Que es la desviación tipica del indice
CORTES_COMPROMISO = ([-float("inf"), -1, 1, float("inf")], ["Bajo", "Medio", "Alto"])     # en DT del índice, como en el EDA
CORTES_RECURSOS = ([-float("inf"), 4.5, 5.5, float("inf")], ["Hasta 4", "5 de 6", "Los 6"])    # recursos de estudio

# Dimensiones por las que se puede filtrar o agrupar (columna -> nombre legible)
DIMENSIONES = {
    "tipo_centro": "Tipo de centro",
    "ubicacion": "Ubicación",
    "tamano": "Tamaño del centro",
    "nivel_compromiso": "Nivel de compromiso",
    "nivel_recursos": "Recursos de estudio",
    "sexo": "Sexo",
    "origen": "Origen",
    "CNT": "País",
    "year": "Edición",
}

# Variables numéricas que admiten medias y correlaciones (columna -> nombre legible)
VARIABLES_NUMERICAS = {
    "nota": "Nota en matemáticas",
    "Indice_Compromiso_Competencia": "Índice de compromiso y competencia",
    "recursos_estudio": "Recursos de estudio del hogar",
    "riqueza_hogar": "Riqueza del hogar",
    "libros": "Libros en casa",
    "HISEI_TREND": "Ocupación de los padres",
    "PAREDINT_TREND": "Años de estudios de los padres",
    "composicion_social_centro": "Composición social del centro",
    "dotacion_centro": "Dotación del centro",
}

# ==========================================================
#  GROQ
# ==========================================================
# Modelos verificados con Tool Calling, por orden de preferencia (principal -> respaldo).
# La app cruza esta lista con client.models.list() para usar solo los que siguen activos.
MODELOS_GROQ_PRIORIDAD = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]
# Subcadenas de modelos de Groq que no sirven para chat con herramientas (audio, guardarraíles...)
MODELOS_GROQ_EXCLUIDOS = ("whisper", "guard", "tts", "orpheus", "distil")

VENTANA_MENSAJES = 4          # mensajes de conversación enviados a Groq además del System Prompt
LIMITE_RECURSION = 10         # pasos máximos del grafo (asistente <-> herramientas) por pregunta
REINTENTOS_RATE_LIMIT = 2     # intentos por modelo ante un 429 antes de saltar al siguiente

RUTA_SYSTEM_PROMPT = DIR_AGENTE / "system_prompt.md"


def resolver_imagen(referencia: str) -> Path:
    """Convierte la referencia corta que devuelven las herramientas ('img/x.png' o 'tmp/x.png') en ruta absoluta."""
    if referencia.startswith("tmp/"):
        return DIR_IMAGENES_TEMP / referencia[4:]
    return DIR_ARTEFACTOS / referencia


def etiqueta(variable: str) -> str:
    """Nombre legible de una variable o dimensión; si no está en los catálogos, quita los guiones bajos."""
    return VARIABLES_NUMERICAS.get(variable) or DIMENSIONES.get(variable) or variable.replace("_", " ").capitalize()
