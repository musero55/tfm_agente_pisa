"""
presupuesto_pais_edicion.py
===========================

Tabla país-edición: una fila por país (33 OCDE) y edición PISA (2012, 2015, 2018, 2022), con
resultados y contexto de PISA calculados desde las tablas maestras y las variables externas de
gasto, renta, personal y desigualdad de `data/raw/externos/`. La usa `01_EDA_equidad.ipynb`.

    * `construir_tabla`: la tabla completa.
    * `variables_externas` y `gini_edicion`: las variables externas de una edición (el Gini, de la
      OCDE y, si falta, del Banco Mundial).

Nada se imputa: los huecos son NaN (también los ceros que en realidad son datos no disponibles).
Solo se interpolan linealmente los huecos *interiores* de una serie anual para calcular las
medias de años previos y el gasto acumulado.
"""

from __future__ import annotations

import os

import pandas as pd
import pyarrow.parquet as pq

from src.datos_externos import cargar_oecd
from src.pisa_estadisticas import agregar_desviacion_ponderada, agregar_media_ponderada, agregar_pv, reparto_varianza
from src.pisa_pipeline import DOMINIOS, PAISES_OCDE_TODAS_LAS_EDICIONES, columnas_pv, leer_recursos_centros, rutas_datos_anuales

EDICIONES = [2012, 2015, 2018, 2022]
AÑOS_SERIE = range(1995, 2025)
AÑO_BASE = 2020   # año de los precios constantes (el mismo que usa la OCDE en el gasto por alumno)

# Nombre de cada dominio y de cada nivel de la OCDE en las columnas de la tabla
NOMBRE_DOMINIO = {'MATH': 'matematicas', 'READ': 'lectura', 'SCIE': 'ciencias'}
NOMBRE_NIVEL_GASTO = {'1': 'primaria', '2': 'secundaria_primera_etapa', '3': 'secundaria_segunda_etapa', '2_3': 'secundaria'}


# ---------------------------------------------------------------- PISA

def resultados_pisa(ruta_raw_base: str, año: int) -> pd.DataFrame:
    """Por país: media de cada dominio (PV promediados por alumno, ponderados por
    `W_FSTUWT`), nº de alumnos, media y desviación de `ESCS_TREND`, minutos semanales
    de aprendizaje por asignatura (2012-2018; los ceros se tratan como dato ausente)
    y segregación socioeconómica (% de la varianza de `ESCS_TREND` entre centros)."""
    ruta, _ = rutas_datos_anuales(ruta_raw_base, año)
    nombres = pq.ParquetFile(ruta).schema.names
    columnas_valores_plausibles = [columna for dominio in DOMINIOS for columna in columnas_pv(dominio) if columna in nombres]
    minutos = {'pisa_minutos_semanales_matematicas': 'MMINS', 'pisa_minutos_semanales_lengua': 'LMINS', 'pisa_minutos_semanales_ciencias': 'SMINS'}
    minutos = {k: v for k, v in minutos.items() if v in nombres}
    estudiantes = pd.read_parquet(ruta, columns=['CNT', 'CNTSCHID', 'W_FSTUWT', 'ESCS_TREND'] + columnas_valores_plausibles + list(minutos.values()))
    # Medias y desviación ponderadas por país con las funciones de src/pisa_estadisticas.py (las mismas que 01_EDA_notas_asignatura)
    estudiantes = estudiantes.assign(**{nuevo: estudiantes[origen].where(estudiantes[origen] > 0) for nuevo, origen in minutos.items()})
    tabla = agregar_media_ponderada(estudiantes.rename(columns={'ESCS_TREND': 'pisa_escs_trend_media'}), ['pisa_escs_trend_media'] + list(minutos))
    for dominio in DOMINIOS:
        tabla = tabla.merge(agregar_pv(estudiantes, dominio, nombre=f'pisa_{NOMBRE_DOMINIO[dominio]}'), on='CNT', validate='one_to_one')
    tabla = tabla.merge(agregar_desviacion_ponderada(estudiantes.rename(columns={'ESCS_TREND': 'pisa_escs_trend_desviacion_tipica'}),
                                                     ['pisa_escs_trend_desviacion_tipica']), on='CNT', validate='one_to_one')
    # Número de alumnos y segregación: % de la varianza de ESCS_TREND (ponderada con W_FSTUWT) entre los centros del país
    # (0 = todos los centros igual de mixtos; cuanto más alto, más separados por nivel socioeconómico)
    por_pais = estudiantes.groupby('CNT')
    otras = pd.DataFrame({
        'pisa_numero_alumnos': por_pais.size(),
        'pisa_segregacion_social_entre_centros_pct': por_pais.apply(
            lambda pais: reparto_varianza(pais, 'ESCS_TREND', {'entre centros': ['CNTSCHID']}, 'dentro de los centros', peso_col='W_FSTUWT')['entre centros'],
            include_groups=False),
    }).reset_index()
    columnas = (['pais', 'pisa_numero_alumnos'] + [f'pisa_{NOMBRE_DOMINIO[dominio]}' for dominio in DOMINIOS]
                + ['pisa_escs_trend_media', 'pisa_escs_trend_desviacion_tipica'] + list(minutos) + ['pisa_segregacion_social_entre_centros_pct'])
    return tabla.merge(otras, on='CNT', validate='one_to_one').rename(columns={'CNT': 'pais'}).astype({'pais': object})[columnas]


