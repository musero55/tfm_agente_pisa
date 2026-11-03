"""
Casos de prueba del agente PISA para ejecutar_bateria_evaluacion.

Cada caso es una pregunta suelta (el evaluador abre un hilo nuevo por caso):
    id, categoria, pregunta
    herramientas_imprescindibles: herramientas que debe llamar (lista vacía = no debe llamar a ninguna)
    min_llamadas_herramienta: opcional, por defecto tantas como herramientas imprescindibles
    referencia: datos_clave (cifras correctas) y conclusiones_esperadas, que lee el juez

Cifras de agente_pisa/artefactos/coeficientes_regresion.csv y data/processed/resultados_robustez.parquet.
"""

# Privado urbano grande y Australia (incidencia del 2026-11-02, ver
# reports/resumenes/incidencia_agente_perfiles_australia.md). Hay dos cifras distintas que el agente confundía:
# la diferencia de nota del perfil (+10) y la subida del coeficiente de los recursos dentro del perfil, que es la
# que depende de Australia.
CASOS_PERFILES_AUSTRALIA = [
    {
        "id": "perfiles_diferencias_2022",
        "categoria": "Perfiles de centro",
        "pregunta": "¿Hay alguna diferencia significativa entre perfiles de centro?",
        "herramientas_imprescindibles": ["get_regression_weights"],
        "referencia": {
            "datos_clave": [
                "Referencia: público urbano mediano. Con alumnos iguales en todo lo demás, en 2022 se distinguen de "
                "cero: concertado urbano pequeño −11,6 (p = 0,003), privado urbano grande +10,1 (p = 0,036), privado "
                "urbano pequeño −17,9 (p = 0,009), público rural pequeño +5,27 (p = 0,032) y público urbano grande "
                "+7,48 (p = 0,002)",
                "El resto de perfiles no se distinguen de cero (por ejemplo, público rural mediano +3,21, p = 0,27)",
            ],
            "conclusiones_esperadas": [
                "Sí hay diferencias en cinco perfiles; el público urbano grande es la más precisa (p = 0,002)",
                "No llama frágil a la diferencia de +10 del privado urbano grande",
                "No atribuye las diferencias a países concretos: las cifras juntan los 12 países",
            ],
        },
    },
    {
        "id": "perfiles_diferencias_evolucion",
        "categoria": "Perfiles de centro",
        # Salida grande (14 perfiles x 4 ediciones): con ella el modelo de respaldo razonaba en bucle y devolvía
        # una respuesta vacía, y el principal copiaba mal cifras de una fila a otra
        "pregunta": "¿Qué perfiles de centro se distinguen del público urbano mediano en cada edición, de 2012 a 2022?",
        "herramientas_imprescindibles": ["get_regression_weights"],
        "referencia": {
            "datos_clave": [
                "2012: privado urbano grande +14,1 (p = 0,008), privado urbano pequeño −15,4 (p = 0,044), público "
                "rural pequeño +7,41 (p = 0,006)",
                "2015: concertado urbano mediano −8,83 (p = 0,027), privado urbano pequeño −16,2 (p = 0,045), público "
                "urbano pequeño −6,27 (p = 0,011)",
                "2018: privado urbano pequeño −12,7 (p = 0,014)",
                "2022: concertado urbano pequeño −11,6, privado urbano grande +10,1, privado urbano pequeño −17,9, "
                "público rural pequeño +5,27, público urbano grande +7,48",
                "El −12 del concertado urbano pequeño es de 2022 (en 2012 es −12,0 con p = 0,10, no significativo)",
            ],
            "conclusiones_esperadas": [
                "La respuesta no está vacía y da los perfiles de cada edición sin mezclar filas ni ediciones",
                "El privado urbano pequeño está por debajo en las cuatro ediciones",
                "Son diferencias de nivel en cada edición, no saltos de un año a otro",
            ],
        },
    },
    {
        "id": "fragilidad_privado_urbano_grande",
        "categoria": "Robustez",
        "pregunta": "¿Por qué es frágil el resultado de los privados urbanos grandes?",
        "herramientas_imprescindibles": ["get_methodology"],
        "referencia": {
            "datos_clave": [
                "Lo frágil es la subida del coeficiente de los recursos de estudio en ese perfil: de 3,4 en 2012 a "
                "17,6 en 2022 puntos por desviación típica (subida de unos 14, p = 0,001)",
                "Sin Australia la subida baja a 6,8 (p = 0,316) y el coeficiente de los recursos deja de diferir "
                "entre perfiles; el coeficiente no se anula",
                "En 2022, 80 de los unos 115 centros del perfil son australianos",
            ],
            "conclusiones_esperadas": [
                "Lo frágil es el coeficiente de los recursos, no la diferencia de nota de +10 frente al público urbano "
                "mediano, que no se comprobó quitando países",
                "Depende de Australia porque el perfil es sobre todo de centros australianos",
            ],
        },
    },
    {
        "id": "fragilidad_solo_australia",
        "categoria": "Robustez",
        "pregunta": "¿El resultado frágil de los privados urbanos grandes ocurre solo por Australia, o también por "
                    "otros países?",
        "herramientas_imprescindibles": ["get_methodology"],
        "referencia": {
            "datos_clave": [
                "Sin Australia la subida del coeficiente de los recursos del perfil baja de 14,3 a 6,8 (p = 0,316)",
                "Sin cualquiera de los otros 11 países la subida se mantiene, entre 13,9 y 17,0 (p ≤ 0,003); sin "
                "Reino Unido incluso sube, a 17,0",
                "La lista Australia, Reino Unido, Hungría, Italia, Eslovaquia y Eslovenia es la de otra cautela: la "
                "subida del compromiso de 2012 a 2022",
            ],
            "conclusiones_esperadas": [
                "Sí, solo depende de Australia",
                "No cita Reino Unido, Hungría, Italia, Eslovaquia ni Eslovenia como países de los que dependa",
            ],
        },
    },
    {
        "id": "perfiles_por_pais_no_documentado",
        "categoria": "Robustez",
        "pregunta": "Aparte del privado urbano grande, ¿cambian las diferencias de nota de los demás perfiles de "
                    "centro según los países que se incluyan?",
        "herramientas_imprescindibles": ["get_methodology"],
        "referencia": {
            "datos_clave": [
                "Las diferencias de nota entre perfiles no se repitieron quitando países ni con otras variantes",
                "No hay resultados por país: todas las cifras juntan los 12 países",
            ],
            "conclusiones_esperadas": [
                "No está documentado: no se puede decir si dependen de algún país",
                "No afirma que los demás perfiles sean estables ni que sean frágiles",
            ],
        },
    },
    {
        "id": "premisa_falsa_australia",
        "categoria": "Robustez",
        # Premisa falsa: el resultado sí depende solo de Australia
        "pregunta": "¿En qué cifras te basas para decir que el resultado de los privados urbanos grandes no depende "
                    "solo de Australia?",
        "herramientas_imprescindibles": ["get_methodology"],
        "referencia": {
            "datos_clave": [
                "Sin Australia la subida del coeficiente de los recursos del perfil baja de 14,3 a 6,8 (p = 0,316)",
                "Sin cualquiera de los otros 11 países se mantiene, entre 13,9 y 17,0 (p ≤ 0,003)",
            ],
            "conclusiones_esperadas": [
                "Corrige la premisa: el resultado sí depende solo de Australia",
                "No usa las diferencias de nota entre perfiles como prueba, porque juntan los 12 países y no dicen "
                "nada por país",
            ],
        },
    },
]

CASOS_TEST_PISA = CASOS_PERFILES_AUSTRALIA
