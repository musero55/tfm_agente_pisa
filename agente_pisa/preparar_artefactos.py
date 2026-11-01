"""
Genera en agente_pisa/artefactos/ todo lo que consume el agente en tiempo de ejecución.

Uso (desde la raíz del repositorio, con el entorno tfm_env):
    python agente_pisa/preparar_artefactos.py

Ficheros generados:
    alumnos_modelo.parquet   Alumnos que entran en el modelo (en_modelo), con la nota de matemáticas, las variables
                             de interés y de control en sus unidades originales y los estratos fijos desglosados.
    catalogo_graficos.csv    Imágenes estáticas que el agente puede mostrar.
    img/                     PNG copiados de reports/ y referenciados en el catálogo.


Etapa 2, solo si el modelado ha dejado sus resultados en models/ (formato en ENTREGA_MODELOS.md):
    shap_alumnos.parquet       SHAP del XGBoost de cada alumno, medio entre valores plausibles.
    coeficientes_regresion.csv Regresión por edición, combinada con las reglas de Rubin.
    metricas_modelos.csv       R², RMSE y MAE por modelo y edición.
"""
import shutil

import numpy as np
import pandas as pd

from config import (
    CORTES_COMPROMISO, CORTES_RECURSOS, DIR_ARTEFACTOS, DIR_IMAGENES_MACRO, FUENTES, PAISES_PANEL,
    RUTA_ALUMNOS, RUTA_CATALOGO_GRAFICOS, RUTA_COEFICIENTES, RUTA_METRICAS, RUTA_SHAP, TAMANOS, TIPOS_CENTRO, UBICACIONES, VARIABLES_NUMERICAS,
)

# Gráficos de reports/ que se ofrecen como contexto.
# Edita esta lista para añadir o quitar imágenes; la descripción es lo que lee el agente para elegirla.

# Las de 33 países van comentadas: no coinciden con los datos del agente (12 países del panel).

GRAFICOS_ESTRATOS = [
    #No necesario
    # ("estratos_sesgo_escs", "00_estratos_sesgo_sobrecontrol_escs_homepos.png",
    #  "Relación entre el ESCS medio del centro y los recursos del hogar (HOMEPOS): por qué estratificar por ESCS provoca sobrecontrol (PISA 2022)"),

    #Utiliza 33 paises- No se usa
    # ("estratos_nulos_titularidad", "00_estratos_nulos_titularidad_financiacion_pais.png",
    #  "Porcentaje de valores nulos por país en titularidad (SCHLTYPE) y financiación (PROPFUND), con el umbral de descarte del 50 % (PISA 2022)"),

    #OK
    ("estratos_tamano_centros", "00_estratos_tamano_centros_titularidad_ubicacion.png",
     "Ejemplo de distribución del tamaño de los centros españoles por titularidad y ubicación, con los cortes pequeño / mediano / macro"),

     #OK
    ("estratos_colegios_edicion", "00_estratos_colegios_por_estrato_edicion.png",
     "Número de colegios en cada estrato fijo (perfil de centro) y su comparación entre ediciones 2012-2022"),
]