def escs_de_centros(ruta_raw_base: str, año: int) -> pd.DataFrame:
    """Media de `ESCS_TREND` de los alumnos de cada centro (ponderada por `W_FSTUWT`)."""
    ruta, _ = rutas_datos_anuales(ruta_raw_base, año)
    estudiantes = pd.read_parquet(ruta, columns=['CNT', 'CNTSCHID', 'W_FSTUWT', 'ESCS_TREND']).dropna(subset=['ESCS_TREND'])
    return agregar_media_ponderada(estudiantes.rename(columns={'ESCS_TREND': 'escs_centro'}), ['escs_centro'], claves='centro')


def centros_pisa(ruta_raw_base: str, año: int) -> pd.DataFrame:
    """Por país, con el peso del centro (`W_SCHGRNRABWT`): medias de recursos y
    financiación del centro, % de centros públicos (`SCHLTYPE` = 3), autonomía sobre
    recursos y **brecha de recursos** entre centros desfavorecidos y favorecidos
    (cuartil inferior menos superior de `ESCS_TREND` medio del centro). Un valor
    negativo en ratio, tamaño de clase o escasez significa que los desfavorecidos
    están mejor dotados; positivo en profesorado certificado, al revés."""
    # Recursos de cada centro con nombres comunes a todas las ediciones (`leer_recursos_centros`, src/pisa_pipeline.py)
    colegios = leer_recursos_centros(ruta_raw_base, año).merge(escs_de_centros(ruta_raw_base, año), on=['CNT', 'CNTSCHID'], how='left')
    colegios['_centro_publico_pct'] = 100 * colegios['centro_publico']

    # Media de cada variable por país, con el peso del centro (las que la edición no tiene quedan NaN)
    origen_variables = {'pisa_alumnos_por_profesor': 'alumnos_por_profesor', 'pisa_tamaño_clase': 'tamaño_clase', 'pisa_tamaño_centro': 'tamaño_centro',
                        'pisa_centros_publicos_pct': '_centro_publico_pct',
                        'pisa_financiacion_centro_gobierno_pct': 'financiacion_gobierno_pct', 'pisa_financiacion_centro_cuotas_pct': 'financiacion_cuotas_pct',
                        'pisa_financiacion_centro_donaciones_pct': 'financiacion_donaciones_pct', 'pisa_financiacion_centro_otras_pct': 'financiacion_otras_pct',
                        'pisa_profesores_certificados_pct': 'profesores_certificados_pct', 'pisa_profesores_master_pct': 'profesores_master_pct',
                        'pisa_ordenadores_por_alumno': 'ordenadores_por_alumno', 'pisa_autonomia_recursos': 'autonomia_recursos',
                        'pisa_escasez_material_educativo': 'escasez_material_educativo', 'pisa_escasez_personal': 'escasez_personal'}
    origen_brechas = {'pisa_brecha_alumnos_por_profesor': 'alumnos_por_profesor', 'pisa_brecha_tamaño_clase': 'tamaño_clase',
                      'pisa_brecha_profesorado_certificado': 'profesores_certificados_pct',
                      'pisa_brecha_escasez_material': 'escasez_material_educativo', 'pisa_brecha_escasez_personal': 'escasez_personal'}

    def media_por_pais(centros, origenes):
        """Media por país, ponderada con el peso del centro, de las columnas de `origenes` ({nombre nuevo: columna}) que existan."""
        disponibles = {nuevo: origen for nuevo, origen in origenes.items() if origen in centros.columns}
        valores = centros[['CNT', 'W_SCHGRNRABWT']].assign(**{nuevo: centros[origen] for nuevo, origen in disponibles.items()})
        return agregar_media_ponderada(valores, list(disponibles), peso_col='W_SCHGRNRABWT').set_index('CNT')

    tabla = media_por_pais(colegios, origen_variables)
    tabla.insert(0, 'pisa_numero_centros', colegios.groupby('CNT').size())
    # Brecha de recursos entre el cuartil de centros más desfavorecido y el más favorecido de cada país
    escs_por_pais = colegios.groupby('CNT')['escs_centro']
    desfavorecidos = colegios['escs_centro'] <= escs_por_pais.transform(lambda escs: escs.quantile(0.25))
    favorecidos = colegios['escs_centro'] >= escs_por_pais.transform(lambda escs: escs.quantile(0.75))
    tabla = tabla.join(media_por_pais(colegios[desfavorecidos], origen_brechas) - media_por_pais(colegios[favorecidos], origen_brechas))
    columnas = ['pisa_numero_centros'] + list(origen_variables) + list(origen_brechas)
    return tabla.reindex(columns=columnas).rename_axis('pais').reset_index().astype({'pais': object})


