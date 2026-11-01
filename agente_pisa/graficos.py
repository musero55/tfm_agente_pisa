"""
Gráficos generados en tiempo real (etapa 2): waterfall SHAP de un perfil concreto de alumno. Solo dibuja: la
herramienta que lo llama promedia con SENWT los SHAP de los alumnos del perfil (artefactos/shap_alumnos.parquet,
una sola edición) y le pasa esas medias y el valor base. No carga ningún modelo.

Los gráficos de contexto NO se generan aquí: son PNG estáticos copiados en artefactos/img por preparar_artefactos.py.
"""
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from config import DIR_IMAGENES_TEMP, etiqueta


def _formatear(valor) -> str:
    if not isinstance(valor, (int, float, np.number)) or pd.isna(valor):
        return str(valor)
    if float(valor).is_integer() or abs(valor) >= 1000:
        return f"{valor:.0f}"
    return f"{valor:.2f}"


def guardar_waterfall(valores_shap: pd.Series, datos_perfil: pd.Series, valor_base: float, titulo: str,
                      max_variables: int = 10) -> str:
    """
    Dibuja el waterfall SHAP de un perfil y devuelve su referencia corta ('tmp/<fichero>.png').
    - valores_shap: contribución de cada variable (índice = nombre de la variable).
    - datos_perfil: valor de cada variable en el perfil (mismo índice), para mostrarlo junto a su nombre.
    """
    explicacion = shap.Explanation(
        values=valores_shap.to_numpy(dtype=float), base_values=float(valor_base),
        data=np.array([_formatear(datos_perfil.get(v, np.nan)) for v in valores_shap.index], dtype=object),
        feature_names=[etiqueta(v) for v in valores_shap.index],
    )
    shap.plots.waterfall(explicacion, max_display=max_variables, show=False)
    figura = plt.gcf()
    figura.suptitle(f"{titulo} (nota en matemáticas)", fontsize=11)
    figura.set_size_inches(9, 6)

    DIR_IMAGENES_TEMP.mkdir(parents=True, exist_ok=True)
    nombre = f"waterfall_{uuid.uuid4().hex[:10]}.png"
    figura.savefig(DIR_IMAGENES_TEMP / nombre, dpi=110, bbox_inches="tight")
    plt.close("all")
    return f"tmp/{nombre}"
