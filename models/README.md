# Entrega de los modelos

Todo va en la carpeta `models/`, en la raíz del repositorio. Una regresión y un XGBoost por edición, estimados con cada valor plausible de matemáticas (10 por edición; 5 en 2012). El agente no carga ningún modelo: solo estas tres tablas.

## Ficheros

```
models/
├── shap_alumnos.parquet
├── coeficientes_regresion.csv
└── metricas_modelos.csv
```

## 1. XGBoost: `models/shap_alumnos.parquet`

Los valores SHAP **de cada alumno**, promediados entre los modelos de los valores plausibles de su edición. No sirve un SHAP medio global por variable: el agente tiene que poder agrupar a los alumnos por tipo de centro, origen social, etc.

Una fila por alumno `en_modelo`:

| columna | contenido |
|---|---|
| `CNT`, `year`, `CNTSCHID`, `CNTSTUID` | identificadores, para unirla con `tabla_modelo_alumno.parquet` |
| `valor_base` | media de los valores base (`expected_value`) de los modelos de su edición |
| `prediccion` | media de las predicciones de los modelos de su edición |
| `shap_<variable>` | una columna por variable del modelo, con su nombre exacto (`shap_recursos_estudio`, `shap_perfil_categoria`...), en puntos de la nota de matemáticas |

- En cada fila, `valor_base` + la suma de las columnas `shap_` debe dar `prediccion`.
- Si una variable no está en el modelo de una edición, su columna `shap_` va vacía en esa edición.
- Indicar si los SHAP se calculan sobre todos los alumnos o solo sobre los de test.

## 2. Regresión: `models/coeficientes_regresion.csv`

Los resultados **ya combinados con las reglas de Rubin**: una regresión por valor plausible y, después, una sola fila por variable, edición y especificación. No hace falta pasar las regresiones de cada valor plausible.

| columna | contenido |
|---|---|
| `edicion` | 2012, 2015, 2018 o 2022 |
| `especificacion` | p. ej. `sin_controles`, `con_controles` (si solo hay una, siempre el mismo valor) |
| `tipo` | `principal` o `efecto_fijo_perfil` |
| `variable` | nombre exacto de la columna en la tabla, incluidos los indicadores `sin_<variable>`; en los efectos fijos, `perfil` |
| `perfil` | vacío en `principal`; en `efecto_fijo_perfil`, el perfil (`PUB_RUR_PEQ`...) |
| `coeficiente` | media de los coeficientes de los valores plausibles |
| `error_tipico` | agrupado por centro, con la varianza entre valores plausibles (Rubin); `03_errores_brr` comprueba que coincide casi del todo con el de pesos replicados (BRR) |
| `ic_inf`, `ic_sup` | intervalo de confianza al 95 % |
| `p_valor` | |
| `unidad` | `tipificada` u `original` |

Ejemplos de filas:

| tipo | variable | perfil | lectura |
|---|---|---|---|
| `principal` | `recursos_estudio` | | efecto de los recursos, el mismo en todos los perfiles |
| `efecto_fijo_perfil` | `perfil` | `PUB_RUR_PEQ` | diferencia de nota de ese perfil frente al de referencia, con lo demás igual |

- Indicar cuál es el perfil de referencia (el que no tiene fila de efecto fijo).
- Los efectos fijos de país-edición no hacen falta.

## 3. Métricas: `models/metricas_modelos.csv`

Una fila por modelo y edición, con la media de las métricas de los valores plausibles:

| columna | contenido |
|---|---|
| `edicion` | 2012, 2015, 2018 o 2022 |
| `modelo` | `regresion` o `xgboost` |
| `conjunto` | `test`, `validacion_cruzada`, ... |
| `r2`, `rmse`, `mae` | |
| `n_alumnos` | |

## Además

- Indicar los pesos usados (`SENWT`).

## Cómo se generan

| fichero | lo genera |
|---|---|
| `coeficientes_regresion.csv` | `notebooks/fase_3_modelado/03_regresion_por_edicion`, sección 5 |
| `shap_alumnos.parquet` | `notebooks/fase_3_modelado/03_xgboost_shap`, sección 6 |
| `metricas_modelos.csv` | `notebooks/fase_3_modelado/03_xgboost_shap`, secciones 2 y 6 |

- **Pesos**: `SENWT` en los dos modelos, en las métricas y en los SHAP.
- **SHAP**: los modelos se entrenan con todos los alumnos `en_modelo` de la edición y los SHAP se calculan sobre todos ellos, no solo sobre los de test.
- **Regresión**:
  - Dos especificaciones: `pendiente_comun` (una pendiente de cada variable de interés para todos los perfiles) y `pendiente_por_perfil` (una pendiente de cada variable de interés en cada perfil).
  - Perfil de referencia: `PUB_URB_MED`, el que tiene más centros. No tiene fila de `efecto_fijo_perfil`.
  - Un tercer valor de `tipo`, `pendiente_perfil`, para las pendientes por perfil de `pendiente_por_perfil`: `variable` es la variable de interés y `perfil`, el perfil (los 15, también el de referencia). En esta especificación, las variables de interés no tienen fila `principal`.
  - Las variables tipificadas tienen una fila `tipificada` (puntos por desviación típica, como se estima el modelo) y otra `original` (puntos por unidad de la variable). La constante y las variables de 0 o 1 solo tienen la `original`.
  - Columnas añadidas a las de la guía: `porcentaje_varianza_entre_pv`, `valores_plausibles`, `alumnos` (del perfil-edición en las filas con perfil; de la edición en el resto) y `poco_representativo` (perfil-edición con menos de 30 centros).
- **Métricas**: `conjunto` = `validacion_cruzada`, los alumnos de prueba de 5 pliegues separados por centro. `rmse` y `mae` en puntos de matemáticas. Columna añadida: `valores_plausibles`.
- **Robustez**: las comprobaciones de robustez de la regresión no están en esta carpeta, sino en `data/processed/resultados_robustez.parquet` (`03_robustez_regresion`).
