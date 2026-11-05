# Requisitos pendientes del agente PISA

Checklist de lo que falta para cerrar el agente. Cada punto indica qué fichero hay que tocar. Después de cualquier cambio en los datos o las imágenes, basta con ejecutar `python agente_pisa/preparar_artefactos.py`.

El agente sirve para entender el proyecto y analizar sus resultados, así que tiene que conocer las decisiones metodológicas: todo lo que explique sale de `metodologia/` (un `.md` nuevo basta para que `get_methodology` lo vea).

## Etapa 1: hecha

- [x] Estadísticas descriptivas sobre `data/processed/tabla_modelo_alumno.parquet`: solo matemáticas, 12 países y alumnos `en_modelo`.
- [x] Filtros y comparaciones por `estratos fijos`, nivel de compromiso, recursos de estudio, sexo, origen, país y edición.
- [x] Aviso de la limitación de 2018 en las herramientas, la interfaz y el System Prompt.
- [x] Galería con gráficos de ejemplo de `reports/`.

## Etapa 2: modelos (regresión y XGBoost)

Una regresión y un XGBoost por edición, estimados con cada valor plausible. El agente no carga ningún modelo: solo sus resultados.

**Entrega del modelado: hecha** (commit `0f02e7f`)
- [x] `models/shap_alumnos.parquet`: coincide con el formato pedido (298.782 alumnos; SHAP calculados sobre todos, no solo test).
- [x] `models/coeficientes_regresion.csv`: llegó con otro formato; `preparar_artefactos.py` lo traduce (`ADAPTACION_MODELOS.md`).
- [x] `models/metricas_modelos.csv`: solo de la regresión por perfil y del XGBoost, con validación cruzada por centro.
- [x] `preparar_artefactos.py` ejecutado: las tres tablas ya están en `artefactos/` y `datos.py` las carga.

**Metodología de los modelos** (sin esto el agente no sabe leer sus propias cifras)
- [x] `robustez.md`: qué resultados aguantan las comprobaciones y cuáles no.
- [x] Cautelas añadidas en `compromiso.md` (la subida viene de los deberes), `perfiles_centro.md` (privado urbano grande = Australia) y `recursos_estudio.md` (cifras del modelo).
- [x] `metodologia/modelos.md`: las dos regresiones y cómo se lee un coeficiente, unidades, fiabilidad, XGBoost y SHAP, métricas y cómo usarlo en las respuestas.
- [x] Se recuperan los efectos fijos de perfil de la común (`variable = "efecto_perfil"`, con el perfil en `estrato`): diferencia de nota frente a `PUB_URB_MED` con lo demás igual. Explicado en `modelos.md`.
- [x] La regresión «global» de la traducción pasa a llamarse `comun`, como la de Alberto (`pendiente_comun`): compara alumnos del mismo país y perfil.

**Herramientas nuevas** (cada una se activa con su tabla: `datos.regresion_disponible()`, `shap_disponible()`, `metricas_disponibles()`)
- [x] `get_regression_weights(variable, year, tipo_centro, ubicacion, tamano, cambio)` en `herramientas.py`:
  - sin variable, el peso de todas ordenado por puntos por desviación típica (columna `coeficiente_dt`, añadida a la tabla);
  - una variable: coeficiente común con intervalo y p; con filtros de perfil, el de cada perfil (solo compromiso y recursos);
  - `variable='perfil'`: diferencia frente a `PUB_URB_MED` con lo demás igual;
  - `cambio`: simulación lineal con su intervalo; `year='all'`: evolución y cambio 2012-2022 con su p;
  - avisos de 2018, perfiles poco representativos y los dos resultados frágiles de `robustez.md` (Australia y subida del compromiso).
- [x] `get_xgboost_patterns(analisis, year, variable, filtros, group_by)` en `herramientas.py`, con los SHAP de cada alumno:
  - `importancia`: puntos que mueve cada variable, en un grupo, entre grupos o entre ediciones; calcula qué variables difieren más de 2 puntos entre grupos (si no, «el patrón es casi igual»);
  - `contribucion`: por qué la predicción de un grupo está por encima o por debajo de la media, con waterfall (`graficos.guardar_waterfall`);
  - `forma`: SHAP medio por valor (recursos redondeados al entero, como `03_xgboost_shap`; variables continuas por quintiles);
  - aviso cuando se filtra por perfil y el grupo tiene menos de 5.000 alumnos (el XGBoost no ve patrones de grupos pequeños).
