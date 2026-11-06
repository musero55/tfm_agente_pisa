"""
Genera en agente_pisa/artefactos/ todo lo que consume el agente en tiempo de ejecución.

Uso (desde la raíz del repositorio, con el entorno tfm_env):
    python agente_pisa/preparar_artefactos.py

Ficheros generados:
    alumnos_modelo.parquet   Alumnos que entran en el modelo (en_modelo), con la nota de matemáticas, las variables
                             de interés y de control en sus unidades originales y los estratos fijos desglosados.
    catalogo_graficos.csv    Imágenes estáticas que el agente puede mostrar.
    img/                     PNG copiados de reports/ y referenciados en el catálogo.


Resultados de los modelos, solo si existen en models/ (formato en models/README.md):
    shap_alumnos.parquet       SHAP del XGBoost de cada alumno, medio entre valores plausibles.
    coeficientes_regresion.csv Regresión por edición, combinada con las reglas de Rubin, traducida al formato del
                               agente (README_ARQUITECTURA.md, sección 9).
    metricas_modelos.csv       R², RMSE y MAE por modelo y edición.
"""
import shutil

import numpy as np
import pandas as pd

from config import (
    CORTES_COMPROMISO, CORTES_RECURSOS, DIR_ARTEFACTOS, DIR_IMAGENES_MACRO, FUENTES, PAISES_PANEL,
    RUTA_ALUMNOS, RUTA_CATALOGO_GRAFICOS, RUTA_COEFICIENTES, RUTA_CONDUCTAS, RUTA_METRICAS, RUTA_SHAP, TAMANOS, TIPOS_CENTRO, UBICACIONES, VARIABLES_NUMERICAS,
)

# Gráficos de reports/ que se ofrecen como contexto.
# Edita esta lista para añadir o quitar imágenes; la descripción es lo que lee el agente para elegirla.

GRAFICOS_ESTRATOS = [
    ("estratos_tamano_centros", "00_estratos_tamano_centros_titularidad_ubicacion.png",
     "Ejemplo de distribución del tamaño de los centros españoles por titularidad y ubicación, con los cortes pequeño / mediano / macro"),
    ("estratos_colegios_edicion", "00_estratos_colegios_por_estrato_edicion.png",
     "Número de colegios en cada estrato fijo (perfil de centro) y su comparación entre ediciones 2012-2022"),
]

GRAFICOS_COMPROMISO = [
    ("compromiso_distribucion_2022", "01_compromiso_distribucion_indicadores_2022.png",
     "Distribución de los tres indicadores del índice de compromiso (horas de deberes, absentismo e impuntualidad) en PISA 2022"),
    ("compromiso_por_estrato_2022", "01_compromiso_indicadores_por_estrato_2022.png",
     "Horas de deberes, absentismo e impuntualidad por estrato de titularidad y ubicación (PISA 2022)"),
    ("compromiso_indicadores_2012", "01_compromiso_indicadores_2012.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2012"),
    ("compromiso_indicadores_2015", "01_compromiso_indicadores_2015.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2015"),
    ("compromiso_indicadores_2018", "01_compromiso_indicadores_2018.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2018 (edición con huecos en deberes)"),
    ("compromiso_disponibilidad", "01_compromiso_disponibilidad_pais_edicion.png",
     "Disponibilidad de cada variable del índice de compromiso por país y edición, y países que forman el panel común"),
    ("compromiso_titularidad_ubicacion", "01_compromiso_indice_por_titularidad_ubicacion_2022.png",
     "Índice de compromiso y competencia por titularidad y ubicación del centro (PISA 2022)"),
    ("compromiso_espana_vs_panel", "01_compromiso_indice_alumno_espana_vs_panel_2022.png",
     "Reparto de alumnos por nivel del índice de compromiso y competencia: España frente al resto del panel (PISA 2022)"),
    ("compromiso_evolucion", "01_compromiso_evolucion_indice.png",
     "Evolución del índice de compromiso y competencia 2012-2022, global y por titularidad, en el panel común de países"),
]