# ---------------------------------------------------------------- series externas

def serie(datos: pd.DataFrame, **filtros) -> pd.DataFrame:
    """Serie anual (filas: años; columnas: países) con los filtros dados. Falla si
    quedan duplicados país-año, señal de que falta un filtro."""
    for k, v in filtros.items():
        datos = datos[datos[k] == v]
    assert not datos.duplicated(['pais', 'año']).any(), f'duplicados con {filtros}'
    return datos.pivot(index='año', columns='pais', values='valor').reindex(AÑOS_SERIE)


def a_usd_ppp(xdc_corrientes: pd.DataFrame, deflactor: pd.DataFrame, factor_ppp: pd.DataFrame, base: int = AÑO_BASE) -> pd.DataFrame:
    """Series anuales en moneda nacional a precios corrientes -> USD PPP a precios constantes de `base`
    (el método de la OCDE): se deflactan con el deflactor del PIB del país y se convierten con su
    factor PPP del año `base`. Así son comparables entre países y años, y con el gasto por alumno."""
    return xdc_corrientes * (deflactor.loc[base] / deflactor) / factor_ppp.loc[base]


def valor_en_año(serie_anual: pd.DataFrame, año: int) -> pd.Series:
    """Valor de cada país en un año (NaN si no hay)."""
    return serie_anual.loc[año]


def interpolada(serie_anual: pd.DataFrame) -> pd.DataFrame:
    """Rellena linealmente los huecos *interiores* de cada país (nunca extrapola)."""
    return serie_anual.interpolate(limit_area='inside')


def media_previa(serie_anual: pd.DataFrame, año: int, ventana: int = 4, minimo: int = 3) -> pd.Series:
    """Media de los `ventana` años hasta `año` (incluido), sobre la serie interpolada.
    NaN si hay menos de `minimo` años con dato."""
    ventana_interpolada = interpolada(serie_anual).loc[año - ventana + 1:año]
    return ventana_interpolada.mean().where(ventana_interpolada.notna().sum() >= minimo)


