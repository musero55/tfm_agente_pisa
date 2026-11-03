"""
modelo_regresion.py
===================

Regresión por edición de la nota sobre las variables de interés, con efecto fijo de país, sobre la matriz de
`preparacion_modelo.matriz_regresion`:

    * `matriz_diseno`: columnas de la regresión de una edición. Constante, un indicador por país (efecto fijo) y
      por perfil (salvo `PERFIL_REFERENCIA`), los controles con sus indicadores de «sin dato» y las variables de
      interés: una pendiente común (`por_perfil=False`) o una por perfil (`por_perfil=True`, la variable
      multiplicada por el indicador de cada perfil, así que cada coeficiente es la pendiente de ese perfil).
    * `mco_ponderado`: mínimos cuadrados ponderados con errores típicos agrupados por centro.
    * `pesos_replicados` / `mco_brr`: los 80 pesos replicados de PISA y la regresión con errores típicos de
      muestreo calculados con ellos (BRR con el ajuste de Fay), el método oficial de PISA.
    * `estimar_con_rubin`: la regresión con cada valor plausible, combinada con las reglas de Rubin (media de los
      coeficientes; varianza dentro más (1 + 1/M) por la varianza entre valores plausibles). La varianza dentro es
      la agrupada por centro o, si se pasan pesos replicados, la de BRR.
    * `estimar_por_edicion`: `estimar_con_rubin` en cada edición, para repetir el modelo con otras variables.
    * `cambio_entre_ediciones`: cambio de unos coeficientes entre dos ediciones y contraste de que es igual en todos.
    * `contraste_igualdad`: contraste de Wald de que varios coeficientes son iguales entre sí.
    * `valores_plausibles_completos`: los valores plausibles de un dominio que tienen todas las filas.
    * `coeficientes_con_error`: «coeficiente (error típico)» de unos términos por edición, para mostrarlos.

Los errores típicos agrupados por centro aproximan los de PISA; `03_errores_brr` los compara con los de BRR en
el modelo principal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.pisa_pipeline import rutas_datos_anuales
from src.preparacion_modelo import CONTROLES, DE_INTERES
from src.tabla_alumno import CLAVES_ALUMNO

PERFIL_REFERENCIA = 'PUB_URB_MED'   # el perfil con más centros: los indicadores de perfil se miden frente a él
NUMERO_REPLICAS = 80
# Columnas de los pesos replicados en cada edición (en 2012 tienen otro nombre)
COLUMNAS_REPLICAS = {2012: [f'W_FSTR{replica}' for replica in range(1, NUMERO_REPLICAS + 1)],
                     **{edicion: [f'W_FSTURWT{replica}' for replica in range(1, NUMERO_REPLICAS + 1)] for edicion in (2015, 2018, 2022)}}
FACTOR_FAY = 0.5   # ajuste de Fay de PISA: cada réplica multiplica el peso de la mitad de las zonas por 1,5 y el de la otra mitad por 0,5


def matriz_diseno(datos: pd.DataFrame, por_perfil: bool, controles: list[str] = CONTROLES,
                  de_interes: list[str] = DE_INTERES) -> pd.DataFrame:
    """Columnas de la regresión para las filas de `datos` (una edición de `matriz_regresion`). Las pendientes por
    perfil se llaman `<variable>:<perfil>`. Se quitan las columnas sin variación (por ejemplo, un indicador de
    «sin dato» de una variable que no tiene huecos en esa edición) salvo la constante."""
    diseno = pd.DataFrame({'constante': 1.0}, index=datos.index)
    # Efecto fijo de país: un indicador por país salvo el primero, que queda en la constante
    paises = pd.get_dummies(datos['CNT'], prefix='pais', dtype=float)
    diseno = diseno.join(paises.drop(columns=paises.columns[0]))
    # Nivel propio de cada perfil, frente al de referencia
    perfiles = sorted(datos['perfil'].unique())
    for perfil in perfiles:
        if perfil != PERFIL_REFERENCIA:
            diseno[f'perfil_{perfil}'] = (datos['perfil'] == perfil).astype(float)
    for variable in de_interes:
        if por_perfil:
            # Una columna por perfil: la variable en los alumnos del perfil y 0 en los demás (también el de referencia)
            for perfil in perfiles:
                diseno[f'{variable}:{perfil}'] = datos[variable] * (datos['perfil'] == perfil)
        else:
            diseno[variable] = datos[variable]
    indicadores = [f'sin_{variable}' for variable in controles if f'sin_{variable}' in datos.columns]
    diseno = diseno.join(datos[controles + indicadores])
    constantes = [columna for columna in diseno.columns if columna != 'constante' and diseno[columna].nunique() < 2]
    return diseno.drop(columns=constantes)


def valores_plausibles_completos(datos: pd.DataFrame, dominio: str = 'MATH') -> list[str]:
    """Columnas de valores plausibles de `dominio` que tienen todas las filas de `datos` (5 en 2012, 10 en las demás)."""
    return [columna for columna in datos.columns if columna.startswith('PV') and columna.endswith(dominio) and datos[columna].notna().all()]


def mco_ponderado(diseno: pd.DataFrame, nota: pd.Series, pesos: pd.Series, grupos: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Coeficientes de la regresión de `nota` sobre `diseno` por mínimos cuadrados ponderados con `pesos`, y su matriz
    de covarianzas agrupada por `grupos` (estimador sándwich con la corrección G/(G-1)·(N-1)/(N-K))."""
    matriz = diseno.to_numpy(dtype=float)
    valores_nota = nota.to_numpy(dtype=float)
    valores_peso = pesos.to_numpy(dtype=float)
    # (X'WX)^-1: el «pan» del sándwich
    inversa = np.linalg.inv(matriz.T @ (matriz * valores_peso[:, None]))
    coeficientes = inversa @ (matriz.T @ (valores_peso * valores_nota))
    residuos = valores_nota - matriz @ coeficientes
    # Suma por centro de peso · residuo · fila de diseño: el «relleno», que admite errores correlacionados dentro del centro
    contribuciones = pd.DataFrame(matriz * (valores_peso * residuos)[:, None]).groupby(grupos.to_numpy()).sum().to_numpy()
    filas, columnas, numero_grupos = len(valores_nota), matriz.shape[1], contribuciones.shape[0]
    correccion = numero_grupos / (numero_grupos - 1) * (filas - 1) / (filas - columnas)
    covarianzas = correccion * inversa @ (contribuciones.T @ contribuciones) @ inversa
    return pd.Series(coeficientes, index=diseno.columns), pd.DataFrame(covarianzas, index=diseno.columns, columns=diseno.columns)