GRAFICOS_RECURSOS_CENTRO = [
    ("recursos_centro_evolucion_pais", "01_recursos_centro_evolucion_pais.png",
     "Media de cada recurso del centro (alumnos por profesor, tamaño de clase, ordenadores...) por país y edición"),
    ("recursos_centro_reparto_varianza", "01_recursos_centro_reparto_varianza.png",
     "En qué nivel varían los recursos del centro: entre países, ediciones, perfiles de centro, centros y alumnos"),
    ("recursos_centro_perfiles", "01_recursos_centro_perfiles.png",
     "Media de cada índice de recursos del centro por perfil de centro y edición"),
    ("recursos_centro_correlaciones_alumno", "01_recursos_centro_correlaciones_alumno.png",
     "Correlación de los recursos del centro con la composición social, el origen social, los recursos de estudio, el compromiso y la nota del alumno"),
    ("recursos_centro_asociacion_nota", "01_recursos_centro_asociacion_nota.png",
     "Puntos de matemáticas asociados a cada recurso del centro, dentro de cada país y edición, con y sin controles"),
    ("recursos_centro_escasez_2012", "01_recursos_centro_escasez_2012.png",
     "Índices de escasez de recursos del centro en 2012 y por qué no se comparan entre ediciones"),
]

GRAFICOS_VARIABLES_MODELO = [
    ("variables_modelo_huecos", "01_variables_modelo_huecos.png",
     "Diferencia de nota entre los alumnos sin dato y con dato en cada variable del modelo, relativa a su país y edición"),
]

# Modelado (notebooks/fase_3_modelado). Los gráficos de la regresión están en puntos por desviación típica; las
# herramientas del agente, en unidades originales (metodologia/modelos.md, «Unidades»)
GRAFICOS_MODELADO = [
    # 03_regresion_por_edicion: el modelo principal
    ("regresion_coeficiente_comun", "03_regresion_pendiente_comun.png",
     "Regresión: coeficiente común de compromiso y recursos de estudio en cada edición 2012-2022, con intervalo del "
     "95 % (puntos por desviación típica, comparando alumnos del mismo país y origen social)"),
    ("regresion_coeficientes_perfil", "03_regresion_pendientes_perfil.png",
     "Regresión: coeficiente de compromiso y de recursos de estudio en cada perfil de centro y edición, con intervalo "
     "del 95 % (puntos por desviación típica); los puntos huecos son perfiles con menos de 30 centros"),
    ("regresion_cambio_perfil", "03_regresion_cambio_perfil.png",
     "Regresión: cambio de 2012 a 2022 del coeficiente de compromiso y de recursos en cada perfil de centro, con "
     "intervalo del 95 % (puntos por desviación típica); destaca la subida de los recursos en el privado urbano grande, "
     "que depende de Australia"),
    # 03_robustez_regresion: qué resultados aguantan
    ("robustez_resumen", "03_robustez_resumen.png",
     "Robustez: cambio de 2012 a 2022 del coeficiente del compromiso, de los recursos y de los recursos en el privado "
     "urbano grande en cada comprobación (otros controles, panel de 25 países, sin Australia, España, Reino Unido o Corea)"),
    ("robustez_sin_cada_pais", "03_robustez_sin_cada_pais.png",
     "Robustez: p-valor de los contrastes «los perfiles de centro son iguales» al quitar cada país, en el panel común y "
     "en el ampliado; solo sin Australia los recursos dejan de diferir entre perfiles en el panel común"),
    ("robustez_asistencia_panel_ampliado", "03_robustez_asistencia_panel_ampliado.png",
     "Robustez: coeficiente común del absentismo, la impuntualidad y los recursos de estudio por edición, en el panel "
     "común de 12 países y en el ampliado de 25"),
    ("robustez_techo_recursos", "03_robustez_techo_recursos.png",
     "Robustez: porcentaje de alumnos con los seis recursos de estudio (efecto techo) por perfil de centro y edición"),
    # 03_australia_privados_grandes: el privado urbano grande depende de Australia
    ("australia_coeficiente_recursos", "03_australia_pendientes.png",
     "Australia: coeficiente de los recursos de estudio en sus privados urbanos grandes, en toda Australia y en los "
     "otros 11 países, por edición (puntos por desviación típica). El salto de 2022 del privado urbano grande viene de "
     "Australia: no es un rasgo general de estos centros (nota de perfiles de centro)"),
    ("australia_nota_por_tramo", "03_australia_nota_por_tramo.png",
     "Australia: nota media de matemáticas según los recursos de estudio (los seis, falta uno, faltan dos o más) en sus "
     "privados urbanos grandes y en el resto del país, por edición (medias sin controles)"),
    # 03_errores_brr: validación de los errores típicos
    ("errores_brr_comparacion", "03_errores_brr_comparacion.png",
     "Errores típicos de los coeficientes por perfil: agrupados por centro frente a pesos replicados de PISA (BRR); "
     "casi coinciden"),
    # 03_xgboost_shap: comprobación con XGBoost y SHAP
    ("xgboost_importancia", "03_xgboost_importancia.png",
     "XGBoost: importancia de cada variable en la predicción (media del valor absoluto del SHAP, en puntos) por edición"),
    ("xgboost_forma_relacion", "03_xgboost_forma_relacion.png",
     "XGBoost: forma de la relación del compromiso y de los recursos de estudio con la nota (SHAP medio por valor) "
     "frente a la recta de la regresión; muestra el efecto techo de los recursos"),
    ("xgboost_coeficientes_perfil", "03_xgboost_pendientes_perfil.png",
     "XGBoost frente a regresión: coeficiente de compromiso y de recursos en cada perfil y edición (puntos por unidad); "
     "XGBoost no reproduce el salto del privado urbano grande"),
]

