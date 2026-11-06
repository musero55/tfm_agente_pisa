# Agente PISA - Trabajo Fin de Máster

Agente conversacional del TFM **«Compromiso, recursos y nota en PISA (2012-2022)»**. Responde preguntas sobre los resultados del proyecto: estadísticas descriptivas de la nota de matemáticas, metodología, gráficos del análisis y resultados de la regresión por edición y del XGBoost con SHAP, en el panel de 12 países (AUS, DNK, ESP, GBR, GRC, HUN, ISL, ITA, KOR, POL, SVK y SVN).

Esta entrega contiene **solo lo necesario para ejecutar y evaluar el agente**. Los notebooks, los datos, el código del análisis y el script que genera los artefactos (`preparar_artefactos.py`) están en la entrega del proyecto completo. El agente no los necesita: lee los resultados ya generados en `agente_pisa/artefactos/`.

---

## Puesta en marcha

Todos los comandos se ejecutan desde esta carpeta (la que contiene `agente_pisa/` y `requirements.txt`).

1. **Python 3.12.** Las versiones fijadas de `requirements.txt` (numpy 2.1.3, pyarrow 17) no tienen paquetes para Python 3.13 o 3.14 y la instalación falla. Si no se tiene Python 3.12, con [uv](https://docs.astral.sh/uv/) basta `uv venv --python 3.12 .venv` y `uv pip install --python .venv/Scripts/python -r requirements.txt`.
2. **Entorno virtual** con las versiones de `requirements.txt`, registrado como kernel `tfm_env` para el notebook de evaluación:
   ```bash
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements.txt
   .venv/Scripts/python -m ipykernel install --user --name tfm_env --display-name tfm_env
   ```
   En Linux o macOS la ruta es `.venv/bin/python`.
3. **Clave de Groq.** Copiar `agente_pisa/.env.example` como `agente_pisa/.env` y poner la clave en `GROQ_API_KEY=` (se crea gratis en [console.groq.com/keys](https://console.groq.com/keys)).
4. **Lanzar la app:**
   ```bash
   .venv/Scripts/python -m streamlit run agente_pisa/app.py
   ```
   Se abre en `http://localhost:8501`.
5. **Evaluación (opcional):** abrir `agente_pisa/evaluador/evaluator.ipynb` con el kernel `tfm_env` y ejecutar todas las celdas. Tarda unos 25 minutos por la cuota gratuita de Groq. El notebook se entrega con los resultados de la última ejecución.

---

## Contenido

```text
├── agente_pisa/
│   ├── app.py                  Interfaz Streamlit
│   ├── agente.py               Grafo LangGraph y modelos de Groq
│   ├── herramientas.py         Herramientas del agente
│   ├── datos.py, graficos.py   Carga de artefactos y waterfalls SHAP
│   ├── config.py               Rutas, constantes y catálogos
│   ├── system_prompt.md        Instrucciones del agente
│   ├── metodologia/            Notas de metodología que consulta el agente
│   ├── artefactos/             Datos y gráficos que lee el agente (ya generados)
│   ├── evaluador/              Juez LLM, casos de referencia y notebook de evaluación
│   ├── .env.example            Plantilla del .env
│   └── README_ARQUITECTURA.md  Documentación técnica del agente
└── requirements.txt
```

El detalle de la arquitectura, las herramientas, la interfaz y la evaluación está en [agente_pisa/README_ARQUITECTURA.md](agente_pisa/README_ARQUITECTURA.md).
