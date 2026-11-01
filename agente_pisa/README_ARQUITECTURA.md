# Arquitectura técnica del agente PISA

Agente analítico del TFM sobre la nota en matemáticas de PISA 2012-2022 en los 12 países del panel común (AUS, DNK, ESP, GBR, GRC, HUN, ISL, ITA, KOR, POL, SVK y SVN). Combina una interfaz de exploración manual con un chat con un agente LangGraph que usa modelos de Groq con herramientas (*Tool Calling*).

## 1. Estado actual: por etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Interfaz, agente y estadísticas descriptivas sobre `data/processed/tabla_modelo_alumno.parquet`, más una galería de gráficos de ejemplo | Hecha |
| 2 | Vía de modelos: regresión (peso de cada variable) y XGBoost (patrones y waterfall SHAP) | Pendiente del modelado |
| 3 | Gráficos definitivos, marco teórico en el System Prompt y despliegue en Streamlit Cloud | Pendiente |

Lo que falta para cada etapa está en `REQUISITOS_PENDIENTES.md`.

## 2. Estructura de ficheros

```
agente_pisa/
├── app.py                    Interfaz Streamlit (entrypoint de Streamlit Cloud)
├── agente.py                 Grafo LangGraph, selección de modelos Groq, ventana de memoria, reintentos y respaldo
├── herramientas.py           Herramientas del agente, agrupadas en las 3 vías
├── datos.py                  Carga de artefactos con st.cache_data
├── graficos.py               Waterfall SHAP de un perfil (se usará en la etapa 2)
├── config.py                 Rutas, países, avisos, modelos de Groq y etiquetas legibles
├── preparar_artefactos.py    Genera artefactos/ a partir de data/ y reports/ (se ejecuta en local)
├── system_prompt.md          Instrucciones del agente (en inglés, respuestas en español)
├── metodologia/              Notas de metodología en .md, una por tema (cómo se construye cada índice...)
├── requirements.txt          Dependencias mínimas para Streamlit Cloud
├── agente_pisa.ipynb         Banco de pruebas manuales y Gradio
├── evaluador/                Batería de casos de referencia y juez LLM (casos por rehacer)
├── artefactos/               Datos que consume la app (se suben a git)
│   ├── alumnos_modelo.parquet    Alumnos en_modelo (298.782), legibles, con la nota de matemáticas
│   ├── catalogo_graficos.csv     Imágenes que el agente y la galería pueden mostrar
│   └── img/                      PNG copiados de reports/
├── README_ARQUITECTURA.md    Este documento
└── REQUISITOS_PENDIENTES.md  Checklist de lo que falta
```

## 3. Cómo se conectan los ficheros

```
data/processed/tabla_modelo_alumno.parquet + reports/
        │
        ▼  python agente_pisa/preparar_artefactos.py   (local, cada vez que cambien los datos)
artefactos/
        │
        ▼  datos.py  (lectura cacheada)
herramientas.py
        │
        ▼
agente.py  (LangGraph: asistente <-> herramientas, con system_prompt.md)
        │
        ├──► app.py              (Streamlit: chat + panel visual)
        ├──► agente_pisa.ipynb   (pruebas manuales y Gradio)
        └──► evaluador/          (batería de evaluación)
```

`config.py` lo importan todos los módulos. Las herramientas devuelven JSON; la app lee esos resultados en los mensajes de herramienta para mostrar imágenes (clave `imagen`) y para dibujar gráficas de las estadísticas (salidas de `get_math_stats`), sin que el LLM tenga que repetir nada.

## 4. Decisiones de arquitectura

💡 **Datos de alumno legibles y sin codificar.** `alumnos_modelo.parquet` son los alumnos que entran en el modelo (`en_modelo`), con las variables en sus unidades originales, la nota de matemáticas (media de los valores plausibles) y los `estratos fijos` desglosados en tipo, ubicación y tamaño del centro. Las herramientas filtran con los mismos valores con los que pregunta el usuario («privados», «rurales», «chicas»).

💡 **Los mismos alumnos que el modelo.** Las estadísticas descriptivas usan solo los alumnos `en_modelo`, de modo que las cifras del chat son coherentes con las que se obtendrán de la regresión y del XGBoost.

💡 **Ponderación con el peso de senado.** Todas las medias usan `SENWT`. Dentro de un país y edición es proporcional a `W_FSTUWT`, así que da la media representativa del país. En el panel da el mismo peso a cada país y edición, el mismo criterio que usa el modelo.