# 01_EDA_recursos_alumno: cómo se forma el índice de recursos de estudio. Están calculados con los 33 países de la
# OCDE de los datos, no con el panel de 12: la descripción lo dice para que el agente no los presente como del panel.
GRAFICOS_RECURSOS_ALUMNO = [
    ("recursos_alumno_saturacion", "01_recursos_alumno_saturacion.png",
     "Recursos de estudio: porcentaje de alumnos que tiene cada objeto de estudio en casa, por edición, incluidos los "
     "que se dejan fuera del índice (escritorio y sitio tranquilo, sin dato en 2022; software educativo). Casi todos "
     "tienen la mayoría. 33 países de la OCDE, cada país pesa igual"),
    ("recursos_alumno_subindice_estudio", "01_recursos_alumno_subindice_estudio.png",
     "Índice de recursos de estudio: porcentaje de alumnos con 0 a 6 de los seis recursos (habitación, ordenador, "
     "internet, libros de ayuda, libros técnicos y diccionario), por edición; la mayoría tiene 5 o 6. 33 países de la "
     "OCDE, cada país pesa igual"),
    ("recursos_alumno_reparto_varianza", "01_recursos_alumno_reparto_varianza.png",
     "Reparto de la varianza de los recursos de estudio, la riqueza del hogar, los libros, las notas y el nivel "
     "socioeconómico: entre países, ediciones, centros y alumnos; los recursos varían sobre todo entre alumnos del "
     "mismo centro (75 %). 33 países de la OCDE, 2012-2022"),
    ("recursos_alumno_nota", "01_recursos_alumno_asociacion_nota.png",
     "Asociación de los recursos de estudio, la riqueza del hogar y los libros con la nota dentro de cada país y "
     "edición, solos y con el origen social (puntos por desviación típica). Incluye lectura y ciencias, pero el "
     "estudio usa solo matemáticas. 33 países de la OCDE"),
]

COLUMNAS = ["CNT", "CNTSCHID", "CNTSTUID", "year", "perfil", "SENWT", "W_FSTUWT", "sexo_femenino", "inmigrante",
            "tiempo_deberes_totales_diarios", "perfil_poco_representativo",
            "SKIPPING", "TARDYSD", "deberes_en_u"] + \
           [c for c in VARIABLES_NUMERICAS if c != "nota"]



