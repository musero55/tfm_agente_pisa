# Gráficos de reports/ guardados por el resto de notebooks de fase 1 (con savefig):
#   - 01_EDA_recursos_centro.ipynb     (12 países del panel)
#   - 01_EDA_variables_modelo.ipynb    (12 países del panel)
#   - 01_EDA_recursos_alumno.ipynb     (33 países)
#   - 01_EDA_equidad.ipynb             (33 países, incluido 01_recursos_centro_y_nota.png)
# Mismo formato que GRAFICOS_CONTEXTO en agente_pisa/preparar_artefactos.py: (clave, archivo, descripción)
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
    ("recursos_centro_cobertura", "01_recursos_centro_cobertura.png",
     "Porcentaje de centros con dato de cada recurso del centro, por país y edición"),
    ("recursos_centro_correlaciones", "01_recursos_centro_correlaciones.png",
     "Correlaciones entre los recursos del centro dentro de cada país y edición"),
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
    ("universo_modelo", "01_variables_modelo_universo.png",
     "Cobertura de los datos: alumnos con perfil de centro, con índice de compromiso y centros por perfil y edición"),
    ("variables_modelo_huecos", "01_variables_modelo_huecos.png",
     "Diferencia de nota entre los alumnos sin dato y con dato en cada variable del modelo, relativa a su país y edición"),
    ("variables_modelo_huecos_perfil", "01_variables_modelo_huecos_perfil.png",
     "Porcentaje de alumnos sin dato y su diferencia de nota, por perfil de centro y edición"),
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

# 33 países, bloque exploratorio previo a elegir el tema del TFM
GRAFICOS_EQUIDAD = [
    # ("desigualdad_y_rendimiento", "01_desigualdad_y_rendimiento.png",
    #  "Relación del Gini, la dispersión del ESCS y la segregación entre centros con la nota media de matemáticas del país"),
    # ("correlacion_medidas_sociales", "01_correlacion_medidas_sociales.png",
    #  "Correlación entre las tres medidas de desigualdad social"),
    # ("brecha_recursos_centros", "01_brecha_recursos_entre_centros.png",
    #  "Brecha de recursos entre el 25 % de centros más desfavorecidos y el 25 % más favorecido, por país (PISA 2022)"),
    # ("ranking_desigualdad_nota", "01_ranking_correlacion_variables_sociales_recursos.png",
    #  "Correlación de cada medida de desigualdad social y de recursos entre centros con la nota de matemáticas"),
    # ("recursos_centro_nota", "01_recursos_centro_y_nota.png",
    #  "Correlación del nivel socioeconómico y los recursos del centro con su nota media de matemáticas"),
]