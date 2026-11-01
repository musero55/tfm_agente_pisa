# Entrega de los modelos

Todo va en la carpeta `models/`, en la raíz del repositorio. Regresiones por edición, por estrato y de comprobación, y un XGBoost por edición, estimados con cada valor plausible de matemáticas (10 por edición; 5 en 2012). El agente no carga ningún modelo: solo estas tres tablas.

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

**Todas las regresiones en una sola tabla**: por edición, por estrato y las de comprobación. Cada regresión se estima con cada valor plausible y se combina con las reglas de Rubin; no hace falta pasar las de cada valor plausible.

Una fila por coeficiente. Las tres primeras columnas dicen de qué regresión sale:

| columna | contenido |
|---|---|
| `edicion` | 2012, 2015, 2018, 2022, o `todas` si la regresión junta ediciones |
| `estrato` | `todos` (regresión con todos los alumnos) o el perfil de la regresión de ese estrato (`PUB_RUR_PEQ`...) |
| `especificacion` | `principal` o el nombre de la comprobación: `sin_2018`, `sin_deberes_indice`... |
| `tipo` | `variable` o `efecto_fijo_perfil` |
| `variable` | nombre exacto de la columna en la tabla, incluidos los indicadores `sin_<variable>`; en los efectos fijos, `perfil` |
| `perfil` | vacío en `variable`; en `efecto_fijo_perfil`, el perfil (`PUB_RUR_PEQ`...) |
| `coeficiente` | media de los coeficientes de los valores plausibles |
| `error_tipico` | agrupado por centro, con la varianza entre valores plausibles (Rubin) |
| `ic_inf`, `ic_sup` | intervalo de confianza al 95 % |
| `p_valor` | |
| `unidad` | `tipificada` u `original` |
| `n_alumnos`, `n_centros` | tamaño de la regresión de la que sale el coeficiente (el mismo en todas sus filas) |

Ejemplos de filas:

| edicion | estrato | especificacion | tipo | variable | perfil | lectura |
|---|---|---|---|---|---|---|
| 2022 | `todos` | `principal` | `variable` | `recursos_estudio` | | efecto de los recursos en 2022, con todos los alumnos |
| 2022 | `todos` | `principal` | `efecto_fijo_perfil` | `perfil` | `PUB_RUR_PEQ` | diferencia de nota de ese perfil frente al de referencia, con lo demás igual |
| 2022 | `PUB_RUR_PEQ` | `principal` | `variable` | `recursos_estudio` | | efecto de los recursos en 2022 solo en ese estrato |
| `todas` | `todos` | `sin_2018` | `variable` | `recursos_estudio` | | comprobación: ediciones juntas, sin 2018 |
| 2022 | `todos` | `sin_deberes_indice` | `variable` | `recursos_estudio` | | comprobación: sin las horas de deberes ni el índice de compromiso |

- Indicar cuál es el perfil de referencia de los efectos fijos (el que no tiene fila).
- Explicar en una línea cada especificación de comprobación (qué quita o qué cambia).
- Los efectos fijos de país no hacen falta.

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