def preparar_alumnos() -> pd.DataFrame:
    """Alumnos en_modelo con la nota de matemáticas (media de sus valores plausibles) y columnas descriptivas."""
    tabla = pd.read_parquet(FUENTES["tabla_modelo"])
    alumnos = tabla[tabla["en_modelo"]].copy()

    pvs = [c for c in alumnos.columns if c.startswith("PV") and c.endswith("MATH")]
    alumnos["nota"] = alumnos[pvs].mean(axis=1)   # 2012 tiene 5 PV y el resto 10: la media ignora los vacíos
    alumnos = alumnos[COLUMNAS + ["nota"]]

    # Estratos fijos desglosados a partir del código de perfil (p. ej. PUB_URB_MED)
    partes = alumnos["perfil"].str.split("_", expand=True)
    alumnos["tipo_centro"] = partes[0].map(TIPOS_CENTRO)
    alumnos["ubicacion"] = partes[1].map(UBICACIONES)
    alumnos["tamano"] = partes[2].map(TAMANOS)
    assert alumnos[["tipo_centro", "ubicacion", "tamano"]].notna().all().all(), "Perfil con códigos desconocidos"

    # Niveles descriptivos de las variables de interés y de los controles del alumno
    for columna, origen, (cortes, niveles) in [("nivel_compromiso", "Indice_Compromiso_Competencia", CORTES_COMPROMISO),
                                               ("nivel_recursos", "recursos_estudio", CORTES_RECURSOS)]:
        alumnos[columna] = pd.cut(alumnos[origen], bins=cortes, labels=niveles, right=False)
    alumnos["sexo"] = alumnos["sexo_femenino"].map({1.0: "Chica", 0.0: "Chico"})
    alumnos["origen"] = alumnos["inmigrante"].map({1.0: "Inmigrante", 0.0: "Nativo"})

    # Deja las columnas con el tipo correcto
    for columna in ["CNT", "perfil", "tipo_centro", "ubicacion", "tamano", "sexo", "origen"]:
        alumnos[columna] = alumnos[columna].astype("category")
    numericas = alumnos.select_dtypes("float64").columns
    alumnos[numericas] = alumnos[numericas].astype(np.float32)

    assert sorted(alumnos["CNT"].unique()) == sorted(PAISES_PANEL), "Los países no coinciden con el panel común"
    return alumnos.drop(columns=["sexo_femenino", "inmigrante"]).reset_index(drop=True)


def copiar_graficos() -> pd.DataFrame:
    filas = []
    for id_grafico, fichero, descripcion in (GRAFICOS_ESTRATOS + GRAFICOS_COMPROMISO + GRAFICOS_RECURSOS_ALUMNO + GRAFICOS_RECURSOS_CENTRO
                                           + GRAFICOS_VARIABLES_MODELO + GRAFICOS_MODELADO):
        origen = FUENTES["reports"] / fichero
        if not origen.exists():
            print(f"Aviso: no existe reports/{fichero}; se omite del catálogo.")
            continue
        shutil.copy2(origen, DIR_IMAGENES_MACRO / fichero)
        filas.append({"id": id_grafico, "tipo": "contexto", "ruta": f"img/{fichero}", "descripcion": descripcion})
    return pd.DataFrame(filas, columns=["id", "tipo", "ruta", "descripcion"])


# Columnas que deben traer los resultados del modelado (models/README.md)
CLAVES_ALUMNO = ["CNT", "year", "CNTSCHID", "CNTSTUID"]
TIPOS_CLAVES = {"CNT": str, "year": "int64", "CNTSCHID": "int64", "CNTSTUID": "int64"}   # para unir sin fallos de tipo
COLUMNAS_SHAP = CLAVES_ALUMNO + ["valor_base", "prediccion"]
# El modelado entregó la regresión con otro formato (models/README.md); se traduce al del agente (README_ARQUITECTURA.md, sección 9)
COLUMNAS_COEFICIENTES = ["edicion", "especificacion", "tipo", "variable", "perfil", "unidad", "coeficiente", "error_tipico",
                         "ic_inf", "ic_sup", "p_valor", "alumnos", "poco_representativo"]
COLUMNAS_METRICAS = ["edicion", "modelo", "conjunto", "r2", "rmse", "mae", "n_alumnos"]
N_PERFILES = 15


def _leer_resultado(clave: str, columnas: list[str]) -> pd.DataFrame | None:
    ruta = FUENTES[clave]
    if not ruta.exists():
        print(f"Aviso: no existe models/{ruta.name} ; se omite.")
        return None
    tabla = pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)
    faltan = [c for c in columnas if c not in tabla.columns]
    assert not faltan, f"{ruta.name}: faltan las columnas {faltan} (ver models/README.md)"
    return tabla