def pesos_replicados(ruta_raw_base: str, datos: pd.DataFrame, peso_col: str = 'SENWT') -> pd.DataFrame:
    """Los `NUMERO_REPLICAS` pesos replicados de PISA de cada fila de `datos` (con `CLAVES_ALUMNO`, `year` y
    `W_FSTUWT`), leídos de los datos de cada edición, con el mismo índice que `datos` y columnas `replica_1` ...
    `replica_80`. Se pasan a la escala de `peso_col` multiplicándolos por `peso_col` / `W_FSTUWT` del alumno (en
    `SENWT` es casi constante dentro de cada país-edición; se aplica alumno a alumno)."""
    partes = []
    for edicion in sorted(datos['year'].unique()):
        # Réplicas de la edición, cruzadas con los alumnos por su clave
        replicas = pd.read_parquet(rutas_datos_anuales(ruta_raw_base, edicion)[0], columns=CLAVES_ALUMNO + COLUMNAS_REPLICAS[edicion])
        replicas = replicas.astype({clave: str for clave in CLAVES_ALUMNO})
        replicas.columns = CLAVES_ALUMNO + [f'replica_{replica}' for replica in range(1, NUMERO_REPLICAS + 1)]
        filas = datos.loc[datos['year'] == edicion, CLAVES_ALUMNO]
        partes.append(filas.reset_index().merge(replicas, on=CLAVES_ALUMNO, how='left', validate='one_to_one').set_index('index'))
    replicas = pd.concat(partes).loc[datos.index].drop(columns=CLAVES_ALUMNO)
    if replicas.isna().any().any():
        raise ValueError('Hay alumnos sin pesos replicados')
    return replicas.mul(datos[peso_col] / datos['W_FSTUWT'], axis=0)


