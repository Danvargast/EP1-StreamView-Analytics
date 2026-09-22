"""
config.py — Parámetros globales del proyecto StreamView Analytics (EP1).

Centraliza rutas, sistema de color y estilo tipográfico para que el informe,
el dashboard y el resumen ejecutivo compartan exactamente la misma identidad
visual (coherencia entre visualizaciones, propósito y audiencia — IE9).

Asignatura : ADY1104 Visualización de Datos — DUOC UC, Sede Los Lagos
Equipo     : Felipe Ángel · Daniel Vargas
"""

from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# 0. Compatibilidad pandas 3.x + Streamlit
#    pandas 3 activa por defecto el tipo string respaldado por PyArrow. Ese
#    backend produce una falla de segmentación cuando un DataFrame con columnas
#    de texto se construye dentro del hilo de trabajo que Streamlit crea en cada
#    re-ejecución, es decir, cada vez que el usuario mueve un filtro. Se fuerza
#    el tipo de texto clásico antes de crear cualquier DataFrame. En pandas 2.x
#    la opción existe y ya viene en False, de modo que la línea es inocua.
# --------------------------------------------------------------------------
try:
    pd.options.future.infer_string = False
except Exception:          # pragma: no cover — versiones sin la opción
    pass


# --------------------------------------------------------------------------
# 1. Rutas del proyecto (todas relativas a la raíz, para reproducibilidad)
# --------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]

DIR_RAW = RAIZ / "data" / "raw"
DIR_PROC = RAIZ / "data" / "processed"
DIR_IMG = RAIZ / "images"
DIR_DOCS = RAIZ / "docs"

CSV_PELICULAS = DIR_RAW / "netflix_movies_detailed_up_to_2025.csv"
CSV_SERIES = DIR_RAW / "netflix_tv_shows_detailed_up_to_2025.csv"

CATALOGO = DIR_PROC / "catalogo_integrado.csv"

for _d in (DIR_PROC, DIR_IMG, DIR_DOCS):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 2. Reglas analíticas explícitas
#    Se declaran como constantes para que ninguna cifra del informe dependa
#    de un criterio implícito dentro de un gráfico.
# --------------------------------------------------------------------------
ANIO_MIN = 2010
ANIO_MAX = 2025
ANIO_CIERRE = 2024        # última cohorte madura; 2025 se excluye de tendencias
PCT_SIN_VOTOS_2025 = 68.2  # evidencia que justifica excluir 2025

# --------------------------------------------------------------------------
# 3. Sistema de color (superficie clara, validado para daltonismo)
#    Paleta categórica: sólo se usan 3 ranuras; más de 3 se pliega a "Otros".
# --------------------------------------------------------------------------
SUPERFICIE = "#fcfcfb"     # fondo del gráfico
PLANO = "#f9f9f7"          # fondo de página
TINTA = "#0b0b0b"          # texto primario
TINTA_2 = "#52514e"        # texto secundario
TINTA_3 = "#898781"        # ejes y etiquetas menores
REJILLA = "#e1e0d9"        # línea de rejilla (hairline)
EJE = "#c3c2b7"            # línea base

SERIE_1 = "#2a78d6"        # azul    — ranura categórica 1
SERIE_2 = "#eb6834"        # naranja — ranura categórica 2
SERIE_3 = "#1baf7a"        # aqua    — ranura categórica 3 (exige etiqueta visible)
CATEGORICA = [SERIE_1, SERIE_2, SERIE_3]

# Estados reservados: nunca se usan como color de serie.
OK = "#0ca30c"
ALERTA = "#fab219"
GRAVE = "#ec835a"
CRITICO = "#d03b3b"

NEUTRO = "#b9b8b1"         # "todo lo demás" cuando se destaca un solo dato

# Rampa secuencial de un solo tono (azul, claro → oscuro)
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

FUENTE = "DejaVu Sans"     # sans del sistema; sin serif ni tipografía display


def estilo_matplotlib():
    """Aplica el estilo del proyecto a matplotlib. Llamar una sola vez."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "font.family": FUENTE,
        "font.size": 11,
        "text.color": TINTA,
        "axes.edgecolor": EJE,
        "axes.labelcolor": TINTA_2,
        "axes.titlecolor": TINTA,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": REJILLA,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",       # rejilla sólida: el punteado es ruido
        "xtick.color": TINTA_3,
        "ytick.color": TINTA_3,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "figure.dpi": 130,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


FUENTE_DATO = ("Fuente: catálogo Netflix hasta 2025 (movies + tv shows), "
               "31.991 títulos · Elaboración propia — StreamView Analytics")