def preparar_shap(alumnos: pd.DataFrame) -> pd.DataFrame | None:
    """SHAP por alumno, comprobado (valor base + SHAP = predicción) y solo con los alumnos del agente."""
    shap = _leer_resultado("shap_alumnos", COLUMNAS_SHAP)
    if shap is None:
        return None
    columnas_shap = [c for c in shap.columns if c.startswith("shap_")]
    assert columnas_shap, "shap_alumnos.parquet: no hay columnas shap_<variable>"
    suma = shap["valor_base"] + shap[columnas_shap].sum(axis=1)   # sum() ignora los huecos de variables sin modelo
    desvio = (suma - shap["prediccion"]).abs().max()
    assert desvio < 0.5, f"shap_alumnos.parquet: valor base + SHAP difiere de la predicción hasta {desvio:.2f} puntos"
    assert not shap.duplicated(CLAVES_ALUMNO).any(), "shap_alumnos.parquet: alumnos repetidos"

    shap = shap[COLUMNAS_SHAP + columnas_shap].astype(TIPOS_CLAVES).merge(
        alumnos[CLAVES_ALUMNO].astype(TIPOS_CLAVES), on=CLAVES_ALUMNO, how="inner")
    if len(shap) < len(alumnos):
        print(f"Aviso: {len(alumnos) - len(shap)} alumnos del agente sin SHAP (¿solo se calcularon en test?).")
    numericas = shap.select_dtypes("float64").columns
    shap[numericas] = shap[numericas].astype(np.float32)
    return shap


def preparar_coeficientes() -> pd.DataFrame | None:
    """Traduce la regresión entregada a una fila por edición, regresión (comun o por_perfil), estrato y variable."""
    coeficientes = _leer_resultado("coeficientes_regresion", COLUMNAS_COEFICIENTES)
    if coeficientes is None:
        return None
    # Unidades originales (las de alumnos_modelo.parquet), con el coeficiente tipificado al lado para comparar variables
    # entre sí (vacío en las de 0 o 1 y en los efectos de perfil, que no se tipifican); fuera la constante
    claves = ["edicion", "especificacion", "tipo", "variable", "perfil"]
    tipificados = (coeficientes[coeficientes["unidad"] == "tipificada"][claves + ["coeficiente"]]
                   .rename(columns={"coeficiente": "coeficiente_dt"}))
    coeficientes = coeficientes[(coeficientes["unidad"] == "original") & (coeficientes["variable"] != "constante")]
    coeficientes = coeficientes.merge(tipificados, on=claves, how="left", validate="one_to_one")
    comun = coeficientes[coeficientes["especificacion"] == "pendiente_comun"]
    # Común: coeficientes de todas las variables, y el punto de partida de cada perfil frente a PUB_URB_MED
    # (solo de esta regresión: con coeficientes iguales en todos los perfiles, es una sola cifra por perfil)
    comunes = comun[comun["tipo"] == "principal"].assign(regresion="comun", estrato="todos")
    efectos_perfil = comun[comun["tipo"] == "efecto_fijo_perfil"].assign(regresion="comun", variable="efecto_perfil")
    efectos_perfil["estrato"] = efectos_perfil["perfil"]
    # Por perfil: solo los coeficientes por perfil (los controles ya están en la común)
    por_perfil = coeficientes[coeficientes["tipo"] == "pendiente_perfil"].assign(regresion="por_perfil")
    por_perfil["estrato"] = por_perfil["perfil"]
    tabla = pd.concat([comunes, efectos_perfil, por_perfil]).rename(columns={"alumnos": "n_alumnos"})
    tabla = tabla[["edicion", "regresion", "estrato", "variable", "coeficiente", "error_tipico", "ic_inf", "ic_sup",
                   "p_valor", "unidad", "coeficiente_dt", "n_alumnos", "poco_representativo"]].reset_index(drop=True)

    assert not tabla.duplicated(["edicion", "regresion", "estrato", "variable"]).any(), \
        "coeficientes_regresion.csv: coeficientes repetidos tras la traducción"
    perfiles = tabla[tabla["regresion"] == "por_perfil"].groupby(["edicion", "variable"])["estrato"].nunique()
    assert (perfiles == N_PERFILES).all(), f"coeficientes_regresion.csv: no todas las pendientes tienen {N_PERFILES} perfiles"
    return tabla