def _coeficientes_mco(matriz: np.ndarray, pesos: np.ndarray, notas: np.ndarray) -> np.ndarray:
    """Coeficientes de mínimos cuadrados ponderados de cada columna de `notas` sobre `matriz` (columnas, una por nota)."""
    return np.linalg.solve(matriz.T @ (matriz * pesos[:, None]), matriz.T @ (pesos[:, None] * notas))


def mco_brr(diseno: pd.DataFrame, notas: pd.DataFrame, pesos: pd.Series, replicas: pd.DataFrame) -> tuple[list[pd.Series], list[pd.DataFrame]]:
    """Para cada columna de `notas` (un valor plausible), los coeficientes de su regresión sobre `diseno` con `pesos` y
    su matriz de covarianzas de muestreo por BRR: la regresión se repite con cada peso replicado de `replicas` y la
    covarianza es la suma de los productos de las desviaciones de cada réplica dividida por R·(1 − `FACTOR_FAY`)²."""
    matriz, valores = diseno.to_numpy(dtype=float), notas.to_numpy(dtype=float)
    # Todos los valores plausibles a la vez: una columna de coeficientes por valor plausible
    completos = _coeficientes_mco(matriz, pesos.to_numpy(dtype=float), valores)
    # Desviación de cada réplica respecto a la estimación con el peso completo (réplica × coeficiente × valor plausible)
    desviaciones = np.stack([_coeficientes_mco(matriz, replicas[columna].to_numpy(dtype=float), valores) - completos for columna in replicas.columns])
    escala = replicas.shape[1] * (1 - FACTOR_FAY) ** 2
    estimaciones = [pd.Series(completos[:, posicion], index=diseno.columns) for posicion in range(valores.shape[1])]
    covarianzas = [pd.DataFrame(desviaciones[:, :, posicion].T @ desviaciones[:, :, posicion] / escala, index=diseno.columns, columns=diseno.columns)
                   for posicion in range(valores.shape[1])]
    return estimaciones, covarianzas