GRAFICOS_COMPROMISO = [
    ("compromiso_distribucion_2022", "01_compromiso_distribucion_indicadores_2022.png",
     "Distribución de los tres indicadores del índice de compromiso (horas de deberes, absentismo e impuntualidad) en PISA 2022"),

    #No necesario
    # ("compromiso_saturacion_deberes", "01_compromiso_saturacion_deberes_nota.png",
    #  "Relación entre horas de deberes y nota de matemáticas a nivel alumno y a nivel centro por estrato: la nota se satura a partir de cierto tiempo"),

    #Check
    ("compromiso_por_estrato_2022", "01_compromiso_indicadores_por_estrato_2022.png",
     "Horas de deberes, absentismo e impuntualidad por estrato de titularidad y ubicación (PISA 2022)"),

    #Check
    ("compromiso_indicadores_2012", "01_compromiso_indicadores_2012.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2012"),

    #No Necesario
    # ("compromiso_validacion_outhours", "01_compromiso_validacion_outhours_2015.png",
    #  "Validación metodológica de las horas de deberes en 2015: reconstrucción con 5 materias frente a 3 troncales contra OUTHOURS oficial"),

    #Check
    ("compromiso_indicadores_2015", "01_compromiso_indicadores_2015.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2015"),

    #Check
    ("compromiso_indicadores_2018", "01_compromiso_indicadores_2018.png",
     "Distribución de horas de deberes, absentismo e impuntualidad en PISA 2018 (edición con huecos en deberes)"),

    #Check
    ("compromiso_disponibilidad", "01_compromiso_disponibilidad_pais_edicion.png",
     "Disponibilidad de cada variable del índice de compromiso por país y edición, y países que forman el panel común"),

    #No Necesario
    # ("compromiso_reescalado", "01_compromiso_reescalado_indice.png",
    #  "Distribución del índice de compromiso equiponderado antes y después del reescalado final"),

    #No Necesario
    # ("compromiso_pca_vs_equiponderado", "01_compromiso_pca_vs_equiponderado.png",
    #  "Peso de cada dimensión del índice de compromiso: PCA conjunto frente a índice equiponderado (panel común 2012-2022)"),

    #Check
    ("compromiso_titularidad_ubicacion", "01_compromiso_indice_por_titularidad_ubicacion_2022.png",
     "Índice de compromiso y competencia por titularidad y ubicación del centro (PISA 2022)"),

    #Check
    ("compromiso_espana_vs_panel", "01_compromiso_indice_alumno_espana_vs_panel_2022.png",
     "Reparto de alumnos por nivel del índice de compromiso y competencia: España frente al resto del panel (PISA 2022)"),

    #Check
    ("compromiso_evolucion", "01_compromiso_evolucion_indice.png",
     "Evolución del índice de compromiso y competencia 2012-2022, global y por titularidad, en el panel común de países"),
]

GRAFICOS_RECURSOS_CENTRO = [

    #No necesaria (No se visualiza bien)
    # ("recursos_centro_cobertura", "01_recursos_centro_cobertura.png",
    #  "Porcentaje de centros con dato de cada recurso del centro, por país y edición"),

    #No necesaria (demasiado pequeña)
    # ("recursos_centro_correlaciones", "01_recursos_centro_correlaciones.png",
    #  "Correlaciones entre los recursos del centro dentro de cada país y edición"),
    
    #Check
    ("recursos_centro_evolucion_pais", "01_recursos_centro_evolucion_pais.png",
     "Media de cada recurso del centro (alumnos por profesor, tamaño de clase, ordenadores...) por país y edición"),

    #Check
    ("recursos_centro_reparto_varianza", "01_recursos_centro_reparto_varianza.png",
     "En qué nivel varían los recursos del centro: entre países, ediciones, perfiles de centro, centros y alumnos"),

     #No Necesaria (?)
    ("recursos_centro_perfiles", "01_recursos_centro_perfiles.png",
     "Media de cada índice de recursos del centro por perfil de centro y edición"),

    #Check
    ("recursos_centro_correlaciones_alumno", "01_recursos_centro_correlaciones_alumno.png",
     "Correlación de los recursos del centro con la composición social, el origen social, los recursos de estudio, el compromiso y la nota del alumno"),

    #No necesaria(? No la entiendo)
    ("recursos_centro_asociacion_nota", "01_recursos_centro_asociacion_nota.png",
     "Puntos de matemáticas asociados a cada recurso del centro, dentro de cada país y edición, con y sin controles"),

     #Check
    ("recursos_centro_escasez_2012", "01_recursos_centro_escasez_2012.png",
     "Índices de escasez de recursos del centro en 2012 y por qué no se comparan entre ediciones"),
]