# Las tres conductas del índice de compromiso, cada una con su coeficiente (03_robustez_regresion, especificación
# «componentes del índice»: el modelo de coeficiente común con las conductas en lugar del índice). Solo 2012 y 2022.
# El índice les da el mismo peso, pero no pesan igual: para una conducta concreta, el agente usa esta tabla
CONDUCTAS = {
    "SKIPPING": ("faltar_a_clase", "Haber faltado a clase (un día o clases sueltas) en las dos últimas semanas, "
                                   "frente a no haber faltado"),
    "TARDYSD": ("llegar_tarde", "Cada paso más de impuntualidad en dos semanas: de ninguna vez a 1 o 2 veces, o de 1 "
                                "o 2 veces a 3 o más"),
    "deberes_en_u": ("deberes_tiempo_intermedio", "Dedicar a los deberes un tiempo intermedio (el tercio central de "
                                                  "su edición), frente a poco o mucho tiempo"),
}


def preparar_conductas() -> pd.DataFrame | None:
    """Coeficiente de cada conducta del compromiso en 2012 y 2022, y su cambio, de las comprobaciones de robustez."""
    ruta = FUENTES["resultados_robustez"]
    if not ruta.exists():
        print(f"Aviso: no existe {ruta.name}; se omite la tabla de conductas.")
        return None
    robustez = pd.read_parquet(ruta)
    filas = robustez[(robustez["especificacion"] == "componentes del índice") & robustez["variable"].isin(CONDUCTAS)]
    assert len(filas) == len(CONDUCTAS), f"{ruta.name}: faltan conductas en la especificación «componentes del índice»"
    return pd.DataFrame([{"conducta": CONDUCTAS[f.variable][0], "descripcion": CONDUCTAS[f.variable][1],
                          "coef_2012": f.pendiente_2012, "coef_2022": f.pendiente_2022,
                          "cambio": f.cambio, "p_cambio": f.p_cambio} for f in filas.itertuples()])


def preparar_metricas() -> pd.DataFrame | None:
    """Métricas por modelo y edición; la regresión evaluada es la de pendiente por perfil."""
    metricas = _leer_resultado("metricas_modelos", COLUMNAS_METRICAS)
    if metricas is None:
        return None
    return metricas.replace({"modelo": {"regresion": "regresion_por_perfil"}})


def main():
    DIR_IMAGENES_MACRO.mkdir(parents=True, exist_ok=True)

    alumnos = preparar_alumnos()
    alumnos.to_parquet(RUTA_ALUMNOS, index=False)
    print(f"{RUTA_ALUMNOS.name}: {alumnos.shape[0]} alumnos, {RUTA_ALUMNOS.stat().st_size / 1e6:.1f} MB")
    print(alumnos.groupby("year", observed=True).size().to_string())

    catalogo = copiar_graficos()
    catalogo.to_csv(RUTA_CATALOGO_GRAFICOS, index=False)
    print(f"{RUTA_CATALOGO_GRAFICOS.name}: {len(catalogo)} gráficos")

    # Elimina imágenes de img/ que ya no están en el catálogo
    en_catalogo = {DIR_ARTEFACTOS / r for r in catalogo["ruta"]}
    for imagen in DIR_IMAGENES_MACRO.glob("*.png"):
        if imagen not in en_catalogo:
            imagen.unlink()

    # Resultados del modelado, si existen
    shap = preparar_shap(alumnos)
    if shap is not None:
        shap.to_parquet(RUTA_SHAP, index=False)
        print(f"{RUTA_SHAP.name}: {len(shap)} alumnos, {RUTA_SHAP.stat().st_size / 1e6:.1f} MB")
    for tabla, destino in [(preparar_coeficientes(), RUTA_COEFICIENTES), (preparar_metricas(), RUTA_METRICAS),
                           (preparar_conductas(), RUTA_CONDUCTAS)]:
        if tabla is not None:
            tabla.to_csv(destino, index=False)
            print(f"{destino.name}: {len(tabla)} filas")


if __name__ == "__main__":
    main()