def estimar_con_rubin(datos: pd.DataFrame, diseno: pd.DataFrame, dominio: str = 'MATH', peso_col: str = 'SENWT',
                      grupo_col: str = 'centro', replicas: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """La regresión con cada valor plausible de `dominio` que tienen todas las filas, combinada con las reglas de
    Rubin. La varianza de muestreo es la agrupada por `grupo_col` (`mco_ponderado`) o, si se pasan los pesos
    replicados de `pesos_replicados` (mismas filas que `datos`), la de BRR (`mco_brr`). Devuelve una tabla por
    coeficiente (coeficiente, error típico, intervalo del 95 %, valor p y % de la varianza que viene de los valores
    plausibles) y la matriz de covarianzas total."""
    valores_plausibles = valores_plausibles_completos(datos, dominio)
    if replicas is None:
        estimaciones, covarianzas = [], []
        for columna in valores_plausibles:
            coeficientes, covarianza = mco_ponderado(diseno, datos[columna], datos[peso_col], datos[grupo_col])
            estimaciones.append(coeficientes)
            covarianzas.append(covarianza)
    else:
        estimaciones, covarianzas = mco_brr(diseno, datos[valores_plausibles], datos[peso_col], replicas)
    # Reglas de Rubin
    estimaciones = pd.DataFrame(estimaciones)
    numero = len(valores_plausibles)
    dentro = sum(covarianzas) / numero   # varianza de muestreo media
    entre = estimaciones.cov() if numero > 1 else dentro * 0   # variación de los coeficientes entre valores plausibles
    total = dentro + (1 + 1 / numero) * entre
    coeficiente = estimaciones.mean()
    error = np.sqrt(np.diag(total))
    tabla = pd.DataFrame({'coeficiente': coeficiente, 'error_tipico': error,
                          'inferior_95': coeficiente - 1.96 * error, 'superior_95': coeficiente + 1.96 * error,
                          'valor_p': 2 * stats.norm.sf(np.abs(coeficiente / error)),
                          '% varianza entre PV': 100 * (1 + 1 / numero) * np.diag(entre) / np.diag(total),
                          'valores_plausibles': numero})
    return tabla, total


def estimar_por_edicion(matriz: pd.DataFrame, por_perfil: bool, dominio: str = 'MATH', replicas: pd.DataFrame | None = None,
                        **opciones_diseno) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    """`estimar_con_rubin` en cada edición de `matriz` con la nota de `dominio`, con el diseño de `matriz_diseno`
    (`opciones_diseno` pasa `controles` y `de_interes`) y, si se pasan, los pesos replicados de `pesos_replicados`
    (mismo índice que `matriz`). Devuelve la tabla de todas las ediciones, con índice (`year`, `termino`), y la
    matriz de covarianzas de cada edición."""
    tablas, covarianzas = {}, {}
    for edicion in sorted(matriz['year'].unique()):
        en_edicion = matriz['year'] == edicion
        datos_edicion = matriz[en_edicion].reset_index(drop=True)
        replicas_edicion = None if replicas is None else replicas[en_edicion].reset_index(drop=True)
        tablas[edicion], covarianzas[edicion] = estimar_con_rubin(datos_edicion, matriz_diseno(datos_edicion, por_perfil, **opciones_diseno), dominio=dominio,
                                                                  replicas=replicas_edicion)
    return pd.concat(tablas, names=['year', 'termino']), covarianzas


def cambio_entre_ediciones(tabla: pd.DataFrame, covarianzas: dict[int, pd.DataFrame], nombres: list[str], inicio: int,
                           final: int) -> tuple[pd.DataFrame, tuple[float, int, float]]:
    """Cambio de los coeficientes `nombres` de `inicio` a `final` (tabla y covarianzas de `estimar_por_edicion`),
    como diferencia de dos estimaciones independientes: coeficientes de las dos ediciones, cambio, error típico y
    valor p. Con más de un nombre, también el contraste de Wald de que el cambio es igual en todos."""
    # Las ediciones son muestras independientes: la covarianza del cambio es la suma de las dos
    antes, despues = tabla.xs(inicio, level='year').loc[nombres, 'coeficiente'], tabla.xs(final, level='year').loc[nombres, 'coeficiente']
    varianza = covarianzas[inicio].loc[nombres, nombres] + covarianzas[final].loc[nombres, nombres]
    error = np.sqrt(np.diag(varianza))
    cambio = pd.DataFrame({inicio: antes, final: despues, 'cambio': despues - antes, 'error_tipico': error,
                           'valor_p': 2 * stats.norm.sf(np.abs((despues - antes) / error))})
    igualdad = contraste_igualdad(despues - antes, varianza, nombres) if len(nombres) > 1 else (np.nan, 0, np.nan)
    return cambio, igualdad


def contraste_igualdad(coeficientes: pd.Series, covarianzas: pd.DataFrame, nombres: list[str]) -> tuple[float, int, float]:
    """Contraste de Wald de que los coeficientes `nombres` son todos iguales: estadístico, grados de libertad
    (número de coeficientes menos uno) y valor p con la ji cuadrado."""
    # Cada fila compara un coeficiente con el primero: todos iguales si todas las diferencias son 0
    restricciones = np.zeros((len(nombres) - 1, len(nombres)))
    restricciones[:, 0] = -1
    restricciones[np.arange(len(nombres) - 1), np.arange(1, len(nombres))] = 1
    diferencias = restricciones @ coeficientes[nombres].to_numpy()
    varianza = restricciones @ covarianzas.loc[nombres, nombres].to_numpy() @ restricciones.T
    estadistico = float(diferencias @ np.linalg.solve(varianza, diferencias))
    grados = len(nombres) - 1
    return estadistico, grados, float(stats.chi2.sf(estadistico, grados))


def coeficientes_con_error(tabla: pd.DataFrame, terminos: list[str], decimales: int = 1) -> pd.DataFrame:
    """«coeficiente (error típico)» como texto, redondeados a `decimales`, de los `terminos` de `tabla` (la de
    `estimar_por_edicion`, con índice edición y término): una fila por término, en el orden de `terminos` y sin los
    que no están en `tabla`, y una columna por edición."""
    nombre_termino = tabla.index.names[1]
    filas = tabla.reset_index()
    filas = filas[filas[nombre_termino].isin(terminos)]
    texto = filas['coeficiente'].round(decimales).astype(str) + ' (' + filas['error_tipico'].round(decimales).astype(str) + ')'
    tabla_texto = filas.assign(texto=texto).pivot(index=nombre_termino, columns='year', values='texto')
    return tabla_texto.loc[[termino for termino in terminos if termino in tabla_texto.index]]
