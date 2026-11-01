# Requisitos pendientes del agente PISA

Checklist de lo que el agente necesita de las fases que aún no están cerradas. Cada punto indica qué fichero espera la arquitectura y qué hay que tocar. Después de cualquier cambio en los datos o las imágenes, basta con ejecutar `python agente_pisa/preparar_artefactos.py`.

## Etapa 1: hecha

- [x] Estadísticas descriptivas sobre `data/processed/tabla_modelo_alumno.parquet`: solo matemáticas, 12 países y alumnos `en_modelo`.
- [x] Filtros y comparaciones por `estratos fijos`, nivel de compromiso, recursos de estudio, sexo, origen, país y edición.
- [x] Aviso de la limitación de 2018 en las herramientas, la interfaz y el System Prompt.
- [x] Galería con 4 gráficos de ejemplo de `reports/`.

## Etapa 2: modelos (regresión y XGBoost)

Una regresión y un XGBoost por edición, estimados con cada valor plausible. El agente no carga ningún modelo: solo sus resultados, que el modelado deja en `models/` con el formato de `ENTREGA_MODELOS.md`.

**Entrega del modelado** (`ENTREGA_MODELOS.md`)
- [ ] `models/shap_alumnos.parquet`: SHAP del XGBoost de cada alumno, medio entre los valores plausibles de su edición, con valor base y predicción.
- [ ] `models/coeficientes_regresion.csv`: la regresión global y la regresión por perfil (variables × indicador de cada perfil) en una tabla, combinadas con las reglas de Rubin.
- [ ] `models/metricas_modelos.csv`: R², RMSE y MAE por modelo y edición.
- [ ] Ejecutar `preparar_artefactos.py`: comprueba el formato (y que valor base + SHAP = predicción), se queda con los alumnos del agente y copia las tres tablas a `artefactos/`. `datos.py` ya las carga.

**Herramientas nuevas** (cada una se activa con su tabla: `datos.regresion_disponible()`, `shap_disponible()`, `metricas_disponibles()`)
- [ ] `get_regression_weights(variable, edicion, estrato)`: peso de cada variable y su significación, por edición. Sin estrato, la regresión global; con estrato, la regresión por perfil. Avisar si el perfil tiene pocos centros. Si los coeficientes están tipificados, `data/processed/parametros_escala.parquet` permite traducirlos a unidades originales («por cada recurso de estudio más...»).
- [ ] Simulación lineal con la regresión: «con 2 recursos más, la nota cambia 2 × coeficiente».
- [ ] Explicación de un perfil: waterfall con la media de los SHAP de los alumnos reales de ese perfil (o con coeficiente × distancia a la media). `graficos.guardar_waterfall` ya lo dibuja.
- [ ] Patrones del XGBoost agrupando la tabla de SHAP: importancia por `estratos fijos`, origen social, nivel de compromiso o de recursos; interacciones y no linealidades.
- [ ] Fiabilidad: citar las métricas de cada modelo y si el XGBoost mejora a la regresión (si no, los efectos son casi lineales).
- [ ] System Prompt: describir las herramientas, que la edición elige el modelo (no se simula «este alumno en otra edición») y que son asociaciones, no efectos causales.

**Gráficos de los modelos**, que `preparar_artefactos.py` puede generar con las tablas de la entrega:
- [ ] Coeficientes de la regresión con sus intervalos (gráfico de bosque).
- [ ] Beeswarm SHAP global del XGBoost.
- [ ] Dependence plots del índice de compromiso y de los recursos de estudio, coloreados por el origen social, para ver interacciones.
- [ ] Importancia SHAP media por `estratos fijos`, para preguntas como «qué pesa más en los centros rurales».
- [ ] Importancia SHAP y coeficientes por edición.

## Etapa 3: cierre

- [ ] Imágenes definitivas: cuando estén en `reports/`, actualizar la lista `GRAFICOS_CONTEXTO` de `preparar_artefactos.py` (fichero y descripción; el agente elige la imagen leyendo la descripción).
- [ ] Marco teórico: completar el bloque marcado en `system_prompt.md` cuando el informe esté cerrado (unos 300 a 500 tokens).
- [ ] Evaluador: los casos de `evaluador/reference_test.py` son del bloque exploratorio de 33 países, ahora en `anexo/`, y piden herramientas que ya no existen. Hay que rehacerlos con preguntas de la línea actual: `estratos fijos`, compromiso, recursos, países del panel y el aviso de 2018.
- [x] Despliegue en Streamlit Cloud: subir `agente_pisa/artefactos/`, configurar la app y el secreto `GROQ_API_KEY` (pasos en `README_ARQUITECTURA.md`, sección 8).

## Notas sobre el repositorio

- [x] `data/processed/README.md` dice que el agente usa `dataset_pisa_estrato_llm.pkl`. Ya no es así: ahora lee `tabla_modelo_alumno.parquet` mediante `preparar_artefactos.py`. Ese `.pkl` puede pasar a `anexo/modelo_por_estrato/datos/`.
