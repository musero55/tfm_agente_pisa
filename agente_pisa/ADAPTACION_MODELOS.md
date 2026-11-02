# Adaptación de los resultados del modelado

## Qué ha pasado

Los resultados que hay en `models/` (commit `0f02e7f`) son correctos, pero la tabla de la regresión tiene otro formato, explicado en [models/README.md](../models/README.md).

En lugar de pedir que se rehaga, `preparar_artefactos.py` la traduce al formato del agente. El fichero original de `models/` no se toca.

| fichero | qué se hace |
|---|---|
| `shap_alumnos.parquet` | nada: coincide con la guía |
| `metricas_modelos.csv` | solo se renombra el modelo `regresion` → `regresion_por_perfil` (es la que se evaluó) |
| `coeficientes_regresion.csv` | se traduce (ver abajo) |

## La regresión: lo que entregó el modelado

Dos regresiones por edición, en la columna `especificacion`:

- `pendiente_comun`: compromiso, recursos y controles tienen **un solo coeficiente** para todos los perfiles. En el agente se llama `comun`.
- `pendiente_por_perfil`: compromiso y recursos tienen **un coeficiente distinto en cada perfil**. Los controles siguen con uno solo.

Dentro de cada regresión, la columna `tipo` dice qué clase de número es cada fila:

| `tipo` | qué es |
|---|---|
| `principal` | coeficiente de una variable, el mismo en todos los perfiles |
| `pendiente_perfil` | coeficiente de compromiso o recursos dentro de un perfil concreto |
| `efecto_fijo_perfil` | cuánto más alta o más baja parte la nota de un perfil frente al de referencia (`PUB_URB_MED`) |

Además, casi cada variable sale dos veces: en unidades `tipificada` y `original`.

## Cómo queda para el agente

`artefactos/coeficientes_regresion.csv`, una fila por edición, regresión, estrato y variable:

| `regresion` | `estrato` | de dónde sale |
|---|---|---|
| `comun` | `todos` | filas `principal` de `pendiente_comun` (variables de interés, controles e indicadores `sin_<variable>`) |
| `comun` | el perfil | filas `efecto_fijo_perfil` de `pendiente_comun`, con `variable = efecto_perfil`: punto de partida de cada perfil frente a `PUB_URB_MED`, con lo demás igual (14 perfiles) |
| `por_perfil` | el perfil (`PUB_RUR_PEQ`...) | filas `pendiente_perfil` de `pendiente_por_perfil`: compromiso y recursos, los 15 perfiles |

Columnas: `edicion`, `regresion`, `estrato`, `variable`, `coeficiente`, `error_tipico`, `ic_inf`, `ic_sup`, `p_valor`, `unidad`, `coeficiente_dt`, `n_alumnos`, `poco_representativo`.

Lo que se descarta:

- La constante: sin los efectos fijos de país (no se guardaron) no corresponde a la nota de ningún país.
- Los efectos fijos de perfil de `pendiente_por_perfil`: allí cada perfil tiene su propia inclinación, así que la distancia entre perfiles depende de los recursos del alumno y no es una cifra única.
- Las filas `tipificada` como filas aparte: se deja la unidad `original`, la misma que `alumnos_modelo.parquet`, y el coeficiente tipificado pasa a la columna `coeficiente_dt` (vacía en las variables de 0 o 1 y en los efectos de perfil). Sirve para comparar variables entre sí.
- Los controles de `pendiente_por_perfil`: ya están en la común.

## Diferencias con lo que pedía la guía

La guía pedía una regresión «global» sin perfiles. El agente usa en su lugar la de coeficiente común de Alberto, con su mismo nombre (`comun`), porque responde mejor a la pregunta del TFM. Cómo se lee cada coeficiente está en [metodologia/modelos.md](metodologia/modelos.md).

1. **La común lleva efecto fijo de perfil y de país.** Su coeficiente compara alumnos del mismo país y del mismo perfil de centro, y es el mismo en todos los perfiles.
2. **La por perfil solo tiene compromiso y recursos.** Para la pregunta del TFM basta: esas dos son las de interés. No hay término general, así que cada coeficiente es el del perfil.
3. **No hay `n_centros`.** En su lugar está `poco_representativo`: `True` si el perfil tiene menos de 30 centros en esa edición.
4. **Métricas:** solo de la regresión por perfil, no de la común.