def acumulado_6_15(primaria: pd.DataFrame, secundaria1: pd.DataFrame, año: int) -> pd.Series:
    """Gasto por alumno acumulado entre los 6 y los 15 años de la cohorte que hace PISA
    en `año`: 6 años de primaria (t-9 a t-4) y 4 de secundaria 1.ª etapa (t-3 a t),
    sobre series interpoladas. Aproximado (no usa la duración teórica de cada país).
    NaN si falta algún año."""
    gasto_primaria = interpolada(primaria).loc[año - 9:año - 4]
    gasto_secundaria = interpolada(secundaria1).loc[año - 3:año]
    completo = (gasto_primaria.notna().sum() == 6) & (gasto_secundaria.notna().sum() == 4)
    return (gasto_primaria.sum() + gasto_secundaria.sum()).where(completo)


def gini_edicion(gini_ocde: pd.DataFrame, gini_banco_mundial: pd.DataFrame, año: int) -> pd.DataFrame:
    """Gini (0-1) de la renta disponible de cada país en la edición `año`. Se toma la observación más cercana al
    año (como mucho ±1); a igual distancia, la de la OCDE antes que la del Banco Mundial (que va de 0 a 100) y,
    si aún empatan, el año anterior. Devuelve `gini`, `gini_fuente` y `gini_año`, indexado por país."""
    gini_ocde_filas = gini_ocde[['pais', 'año', 'valor']].assign(fuente='OCDE', prioridad=0)
    gini_banco_mundial_filas = gini_banco_mundial.dropna(subset=['valor']).assign(valor=lambda datos: datos['valor'] / 100, fuente='Banco Mundial', prioridad=1)
    observaciones = pd.concat([gini_ocde_filas, gini_banco_mundial_filas[['pais', 'año', 'valor', 'fuente', 'prioridad']]])
    observaciones['año'] = observaciones['año'].astype(int)
    observaciones = observaciones[observaciones['año'].between(año - 1, año + 1)].assign(distancia=lambda datos: (datos['año'] - año).abs(), posterior=lambda datos: datos['año'] > año)
    mejor = observaciones.sort_values(['pais', 'distancia', 'prioridad', 'posterior']).groupby('pais').head(1).set_index('pais')
    return mejor[['valor', 'fuente', 'año']].rename(columns={'valor': 'gini', 'fuente': 'gini_fuente', 'año': 'gini_año'})