💡 **Aviso de 2018.** En 2018 las horas de deberes proceden de un cuestionario opcional (64 % de los alumnos con índice de compromiso; 28 % en GBR). Ya está tenido en cuenta en el modelado, pero el agente lo recuerda siempre que una respuesta incluye esa edición: las herramientas añaden el aviso y el System Prompt obliga a mencionarlo.

💡 **Caché de datos.** Las tablas se leen con `st.cache_data`, que devuelve una copia por llamada. Los resultados de los modelos de la etapa 2 también son tablas y se leen igual. La app precarga todas las cachés en el hilo principal (`precargar_artefactos`) porque LangGraph ejecuta las herramientas en hilos sin contexto de Streamlit.

💡 **Selección dinámica de modelos de Groq.** `listar_modelos_groq()` consulta `client.models.list()` y cruza la respuesta con `MODELOS_GROQ_PRIORIDAD` (modelos verificados con Tool Calling: `gpt-oss-120b` como principal y `gpt-oss-20b` como respaldo). Si Groq retira un modelo, desaparece del selector sin tocar el código.

💡 **Protección de tokens en la capa gratuita de Groq.**
- Ventana deslizante de 4 mensajes más el System Prompt, empezando siempre en una pregunta del usuario y sin separar una llamada a herramienta de su resultado.
- Salidas de herramientas en JSON compacto con etiquetas legibles: entre 40 y 230 tokens.
- Solo 4 herramientas, cuyos esquemas ocupan unos 1.070 tokens.
- La metodología (cómo se construye cada índice, marco teórico) no va en el System Prompt: la devuelve `get_methodology` solo cuando se pregunta por ella.
- Las gráficas de las respuestas las dibuja la app a partir del JSON de la herramienta, sin pedírselas al LLM.
- La exploración manual y la galería se calculan con Python puro y consumen 0 tokens.

💡 **Límite de cuota (429) con reintentos y respaldo.** `ChatGroq` se crea con `max_retries=0` y la llamada se envuelve con `tenacity` (`@retry` con backoff exponencial de 2 a 10 s, 2 intentos por modelo). Si el modelo sigue sin cuota, `invocar_con_respaldo` salta al siguiente modelo validado. En las pruebas, `gpt-oss-120b` agotó su cuota por minuto y respondió `gpt-oss-20b` sin intervención.

💡 **Credenciales.** `obtener_api_key()` lee `st.secrets["GROQ_API_KEY"]` en Streamlit Cloud y, si no existe, `agente_pisa/.env` en local. Ambos ficheros de secretos están en `.gitignore`.

💡 **Resultados de los modelos, no modelos (etapa 2).** Hay una regresión y un XGBoost por edición y por valor plausible (40 de cada). La app no carga ninguno: el modelado entrega los coeficientes de la regresión combinados con las reglas de Rubin, las métricas y los SHAP del XGBoost de cada alumno, promediados entre valores plausibles (`ENTREGA_MODELOS.md`). Las preguntas de interacciones o de diferencias por estrato se responden agrupando esa tabla de SHAP; las simulaciones de un perfil, con los coeficientes. Así la app arranca rápido y no depende de la versión de XGBoost. Los gráficos globales (beeswarm y dependence) se pre-generan y el waterfall de un perfil se dibuja en el momento con `graficos.py`.

## 5. Las tres vías de herramientas

| Vía | Herramientas | Qué hace |
|---|---|---|
| a) Estadísticas descriptivas en vivo | `get_math_stats` | Media ponderada de la nota (o de otra variable del alumno) para cualquier subgrupo: país, edición, `estratos fijos`, nivel de compromiso, recursos de estudio, sexo u origen. Con `group_by` compara grupos o hace el ranking de países. Admite términos genéricos |
| | `calculate_correlation` | Correlación ponderada entre dos variables del alumno: la media de las correlaciones dentro de cada país y edición (como en el EDA) y la global |
| b) Contexto estático | `get_context_chart` | Devuelve un PNG del catálogo según una palabra clave |
| | `get_methodology` | Devuelve la nota de metodología de un tema (un `.md` de `metodologia/`): cómo se construye un índice, qué preguntas usa, cómo se igualan las ediciones y qué se hace con los huecos. Los temas salen de los nombres de los ficheros, así que añadir un `.md` basta |
| c) Modelos (etapa 2) | Pendiente | Regresión: peso de cada variable y simulación lineal. XGBoost: patrones por estrato e interacciones a partir de los SHAP por alumno, y waterfall de un perfil |