- [ ] Opcional: el primer waterfall tarda unos 14 s (importar `shap`). Dibujarlo solo con matplotlib quitaría esa espera y la dependencia de `shap`.
- [x] Fiabilidad: las métricas están en `modelos.md` (tabla de calidad); no hace falta herramienta.
- [x] System Prompt: ruta 4 con `get_regression_weights`, unidades, «con lo demás igual», simulación no individual, `modelos` y `robustez`. Ruta 5 con `get_xgboost_patterns` y reglas para diferencias pequeñas y para no inventar explicaciones.
- [x] Tokens por llamada recortados de 4.200 a ~2.460 (System Prompt de 1.743 a ~940; herramientas de 2.457 a ~1.525). Probadas 9 preguntas, una por ruta, con el modelo principal: entre 4.800 y 6.800 tokens por pregunta, todas por debajo del límite de 8.000 por minuto.
- [ ] Opcional: las notas de metodología más largas (`modelos`, 2.807 tokens; `compromiso`, 2.140) son ahora lo más caro de una pregunta de metodología.
- [ ] Probar más preguntas en la app. Probadas con Groq (2026-11-02): peso de compromiso frente a recursos, privados frente a públicos con lo demás igual, simulación de 2 recursos y fiabilidad del privado urbano grande. Con el XGBoost: por qué sacan más los privados, si se aplanan los recursos y qué pesa más en rurales y urbanos. Casi todas con el modelo de respaldo `gpt-oss-20b`, porque el `120b` daba límite de uso; el `120b` interpreta mejor.

## Etapa 3: cierre

- [ ] Imágenes, al redactar la memoria: actualizar las listas de `preparar_artefactos.py` (el agente elige la imagen leyendo la descripción). Incluye:
  - [x] Gráficos de modelado: los 13 PNG `03_*.png` están en la lista `GRAFICOS_MODELADO` (catálogo de 35 gráficos con los de recursos del alumno). `get_context_chart` puntúa ahora todas las palabras de la búsqueda y solo lista los 5 gráficos más relacionados (de ~4.300 a ~1.000 caracteres por respuesta). El System Prompt le prohíbe inventar ejes o valores de una imagen que no ve.
  - Si cambian los PNG de `reports/` al redactar la memoria, revisar que las descripciones sigan siendo ciertas.
  - [x] `GRAFICOS_RECURSOS_ALUMNO`: los 4 gráficos de cómo se forma el índice de recursos ya se copian (catálogo de 35). Están calculados con 33 países de la OCDE (`01_EDA_recursos_alumno`, celda 2), así que su descripción lo dice.
- [ ] Marco teórico: escribirlo como nota `metodologia/marco_teorico.md` cuando el informe esté cerrado. El System Prompt ya no tiene el bloque reservado (se quitó en `e8855de`), y así no gasta tokens en cada llamada.
- [ ] Evaluador: 16 casos en `evaluador/reference_test.py` (perfiles y Australia, y conclusiones de la memoria) y notebook `evaluador/evaluator.ipynb`, que ejecuta la batería, la guarda en `evaluador/resultados/` y compara ejecuciones. Falta lanzar la batería completa y revisar los fallos.
- [x] `README_ARQUITECTURA.md` actualizado: etapas, qué hace cada herramienta y cuándo se llama, temas de metodología, tokens y la traducción de la entrega (sección 9, que sustituye a `ADAPTACION_MODELOS.md`).
- [x] `app.py` probado con las herramientas nuevas (`AppTest`, 2026-11-02): arranca sin errores y el waterfall llega al panel. No necesita más cambios.
- [x] Despliegue en Streamlit Cloud (pasos en `README_ARQUITECTURA.md`, sección 7).

## Qué quitar al terminar

- [x] `ENTREGA_MODELOS.md` (borrado; las referencias del código apuntan ahora a `models/README.md`).
- `ADAPTACION_MODELOS.md`: su contenido ya está en `metodologia/modelos.md` y en la sección 9 de `README_ARQUITECTURA.md`. Se puede borrar.
- `REQUISITOS_PENDIENTES.md` (este fichero).
- En `preparar_artefactos.py`: los gráficos comentados que no se usen, los `#Check` y los textos «pendiente del modelado» / «Etapa 2».
- Las menciones a «etapa 2» y «se añadirá» en `herramientas.py`, `datos.py`, `config.py`, `graficos.py` y `system_prompt.md`.
- Opcional: `agente_pisa.ipynb` (banco de pruebas con Gradio), si ya no se usa.
- No tocar: `models/` (es la entrega del compañero) ni `artefactos/` (los usa la app en la nube).