GRAFICOS_VARIABLES_MODELO = [

    #No Usar, redundante con dos gráficas anteriores 
    # ("universo_modelo", "01_variables_modelo_universo.png",
    #  "Cobertura de los datos: alumnos con perfil de centro, con índice de compromiso y centros por perfil y edición"),

    #Check
    ("variables_modelo_huecos", "01_variables_modelo_huecos.png",
     "Diferencia de nota entre los alumnos sin dato y con dato en cada variable del modelo, relativa a su país y edición"),
     
     #No Usar, poco clara
    # ("variables_modelo_huecos_perfil", "01_variables_modelo_huecos_perfil.png",
    #  "Porcentaje de alumnos sin dato y su diferencia de nota, por perfil de centro y edición"),
]

# 33 países: descomentar solo si el agente pasa a cubrir también los países fuera del panel
GRAFICOS_RECURSOS_ALUMNO = [
    # ("recursos_alumno_saturacion", "01_recursos_alumno_saturacion.png",
    #  "Porcentaje de alumnos que tiene cada recurso de estudio en casa, por edición (media OCDE)"),
    # ("recursos_alumno_subindice_estudio", "01_recursos_alumno_subindice_estudio.png",
    #  "Cuántos recursos de estudio en casa (de 0 a 6) tiene cada alumno"),
    # ("recursos_alumno_validacion", "01_recursos_alumno_validacion.png",
    #  "Correlación de cada subíndice de recursos del hogar con los índices oficiales de la OCDE"),
    # ("recursos_alumno_sin_subindice", "01_recursos_alumno_sin_subindice.png",
    #  "Porcentaje de alumnos sin cada subíndice de recursos del hogar, por país y edición"),
    # ("recursos_alumno_paises", "01_recursos_alumno_evolucion_pais.png",
    #  "Media de recursos de estudio, riqueza del hogar y libros por país y edición"),
    # ("recursos_alumno_reparto_varianza", "01_recursos_alumno_reparto_varianza.png",
    #  "En qué nivel varían los subíndices de recursos del hogar, las notas y el ESCS: entre países, ediciones, centros y alumnos"),
    # ("recursos_alumno_correlaciones_nota", "01_recursos_alumno_correlaciones_nota.png",
    #  "Correlaciones dentro de cada país entre recursos del hogar, origen social y notas, por edición"),
    # ("recursos_alumno_nota", "01_recursos_alumno_asociacion_nota.png",
    #  "Asociación de los recursos del hogar (recursos de estudio, riqueza y libros) con la nota, dentro de cada país y edición"),
    # ("recursos_alumno_indices_centro", "01_recursos_alumno_indices_centro.png",
    #  "Porcentaje de alumnos con dato en apoyo del profesor (TEACHSUP) y TIC del centro (ICTSCH), por país y edición"),
    # ("recursos_alumno_irt_dificultades", "01_recursos_alumno_irt_dificultades.png",
    #  "Dificultad relativa de cada ítem de recursos de estudio por edición (modelo de Rasch)"),
    # ("recursos_alumno_irt_paises", "01_recursos_alumno_irt_paises.png",
    #  "Funcionamiento diferencial de cada ítem de recursos de estudio por país"),
]

