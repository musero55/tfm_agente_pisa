"""
graficos_evaluacion.py
======================

Gráficos de una ejecución del evaluador (`evaluator.ejecutar_bateria_evaluacion`) para el notebook:

    * `grafico_criterios`: cuadrícula caso × comprobación con OK / FALLO / AVISO / ERROR, con el texto en cada celda.
    * `grafico_puntuaciones`: calidad y completitud del juez en cada caso.
    * `grafico_comparacion`: calidad de cada caso en dos ejecuciones.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Paleta: superficie y tintas neutras, dos series (azul y naranja) y colores de estado reservados
SUPERFICIE, TINTA, TINTA_SECUNDARIA, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIE_1, SERIE_2 = "#2a78d6", "#eb6834"
ESTADOS = {  # color de la celda y color del texto
    "OK": ("#0ca30c", "#ffffff"),
    "FALLO": ("#d03b3b", "#ffffff"),
    "AVISO": ("#fab219", TINTA),
    "ERROR": ("#c3c2b7", TINTA),
}
NOMBRES_CRITERIOS = {"Tools OK": "Herramientas", "Fidelidad OK": "Fidelidad", "Estilo Limpio": "Estilo"}


def _estilo(ax: plt.Axes) -> None:
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)
    ax.tick_params(colors=TINTA_SECUNDARIA, length=0)


def grafico_criterios(resultados: pd.DataFrame) -> plt.Figure:
    """Cuadrícula de las tres comprobaciones de cada caso. El estado va escrito en la celda, no solo en el color."""
    casos = resultados["ID"].tolist()
    criterios = list(NOMBRES_CRITERIOS)
    figura, ax = plt.subplots(figsize=(7.5, 0.38 * len(casos) + 1.2), facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    for fila, (_, caso) in enumerate(resultados.iterrows()):
        for columna, criterio in enumerate(criterios):
            estado = caso[criterio] if caso[criterio] in ESTADOS else "ERROR"
            fondo, texto = ESTADOS[estado]
            # Borde del color de la superficie: separa las celdas
            ax.add_patch(plt.Rectangle((columna, fila), 1, 1, facecolor=fondo, edgecolor=SUPERFICIE, linewidth=2))
            ax.text(columna + 0.5, fila + 0.5, estado, ha="center", va="center", fontsize=8.5, color=texto, fontweight="bold")
    ax.set_xlim(0, len(criterios))
    ax.set_ylim(len(casos), 0)
    ax.set_xticks(np.arange(len(criterios)) + 0.5, [NOMBRES_CRITERIOS[c] for c in criterios], color=TINTA)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(casos)) + 0.5, casos, fontsize=8.5, color=TINTA)
    ax.tick_params(length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_title(f"Comprobaciones por caso · ejecución {resultados['Ejecución'].iloc[0]}", loc="left", color=TINTA,
                 fontsize=11, pad=24)
    figura.tight_layout()
    return figura


def grafico_puntuaciones(resultados: pd.DataFrame) -> plt.Figure:
    """Calidad y completitud de cada caso (1 a 5). Los casos con error del juez no tienen puntos."""
    casos = resultados["ID"].tolist()
    posiciones = np.arange(len(casos))
    figura, ax = plt.subplots(figsize=(7.5, 0.38 * len(casos) + 1.4), facecolor=SUPERFICIE)
    _estilo(ax)
    ax.scatter(resultados["Calidad (1-5)"].astype(float), posiciones - 0.15, s=64, color=SERIE_1, marker="o",
               edgecolor=SUPERFICIE, linewidth=2, zorder=3, label="Calidad")
    ax.scatter(resultados["Completitud (1-5)"].astype(float), posiciones + 0.15, s=64, color=SERIE_2, marker="D",
               edgecolor=SUPERFICIE, linewidth=2, zorder=3, label="Completitud")
    ax.set_xlim(0.7, 5.3)
    ax.set_xticks(range(1, 6))
    ax.set_ylim(len(casos) - 0.5, -0.5)
    ax.set_yticks(posiciones, casos, fontsize=8.5, color=TINTA)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Puntuación del juez (1 a 5)", color=TINTA_SECUNDARIA)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, labelcolor=TINTA)
    ax.set_title("Calidad y completitud por caso", loc="left", color=TINTA, fontsize=11, pad=26)
    figura.tight_layout()
    return figura


def grafico_comparacion(comparacion: pd.DataFrame, columna: str = "Calidad (1-5)") -> plt.Figure:
    """`columna` de cada caso antes y después (tabla de `comparar_ejecuciones`), unidos por una línea gris."""
    antes = comparacion[(columna, "Antes")].astype(float)
    despues = comparacion[(columna, "Después")].astype(float)
    casos = comparacion.index.tolist()
    posiciones = np.arange(len(casos))
    figura, ax = plt.subplots(figsize=(7.5, 0.38 * len(casos) + 1.4), facecolor=SUPERFICIE)
    _estilo(ax)
    ax.hlines(posiciones, antes, despues, color=REJILLA, linewidth=2, zorder=2)
    ax.scatter(antes, posiciones, s=64, color=SERIE_2, marker="D", edgecolor=SUPERFICIE, linewidth=2, zorder=3, label="Antes")
    ax.scatter(despues, posiciones, s=64, color=SERIE_1, marker="o", edgecolor=SUPERFICIE, linewidth=2, zorder=4, label="Después")
    ax.set_xlim(0.7, 5.3)
    ax.set_xticks(range(1, 6))
    ax.set_ylim(len(casos) - 0.5, -0.5)
    ax.set_yticks(posiciones, casos, fontsize=8.5, color=TINTA)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel(f"{columna.replace(' (1-5)', '')} según el juez (1 a 5)", color=TINTA_SECUNDARIA)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, labelcolor=TINTA)
    ax.set_title(f"{columna.replace(' (1-5)', '')} por caso en las dos ejecuciones", loc="left", color=TINTA,
                 fontsize=11, pad=26)
    figura.tight_layout()
    return figura