def variables_externas(datos: dict, año: int) -> pd.DataFrame:
    """Variables de presupuesto, renta y personal de cada país en la edición `año`.
    `datos`: dict con los DataFrames cargados con `cargar_oecd` (ver `construir_tabla`)."""
    gasto_por_alumno = datos['gasto']
    base = dict(precios='Q', unidad='USD_PPP_ST', fuente='_T', institucion='INST_EDU', tipo_gasto='DIR_EXP')
    por_nivel = {nivel: serie(gasto_por_alumno, nivel=f'ISCED11_{nivel}', **base) for nivel in ('1', '2', '3', '2_3')}

    variables = {}
    # --- Cuánto: gasto por alumno (USD PPP, precios constantes), en el año de la prueba
    for nivel, serie_nivel in por_nivel.items():
        variables[f'gasto_alumno_{NOMBRE_NIVEL_GASTO[nivel]}_usd_ppp'] = valor_en_año(serie_nivel, año)
    variables['gasto_alumno_secundaria_media_4_años_usd_ppp'] = media_previa(por_nivel['2_3'], año)
    variables['gasto_acumulado_alumno_6_a_15_años_usd_ppp'] = acumulado_6_15(por_nivel['1'], por_nivel['2'], año)
    variables['gasto_alumno_secundaria_pct_pib_per_capita'] = valor_en_año(serie(
        gasto_por_alumno, nivel='ISCED11_2_3', unidad='PT_B1GQ_POP', fuente='_T', institucion='INST_EDU', tipo_gasto='DIR_EXP'), año)

    # --- Esfuerzo y origen de la financiación
    gasto_pib_y_fuentes = datos['gasto_pib']
    variables['gasto_pct_pib_primaria_a_postsecundaria'] = valor_en_año(serie(gasto_pib_y_fuentes, nivel='ISCED11_1T4', unidad='PT_B1GQ', fuente='_T', precios='_Z'), año)
    for nombre, fuente in (('publica', 'S13'), ('privada', 'S1D_NON_EDU'), ('exterior', 'S2')):
        variables[f'financiacion_{nombre}_pct_gasto_secundaria'] = valor_en_año(serie(gasto_pib_y_fuentes, nivel='ISCED11_2_3', unidad='PT_EXP', fuente=fuente, precios='_Z'), año)
    variables['pct_gasto_publico_en_primaria_a_postsecundaria'] = valor_en_año(serie(datos['gasto_pct_publico'], nivel='ISCED11_1T4'), año)

    # --- Cómo: composición del gasto total de secundaria 1.ª+2.ª (corriente + capital)
    comun = dict(nivel='ISCED11_2_3', unidad='USD_PPP', precios='Q', fuente='_T', institucion='INST_EDU')
    corriente = serie(datos['gasto_corriente_capital'], tipo_gasto='CUR', **comun)
    capital = serie(datos['gasto_corriente_capital'], tipo_gasto='CAP', **comun)
    total = corriente + capital
    personal = serie(datos['gasto_personal'], tipo_gasto='CUR_COMP', **comun)
    docentes = serie(datos['gasto_personal'], tipo_gasto='CUR_COMPT', **comun)
    no_docentes = serie(datos['gasto_personal'], tipo_gasto='CUR_COMPO', **comun)
    variables['pct_gasto_secundaria_en_personal'] = 100 * valor_en_año(personal / total, año)
    variables['pct_gasto_secundaria_en_docentes'] = 100 * valor_en_año(docentes / total, año)
    variables['pct_gasto_secundaria_en_personal_no_docente'] = (100 * valor_en_año(no_docentes / total, año)).where(lambda valores: valores != 0)   # 0 = incluido en docentes
    variables['pct_gasto_secundaria_en_capital'] = 100 * valor_en_año(capital / total, año)
    # Gasto total (no por alumno) de secundaria 1.ª+2.ª en USD PPP constantes (la OCDE lo da en millones; 0 = no disponible)
    for nombre, serie_nivel in (('corriente', corriente), ('capital', capital), ('personal', personal),
                      ('docentes', docentes), ('personal_no_docente', no_docentes)):
        variables[f'gasto_total_{nombre}_secundaria_usd_ppp'] = (1e6 * valor_en_año(serie_nivel, año)).where(lambda valores: valores != 0)
    variables['pct_gasto_secundaria_en_otros_corrientes'] = 100 - variables['pct_gasto_secundaria_en_personal'] - variables['pct_gasto_secundaria_en_capital']

    # Servicios básicos frente a auxiliares (transporte, comidas, alojamiento)
    tipo = datos['gasto_tipo']
    base_t = dict(nivel='ISCED11_2_3', unidad='USD_PPP_ST')
    basicos, auxiliares = serie(tipo, tipo_gasto='CORE', **base_t), serie(tipo, tipo_gasto='ASERV', **base_t)
    variables['servicios_auxiliares_pct_gasto_alumno_secundaria'] = 100 * valor_en_año(auxiliares / (basicos + auxiliares), año)
    variables['gasto_alumno_secundaria_servicios_basicos_usd_ppp'] = valor_en_año(basicos, año)
    variables['gasto_alumno_secundaria_servicios_auxiliares_usd_ppp'] = valor_en_año(auxiliares, año)

    # --- Cómo: reparto por nivel y tipo de enseñanza (gasto por alumno, relativo a secundaria)
    def por_alumno(nivel):
        """Gasto por alumno del nivel educativo `nivel` (código ISCED) en el año de la edición."""
        return valor_en_año(serie(gasto_por_alumno, nivel=nivel, **base), año)
    variables['gasto_alumno_preprimaria_usd_ppp'] = por_alumno('ISCED11_02').where(lambda valores: valores != 0)   # 0 = dato no disponible
    variables['ratio_gasto_preprimaria_sobre_secundaria'] = variables['gasto_alumno_preprimaria_usd_ppp'] / variables['gasto_alumno_secundaria_usd_ppp']
    variables['ratio_gasto_fp_sobre_general_secundaria_segunda_etapa'] = por_alumno('ISCED11_35') / por_alumno('ISCED11_34')

    # --- Cuándo: escolarización temprana y repetición
    escolarizacion = datos['escolarizacion']
    for edad, nombre in (('Y3', '3'), ('Y4', '4'), ('Y15', '15')):
        variables[f'escolarizacion_{nombre}_años_pct'] = valor_en_año(serie(escolarizacion, nivel='_T', edad=edad), año)
    variables['repeticion_pct_secundaria_primera_etapa'] = valor_en_año(serie(datos['repeticion'], nivel='ISCED11_24'), año)
    for nombre_columna in ('escolarizacion_3_años_pct', 'escolarizacion_4_años_pct', 'escolarizacion_15_años_pct'):
        variables[nombre_columna] = variables[nombre_columna].where(lambda valores: valores != 0)   # 0% de escolarización a esas edades = dato no disponible (p. ej. Canadá)

    # --- Renta y tamaño
    estadisticas_referencia = datos['referencia']
    pib_per_capita_moneda_local = serie(estadisticas_referencia, medida='GDP_CAPITA', unidad='XDC_PS', precios='V')
    deflactor, factor_ppp = serie(estadisticas_referencia, medida='GDP_DEFLATOR'), serie(estadisticas_referencia, medida='PPPGDP')
    variables['pib_per_capita_usd_ppp'] = valor_en_año(a_usd_ppp(pib_per_capita_moneda_local, deflactor, factor_ppp), año)
    variables['poblacion'] = 1000 * valor_en_año(serie(estadisticas_referencia, medida='POP'), año)   # la OCDE la da en miles
    variables['gasto_publico_total_pct_pib'] = valor_en_año(serie(estadisticas_referencia, medida='T_PUB_EXP', unidad='PT_B1GQ'), año)
    variables['matricula_secundaria_equivalente_tiempo_completo'] = valor_en_año(serie(datos['matricula'], nivel='ISCED11_2_3'), año)

    # --- Docentes: pago, dotación y perfil
    salarios_legales = datos['salarios_legales']
    for etiqueta, experiencia in (('inicial', 'EXP0'), ('15_años_experiencia', 'EXP15')):
        salario_xdc = serie(salarios_legales, nivel='ISCED11_24', unidad='XDC', PERS_EXP_LEV=experiencia)
        variables[f'salario_legal_docente_{etiqueta}_pct_pib_per_capita'] = 100 * valor_en_año(salario_xdc / pib_per_capita_moneda_local, año)
        variables[f'salario_legal_docente_{etiqueta}_usd_ppp'] = valor_en_año(a_usd_ppp(salario_xdc, deflactor, factor_ppp), año)
    variables['salario_real_docente_indice_base_2015'] = valor_en_año(serie(datos['salarios_reales'], nivel='ISCED11_24', unidad='IX'), año)
    variables['horas_docencia_anuales_secundaria_primera_etapa'] = valor_en_año(serie(datos['horas_docencia'], nivel='ISCED11_24'), año)
    variables['alumnos_por_docente_secundaria_primera_etapa'] = valor_en_año(serie(datos['alumnos_docente'], nivel='ISCED11_2', institucion='INST_EDU'), año)
    variables['tamaño_clase_secundaria_primera_etapa'] = valor_en_año(serie(datos['tamaño_clase'], nivel='ISCED11_2', institucion='INST_EDU'), año)
    edad = datos['docentes_edad']
    variables['docentes_50_o_mas_años_pct'] = valor_en_año(serie(edad, edad='Y_GE50'), año)
    variables['docentes_menos_de_30_años_pct'] = valor_en_año(serie(edad, edad='Y_LT30'), año)

    # --- Palancas del gasto por alumno: pago por docente x docentes por alumno
    variables['docentes_por_100_alumnos'] = 100 / variables['alumnos_por_docente_secundaria_primera_etapa']
    variables['coste_docente_por_alumno_pct_pib_per_capita'] = variables['salario_legal_docente_15_años_experiencia_pct_pib_per_capita'] / variables['alumnos_por_docente_secundaria_primera_etapa']
    variables['salario_legal_docente_15_años_pct_pib_per_capita_por_1000_horas'] = 1000 * variables['salario_legal_docente_15_años_experiencia_pct_pib_per_capita'] / variables['horas_docencia_anuales_secundaria_primera_etapa']

    # --- Desigualdad: Gini de la renta disponible
    gini_por_pais = gini_edicion(datos['gini_ocde'], datos['gini_banco_mundial'], año)
    variables['gini'], variables['gini_fuente'], variables['gini_año'] = gini_por_pais['gini'], gini_por_pais['gini_fuente'], gini_por_pais['gini_año']

    return pd.DataFrame(variables).reindex(PAISES_OCDE_TODAS_LAS_EDICIONES).rename_axis('pais').reset_index()