Los niveles descriptivos usan cortes fijos, iguales en todas las ediciones:
- **Compromiso:** bajo por debajo de −1 desviación típica, medio entre −1 y +1, alto por encima de +1 (los umbrales del EDA del índice).
- **Recursos de estudio:** hasta 4, 5 de 6 o los 6.

## 6. Interfaz

- **Barra lateral:** selector del modelo principal (el resto queda como respaldo), nueva conversación y controles de exploración manual: edición, país, dimensión de comparación y filtros de `estratos fijos`.
- **Columna izquierda:** chat. Si una respuesta tiene gráfica, el botón «Ver gráfico en el panel» la vuelve a mostrar.
- **Columna derecha:** panel con el gráfico arriba y la explicación debajo, en tres vistas:
  - *Exploración manual:* barras por grupo o líneas por edición, con un texto generado en Python y los avisos.
  - *Galería de gráficos:* PNG de ejemplo del análisis exploratorio.
  - *Respuesta del agente:* las gráficas e imágenes del último turno y su explicación.

## 7. Guía de reutilización del código original

| Código original | Dónde está ahora |
|---|---|
| Notebook: `client.models.list()` | `agente.py` (`listar_modelos_groq`): cruza la lista con los modelos verificados y alimenta el selector y el respaldo |
| Notebook y script: grafo `asistente <-> tools` con `MemorySaver` y `tools_condition` | `agente.py` (`construir_agente`), igual; los modelos se eligen en cada invocación, así que cambiar de modelo no borra la memoria |
| Notebook: registro de tokens y tool calls | `agente.py` (`_registrar_uso`), con `logging` |
| Script: saneado de `"<|"` en los nombres de tool | `agente.py` (`asistente`), igual |
| Script y notebook: `trim_messages` | `agente.py` (`ventana_deslizante`), con 4 mensajes |
| `app.py`: `thread_id` por sesión, streaming y limpieza de imágenes Markdown | `app.py`, igual |
| `herramientas.py`: normalizadores con `difflib`, asignatura y salida por herramienta | `herramientas.py`: el mismo patrón de normalización, ahora para países, `estratos fijos`, niveles y variables del alumno |
| `system_prompt.md` | Mismas secciones (rol, idioma, estilo y guardarraíles), con el alcance actual y el bloque del marco teórico |
| Notebook: Gradio y evaluación | `agente_pisa.ipynb`, importando el agente desde `agente.py` |
| `evaluador/` | Sin cambios funcionales; se añadió la lista `CASOS_TEST_PISA`, que faltaba |

Herramientas retiradas, porque su contenido pasó al anexo:
- **Presupuesto, macroeconomía y proyecciones OLS:** `get_country_data`, `get_cross_country_stats`, `get_cross_variable_stats`, `analyze_temporal_trend` y `predict_future_trend`.
- **Modelo por estrato:** `get_feature_importance`, `predict_and_explain_performance` y `simulate_scenario`.

`simulate_scenario` y `predict_and_explain_performance` servirán de base para la vía de modelos de la etapa 2.

## 8. Ejecución

**Local** (entorno `tfm_env`, desde la raíz del repositorio):

```bash
python agente_pisa/preparar_artefactos.py      # solo si cambian los datos o las imágenes
streamlit run agente_pisa/app.py
```

Se abre en `http://localhost:8501`. La clave de Groq se lee de `agente_pisa/.env` (`GROQ_API_KEY=...`).

**Streamlit Cloud (etapa 3):**
1. Sube a git `agente_pisa/`, incluida `artefactos/` (unos 7 MB).
2. *New app*, con *Main file path* `agente_pisa/app.py`.
3. En *Advanced settings*: Python 3.12 y el secreto `GROQ_API_KEY = "..."`.

## 9. System Prompt y marco teórico

`system_prompt.md` fija el alcance (solo matemáticas, 12 países, alumnos del modelo, aviso de 2018), el enrutado entre vías, el estilo y los guardarraíles. El marco teórico definitivo se insertará entre las marcas `INICIO BLOQUE MARCO TEÓRICO` y `FIN BLOQUE MARCO TEÓRICO`. Ese texto se envía en cada llamada, así que conviene mantenerlo breve (unos 300 a 500 tokens).
