# Datos para los modelos

| Fichero | Lo genera | Contenido |
|---|---|---|
| `tabla_modelo_alumno.parquet` | `notebooks/fase_2_feature_engineering/02_preparacion_modelo` | Una fila por alumno con perfil de centro de los 12 países del panel común y las cuatro ediciones. Las variables están en sus unidades originales, sin imputar ni codificar. Las marcas `perfil_excluido`, `perfil_poco_representativo`, `con_variables_interes` y `en_modelo` dicen quién entra en el modelo. La leen los notebooks de modelado y el agente |
| `parametros_escala.parquet` | `02_preparacion_modelo` | Media y desviación típica (con `SENWT`, alumnos `en_modelo`) de cada variable continua. Sirven para tipificar (`matriz_regresion`) y para pasar un coeficiente por desviación típica a unidades originales |
| `diccionario_tabla_modelo.csv` | `02_preparacion_modelo` | Papel, descripción y unidades de cada columna de `tabla_modelo_alumno.parquet` |
| `resultados_robustez.parquet` | `notebooks/fase_3_modelado/03_robustez_regresion` | Una fila por comprobación de robustez y variable de interés: pendiente común en 2012 y 2022 y su cambio, contrastes de igualdad entre perfiles y cambio de la pendiente del privado urbano grande (`PRI_URB_MACRO`). La fila `modelo de partida` es el modelo de `03_regresion_por_edicion`. Las filas con `panel` y `pais_quitado` son el modelo sin cada país, en el panel común y en el ampliado |
| `dataset_pisa_estrato_llm.pkl` | `anexo/modelo_por_estrato/02_data_panel_modelos` | Tabla del primer modelo por estrato que usa el agente (`agente_pisa/`) |

Las matrices de la regresión y de XGBoost no se guardan. Se construyen desde la tabla con `matriz_regresion` y `matriz_xgboost` (`src/preparacion_modelo.py`).

Los resultados de los modelos que lee el agente (coeficientes de la regresión, SHAP de XGBoost y métricas de los dos) están en `models/`, descritos en `models/README.md`.
