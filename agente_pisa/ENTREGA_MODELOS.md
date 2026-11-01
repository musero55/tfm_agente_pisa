# Entrega de los modelos

Todo va en la carpeta `models/`, en la raíz del repositorio. Dos regresiones (global y por perfil de centro) y un XGBoost por edición, estimados con cada valor plausible de matemáticas (10 por edición; 5 en 2012). El agente no carga ningún modelo: solo estas tres tablas.

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

Las dos regresiones en una sola tabla, cada una estimada con cada valor plausible y combinada con las reglas de Rubin (no hace falta pasar las de cada valor plausible):

- **Global**: sin perfiles de centro; una pendiente por variable para todos los alumnos.
- **Por perfil** (la larga): cada variable multiplicada por el indicador de cada perfil, así que cada coeficiente es la pendiente de esa variable dentro de ese perfil.

Una fila por coeficiente:

| columna | contenido |
|---|---|
| `edicion` | 2012, 2015, 2018, 2022, o `todas` si la regresión junta ediciones |
| `regresion` | `global` o `por_perfil` |
| `estrato` | `todos` en la global; en la larga, el perfil del coeficiente (`PUB_RUR_PEQ`...) |
| `variable` | nombre exacto de la columna en la tabla (`recursos_estudio`...), **sin el sufijo del perfil**, incluidos los indicadores `sin_<variable>` |
| `coeficiente` | media de los coeficientes de los valores plausibles |
| `error_tipico` | agrupado por centro, con la varianza entre valores plausibles (Rubin) |
| `ic_inf`, `ic_sup` | intervalo de confianza al 95 % |
| `p_valor` | |
| `unidad` | `tipificada` u `original` |
| `n_alumnos`, `n_centros` | en la global, los de la regresión; en la larga, los del perfil |

Ejemplos de filas:

| edicion | regresion | estrato | variable | lectura |
|---|---|---|---|---|
| 2022 | `global` | `todos` | `recursos_estudio` | efecto de los recursos en 2022, con todos los alumnos |
| 2022 | `por_perfil` | `PUB_RUR_PEQ` | `recursos_estudio` | efecto de los recursos en 2022 en ese perfil (el coeficiente de `recursos_estudio × es_PUB_RUR_PEQ`) |
| 2022 | `por_perfil` | `CON_URB_MED` | `recursos_estudio` | efecto de los recursos en 2022 en ese perfil |

- En la larga, confirmar que cada variable va **solo** multiplicada por los perfiles, sin un término general además. Si lo hay, avisar: entonces cada coeficiente sería la diferencia frente a un perfil de referencia, no la pendiente del perfil.
- Las constantes de cada perfil, los efectos fijos de país y las regresiones de comprobación no hacen falta.

## 3. Métricas: `models/metricas_modelos.csv`

Una fila por modelo y edición, con la media de las métricas de los valores plausibles:

| columna | contenido |
|---|---|
| `edicion` | 2012, 2015, 2018 o 2022 |
| `modelo` | `regresion_global`, `regresion_por_perfil` o `xgboost` |
| `conjunto` | `test`, `validacion_cruzada`, ... |
| `r2`, `rmse`, `mae` | |
| `n_alumnos` | |

## Además

- Indicar los pesos usados (`SENWT`).
