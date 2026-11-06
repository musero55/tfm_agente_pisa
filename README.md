# Compromiso, recursos y nota en PISA (2012-2022) - Trabajo Fin de Máster

**Pregunta del TFM**: cómo ha cambiado entre 2012 y 2022 la relación del compromiso del alumno y de sus recursos de estudio con su nota de matemáticas, según el perfil de su centro.

* **Datos**: microdatos de PISA 2012, 2015, 2018 y 2022, en un panel de 12 países con el índice de compromiso en las cuatro ediciones (AUS, DNK, ESP, GBR, GRC, HUN, ISL, ITA, KOR, POL, SVK y SVN). Un panel ampliado de 25 países, sin 2018, sirve de comprobación.
* **Variables de interés**: el índice de compromiso y competencia (tiempo de deberes, absentismo e impuntualidad) y los recursos de estudio del hogar (seis objetos).
* **Perfiles de centro**: 18 combinaciones fijas de titularidad, ubicación y tamaño.
* **Modelos**: regresión lineal por edición con efecto fijo de país, ponderada con `SENWT`, con errores agrupados por centro y los valores plausibles combinados con las reglas de Rubin. XGBoost con SHAP sirve de contraste.

---

## Puesta en marcha

1. **Python 3.12 o superior.** Las dependencias usan pandas 3 y numpy 2.
2. **Entorno con las versiones de `requirements.txt`**. Los resultados guardados se obtuvieron con esas versiones exactas, así que conviene no usar otro Python. Se crea un entorno `.venv` en la raíz y se registra como kernel `tfm_env`, que es el que tienen asignado todos los notebooks:
   ```bash
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements.txt
   .venv/Scripts/python -m ipykernel install --user --name tfm_env --display-name tfm_env
   ```
   En Linux o macOS la ruta es `.venv/bin/python`. Desde VS Code o Jupyter, el kernel que hay que elegir es `tfm_env`.
3. **Datos de partida.** La carpeta `data/raw/` no se entrega, porque pesa más de 10 GB. Hay que descargarla de la OCDE (siguiente sección).
4. **Ejecutar los notebooks en orden** (sección «Orden de los notebooks»). Cada uno lee las tablas que guardan los anteriores.

---

## Datos de partida: descarga de `data/raw/`

Los microdatos de PISA son públicos y se descargan gratis de la web de la OCDE. En cada página de edición, el botón «Download the datasets» lleva a un formulario breve de la OCDE y, tras rellenarlo, a la descarga de los ficheros:

* [PISA 2012](https://www.oecd.org/en/data/datasets/pisa-2012-database.html)
* [PISA 2015](https://www.oecd.org/en/data/datasets/pisa-2015-database.html)
* [PISA 2018](https://www.oecd.org/en/data/datasets/pisa-2018-database.html)
* [PISA 2022](https://www.oecd.org/en/data/datasets/pisa-2022-database.html)

De cada edición hacen falta dos ficheros, el **cuestionario del alumno** (que incluye las notas) y el **cuestionario del centro**, en formato SAS (2012 se convierte antes, ver abajo). Se guardan así:

| Edición | Ficheros | Carpeta |
|---|---|---|
| 2012 | `INT_STU12_DEC03.sav` y `INT_SCQ12_DEC03.sav` | `data/raw/2012/` |
| 2015 | `cy6_ms_cmb_stu_qqq.sas7bdat` y `cy6_ms_cmb_sch_qqq.sas7bdat` | `data/raw/2015/` |
| 2018 | `cy07_msu_stu_qqq.sas7bdat` y `cy07_msu_sch_qqq.sas7bdat` | `data/raw/2018/` |
| 2022 | `CY08MSP_STU_QQQ.SAS7BDAT` y `CY08MSP_SCH_QQQ.SAS7BDAT` | `data/raw/2022/` |

El pipeline busca en cada carpeta el único `.sas7bdat` o `.sav` cuyo nombre contiene una parte fija (`stu12` y `scq12` en 2012; `stu_qqq` y `sch_qqq` en las demás), sin distinguir mayúsculas, así que vale con no cambiar el nombre original.

**2012 se convierte antes.** La OCDE da los datos de 2012 como texto de ancho fijo (`.txt`), comprimido en `INT_STU12_DEC03.zip` y `INT_SCQ12_DEC03.zip`, con un script SAS por fichero que describe las columnas (`PISA2012_SAS_student.sas` y `PISA2012_SAS_school.sas`). Esos cuatro ficheros (los `.zip`, o los `.txt` ya descomprimidos, y los dos `.sas`) se dejan en `data/raw/2012/` y, desde la raíz del proyecto, se ejecuta:

```bash
.venv/Scripts/python -m src.pisa_txt_a_sav
```

`convertir_txt_a_sav` busca los ficheros en `data/raw/2012/` y, para alumnos y para centros por separado:

* si el `.sav` ya existe, avisa de que no hace falta hacer nada;
* si están los originales, genera el `.sav` y después los borra;
* si faltan, lanza un aviso con los que hay que descargar.

Además, en la raíz de `data/raw/`:

* **`escs_trend.csv`**: índices socioeconómicos reescalados por la OCDE para comparar ediciones. Está en la página de PISA 2022, apartado «Rescaled indices for trend analyses» ([`escs_trend.zip`](https://webfs.oecd.org/pisa2022/escs_trend.zip)); se descomprime en `data/raw/`.
* **`pisa_mathematics_2000_2022.csv`, `pisa_reading_2000_2022.csv` y `pisa_science_2000_2022.csv`**: medias por país publicadas por la OCDE. Solo las usa la sección 1 de `01_EDA_notas_asignatura`.

No hace falta descargar nada más:

* **`data/raw/datos_anuales/`** (las tablas maestras) la genera el primer notebook, `00_pipeline_multiedicion_PISA`.
* **`data/raw/externos/`** (Gini, gasto educativo y datos macroeconómicos) la descargan solos `01_EDA_equidad` y los notebooks del anexo, desde las APIs públicas de la OCDE, el Banco Mundial y Eurostat (`src/datos_externos.py`).

**Qué se puede ejecutar sin `data/raw/`.** Las tablas intermedias (`data/intermediate/`), la tabla del modelo (`data/processed/`) y los resultados (`models/`) sí se entregan. Con ellas se ejecutan `03_regresion_por_edicion` y `03_xgboost_shap`, y funciona el agente. Los notebooks de la fase 1, `02_preparacion_modelo`, `03_errores_brr` y `03_robustez_regresion` leen las tablas maestras de `data/raw/datos_anuales/` y necesitan haber descargado los microdatos.

---

## Orden de los notebooks

Los notebooks están en `notebooks/`, por fases. Este es el orden de ejecución, el mismo que recoge `00_pipeline_multiedicion_PISA` («Orden de los notebooks»):

| Paso | Notebook | Qué hace |
|---|---|---|
| 1 | `fase_1_data_ingestion_eda/00_pipeline_multiedicion_PISA` | Tablas maestras de alumnos y centros por edición |
| 2 | `fase_1_data_ingestion_eda/00_Pipeline_generacion_estratos` | Perfil fijo de cada centro: titularidad, ubicación y tamaño |
| 3 | `fase_1_data_ingestion_eda/01_EDA_notas_asignatura` | Nota media por centro y por país; reparto de la varianza de la nota |
| 4 | `fase_1_data_ingestion_eda/01_EDA_equidad` | Desigualdad social y de recursos; `ESCS` medio y recursos de cada centro |
| 5 | `fase_1_data_ingestion_eda/01_EDA_recursos_alumno` | Subíndice de recursos de estudio del hogar |
| 6 | `fase_1_data_ingestion_eda/01_EDA_indice_de_compromiso_competencia` | Índice de compromiso y panel de 12 países (y el ampliado de 25) |
| 7 | `fase_1_data_ingestion_eda/01_EDA_recursos_centro` | Dotación y escasez del centro, que entran como controles |
| 8 | `fase_1_data_ingestion_eda/01_EDA_variables_modelo` | Alumnos del panel y huecos de las variables del modelo |
| 9 | `fase_2_feature_engineering/02_preparacion_modelo` | Tabla del modelo, en `data/processed/` |
| 10 | `fase_3_modelado/03_regresion_por_edicion` | Modelo principal; guarda los coeficientes en `models/` |
| 11 | `fase_3_modelado/03_errores_brr` | Errores típicos con los 80 pesos replicados de PISA (BRR) |
| 12 | `fase_3_modelado/03_robustez_regresion` | Comprobaciones de robustez: medida del compromiso, efecto techo, controles, panel ampliado, quitar cada país, no respuesta, pendiente por país y efecto fijo país × perfil |
| 13 | `fase_3_modelado/03_xgboost_shap` | XGBoost con SHAP; guarda los SHAP y las métricas en `models/` |

Los notebooks tienen una estructura común: una cabecera con la pregunta que responden, secciones numeradas, una observación («Qué se ve») después de cada resultado y unos hallazgos al final, con el notebook siguiente.

---

## Estructura del proyecto

```text
tfm_data_science/
├── data/
│   ├── raw/            # Microdatos y ficheros originales (no se entregan; ver «Datos de partida»)
│   ├── intermediate/   # Tablas intermedias de los EDA (.parquet); ver data/intermediate/README.md
│   └── processed/      # Tabla del modelo, parámetros de escala, diccionario y resultados de robustez
├── notebooks/
│   ├── fase_1_data_ingestion_eda/
│   ├── fase_2_feature_engineering/
│   └── fase_3_modelado/
├── src/                # Funciones comunes que usan los notebooks
├── models/             # Resultados que lee el agente: coeficientes, SHAP y métricas (ver models/README.md)
├── reports/            # Figuras que guardan los notebooks
├── agente_pisa/        # Agente conversacional que responde preguntas sobre los resultados
├── anexo/              # Trabajo previo que se conserva: bloque exploratorio de 33 países y primer modelo por estrato
└── requirements.txt
```

Funciones principales de `src/`:

* `pisa_pipeline.py`: lectura y validación de las tablas maestras.
* `pisa_estadisticas.py`: medias ponderadas, valores plausibles y reparto de la varianza.
* `recursos_alumno.py`, `recursos_centro.py` y `tabla_alumno.py`: construcción de las variables y de la tabla por alumno.
* `preparacion_modelo.py`: perfiles, escala y matrices de los modelos.
* `modelo_regresion.py`: regresión por edición, reglas de Rubin y contrastes.

---

## Convenciones

* **Pesos**: `SENWT` (cada país suma 5.000) en las cifras que juntan países; `W_FSTUWT` dentro de un país.
* **Valores plausibles**: las estimaciones se hacen con cada uno por separado y se combinan con las reglas de Rubin (10 valores plausibles; 5 en 2012).
* **Nombres**: las columnas originales de PISA se mantienen en mayúsculas (`CNT`, `W_FSTUWT`, `PV1MATH`); las columnas nuevas van en minúsculas y *snake_case*.
* **Rutas**: los notebooks están dos niveles por debajo de la raíz, así que leen `../../data/` y añaden `../../` a `sys.path` para importar `src`.