COLUMNAS = ["CNT", "CNTSCHID", "CNTSTUID", "year", "perfil", "SENWT", "W_FSTUWT", "sexo_femenino", "inmigrante",
            "tiempo_deberes_totales_diarios", "perfil_poco_representativo"] + \
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

    # Niveles descriptivos de las variables de interés y de los controles del alumno, parece que l esta cogiendo de la tabla codificada (
    # fijate en sexo y origen)
    for columna, origen, (cortes, niveles) in [("nivel_compromiso", "Indice_Compromiso_Competencia", CORTES_COMPROMISO),
                                               ("nivel_recursos", "recursos_estudio", CORTES_RECURSOS)]:
        alumnos[columna] = pd.cut(alumnos[origen], bins=cortes, labels=niveles, right=False)
    alumnos["sexo"] = alumnos["sexo_femenino"].map({1.0: "Chica", 0.0: "Chico"})
    alumnos["origen"] = alumnos["inmigrante"].map({1.0: "Inmigrante", 0.0: "Nativo"})

    #Deja las columnas con el tipo correcto
    for columna in ["CNT", "perfil", "tipo_centro", "ubicacion", "tamano", "sexo", "origen"]:
        alumnos[columna] = alumnos[columna].astype("category")
    numericas = alumnos.select_dtypes("float64").columns
    alumnos[numericas] = alumnos[numericas].astype(np.float32)

    assert sorted(alumnos["CNT"].unique()) == sorted(PAISES_PANEL), "Los países no coinciden con el panel común"
    return alumnos.drop(columns=["sexo_femenino", "inmigrante"]).reset_index(drop=True)


def copiar_graficos() -> pd.DataFrame:
    filas = []
    for id_grafico, fichero, descripcion in (GRAFICOS_ESTRATOS + GRAFICOS_COMPROMISO + GRAFICOS_RECURSOS_CENTRO + GRAFICOS_VARIABLES_MODELO):
        origen = FUENTES["reports"] / fichero
        if not origen.exists():
            print(f"Aviso: no existe reports/{fichero}; se omite del catálogo.")
            continue
        shutil.copy2(origen, DIR_IMAGENES_MACRO / fichero)
        filas.append({"id": id_grafico, "tipo": "contexto", "ruta": f"img/{fichero}", "descripcion": descripcion})
    return pd.DataFrame(filas, columns=["id", "tipo", "ruta", "descripcion"])


# Columnas que deben traer los resultados del modelado (ENTREGA_MODELOS.md)
CLAVES_ALUMNO = ["CNT", "year", "CNTSCHID", "CNTSTUID"]
TIPOS_CLAVES = {"CNT": str, "year": "int64", "CNTSCHID": "int64", "CNTSTUID": "int64"}   # para unir sin fallos de tipo
COLUMNAS_SHAP = CLAVES_ALUMNO + ["valor_base", "prediccion"]
COLUMNAS_COEFICIENTES = ["edicion", "regresion", "estrato", "variable", "coeficiente", "error_tipico", "ic_inf", "ic_sup",
                         "p_valor", "unidad", "n_alumnos", "n_centros"]
COLUMNAS_METRICAS = ["edicion", "modelo", "conjunto", "r2", "rmse", "mae", "n_alumnos"]


def _leer_resultado(clave: str, columnas: list[str]) -> pd.DataFrame | None:
    ruta = FUENTES[clave]
    if not ruta.exists():
        print(f"Aviso: no existe models/{ruta.name} (pendiente del modelado); se omite.")
        return None
    tabla = pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)
    faltan = [c for c in columnas if c not in tabla.columns]
    assert not faltan, f"{ruta.name}: faltan las columnas {faltan} (ver ENTREGA_MODELOS.md)"
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

    # Etapa 2: resultados del modelado, si ya existen
    shap = preparar_shap(alumnos)
    if shap is not None:
        shap.to_parquet(RUTA_SHAP, index=False)
        print(f"{RUTA_SHAP.name}: {len(shap)} alumnos, {RUTA_SHAP.stat().st_size / 1e6:.1f} MB")
    for clave, columnas, destino in [("coeficientes_regresion", COLUMNAS_COEFICIENTES, RUTA_COEFICIENTES),
                                     ("metricas_modelos", COLUMNAS_METRICAS, RUTA_METRICAS)]:
        tabla = _leer_resultado(clave, columnas)
        if tabla is not None:
            tabla.to_csv(destino, index=False)
            print(f"{destino.name}: {len(tabla)} filas")


if __name__ == "__main__":
    main()