def construir_tabla(ruta_raw_base: str, ruta_externos: str, ediciones: list[int] | None = None) -> pd.DataFrame:
    """Tabla país-edición (una fila por país y edición): PISA + variables externas."""
    ediciones = ediciones or EDICIONES
    leer_csv_externo = lambda nombre: cargar_oecd(os.path.join(ruta_externos, f'{nombre}.csv'))
    pib_per_capita_banco_mundial = pd.read_csv(os.path.join(ruta_externos, 'pib_per_capita_ppp.csv')).dropna(subset=['valor'])
    datos = {
        'gasto': leer_csv_externo('gasto_por_alumno'), 'gasto_pib': leer_csv_externo('gasto_pib_y_fuentes'),
        'gasto_pct_publico': leer_csv_externo('gasto_pct_gasto_publico'), 'gasto_personal': leer_csv_externo('gasto_personal'),
        'gasto_corriente_capital': leer_csv_externo('gasto_corriente_capital'), 'gasto_tipo': leer_csv_externo('gasto_alumno_tipo'),
        'matricula': leer_csv_externo('matricula_equivalente_tc'), 'referencia': leer_csv_externo('estadisticas_referencia'),
        'salarios_reales': leer_csv_externo('salarios_reales_docentes'), 'salarios_legales': leer_csv_externo('salarios_legales_docentes'),
        'horas_docencia': leer_csv_externo('horas_docencia_legales'), 'alumnos_docente': leer_csv_externo('alumnos_por_docente'),
        'tamaño_clase': leer_csv_externo('tamaño_de_clase'), 'docentes_edad': leer_csv_externo('docentes_edad'), 'repeticion': leer_csv_externo('repeticion'),
        'escolarizacion': leer_csv_externo('escolarizacion_por_edad'),
        'gini_ocde': leer_csv_externo('gini_ocde'), 'gini_banco_mundial': pd.read_csv(os.path.join(ruta_externos, 'gini_banco_mundial.csv')),
    }
    pib_per_capita_serie = serie(pib_per_capita_banco_mundial)
    tablas = []
    for año in ediciones:
        tabla_edicion = resultados_pisa(ruta_raw_base, año).merge(centros_pisa(ruta_raw_base, año), on='pais', how='outer')
        tabla_edicion = tabla_edicion.merge(variables_externas(datos, año), on='pais', how='left')
        tabla_edicion['pib_per_capita_banco_mundial_usd_ppp_2021'] = tabla_edicion['pais'].map(valor_en_año(pib_per_capita_serie, año))
        tabla_edicion.insert(0, 'edicion', año)
        tablas.append(tabla_edicion)
    return pd.concat(tablas, ignore_index=True).sort_values(['pais', 'edicion']).reset_index(drop=True)
