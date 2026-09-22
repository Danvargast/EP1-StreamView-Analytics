"""
metricas.py — Indicadores y tablas agregadas del proyecto.

Todas las cifras que aparecen en el informe, en el dashboard y en el resumen
ejecutivo se calculan aquí y sólo aquí. Ninguna se escribe a mano en un gráfico
o en una diapositiva: así el número del titular y el número de la tabla no
pueden divergir.

Convenciones de medición (declaradas para evitar porcentajes ambiguos):
  · "Atención"      = índice de popularidad. Se reporta la MEDIANA, nunca el
                      promedio: la distribución tiene cola larga (Gini 0,58) y
                      el promedio lo arrastran unos pocos estrenos masivos.
  · "Satisfacción"  = nota media 0–10, calculada SÓLO sobre títulos con al menos
                      una interacción. Denominador siempre explícito.
  · "Catálogo invisible" = títulos con cero interacciones registradas.
  · Cohorte de análisis por defecto = 2010–2024. 2025 se excluye de toda lectura
    de tendencia porque el 68,2% de sus títulos aún no acumula interacciones.

Ejecutar:  python src/metricas.py
"""

import numpy as np
import pandas as pd

import config as cfg


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------
def cargar(solo_maduras=False):
    """Lee el catálogo integrado. `solo_maduras=True` descarta la cohorte 2025."""
    cat = pd.read_csv(cfg.CATALOGO, parse_dates=["fecha_referencia"])
    return cat[cat.cohorte_madura].copy() if solo_maduras else cat


# --------------------------------------------------------------------------
# Indicadores de concentración
# --------------------------------------------------------------------------
def gini(valores):
    """Índice de Gini (0 = atención repartida por igual, 1 = todo en un título)."""
    x = np.sort(np.asarray(valores, dtype=float))
    x = x[~np.isnan(x)]
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    n = len(x)
    acum = np.cumsum(x)
    return float((n + 1 - 2 * acum.sum() / acum[-1]) / n)


def curva_concentracion(cat, columna="atencion"):
    """Curva de Lorenz: % acumulado de atención sobre % acumulado de títulos."""
    x = np.sort(cat[columna].dropna().values)[::-1]
    pct_titulos = np.arange(1, len(x) + 1) / len(x) * 100
    pct_atencion = np.cumsum(x) / x.sum() * 100
    return pd.DataFrame({"pct_titulos": pct_titulos, "pct_atencion": pct_atencion})


def atencion_en_top(cat, pct=10, columna="atencion"):
    """% de la atención total que concentra el `pct`% de títulos más vistos."""
    x = np.sort(cat[columna].dropna().values)[::-1]
    k = max(1, int(round(len(x) * pct / 100)))
    return float(x[:k].sum() / x.sum() * 100)


# --------------------------------------------------------------------------
# KPIs del dashboard (5 indicadores clave)
# --------------------------------------------------------------------------
def kpis(cat):
    """Devuelve el bloque de KPIs para la fila superior del dashboard."""
    con_senal = cat[~cat.sin_senal]
    return {
        "titulos": int(len(cat)),
        "atencion_top10": atencion_en_top(cat, 10),
        "catalogo_invisible_pct": float(cat.sin_senal.mean() * 100),
        "catalogo_invisible_n": int(cat.sin_senal.sum()),
        "satisfaccion_mediana": float(con_senal.satisfaccion.median()) if len(con_senal) else np.nan,
        "satisfaccion_n": int(len(con_senal)),
        "atencion_mediana": float(cat.atencion.median()),
        "gini_atencion": gini(cat.atencion),
    }


# --------------------------------------------------------------------------
# Segmentación táctica
# --------------------------------------------------------------------------
CUADRANTES = ["Motores", "Ruido", "Joyas ocultas", "Rezagados"]


def cuadrantes(cat):
    """
    Clasifica cada título con señal en una matriz atención × satisfacción,
    usando las medianas del universo filtrado como umbrales (se devuelven
    junto a la tabla para poder mostrarlos en el gráfico).

      Motores        : atención alta + satisfacción alta → renovar y escalar
      Ruido          : atención alta + satisfacción baja → riesgo de churn
      Joyas ocultas  : atención baja + satisfacción alta → activar en recomendación
      Rezagados      : atención baja + satisfacción baja → candidatos a poda
    """
    con_senal = cat[~cat.sin_senal].copy()
    if con_senal.empty:
        return con_senal.assign(cuadrante=pd.Series(dtype=str)), np.nan, np.nan

    u_at = con_senal.atencion.median()
    u_sa = con_senal.satisfaccion.median()

    alta_at = con_senal.atencion >= u_at
    alta_sa = con_senal.satisfaccion >= u_sa
    con_senal["cuadrante"] = np.select(
        [alta_at & alta_sa, alta_at & ~alta_sa, ~alta_at & alta_sa],
        ["Motores", "Ruido", "Joyas ocultas"],
        default="Rezagados",
    )
    return con_senal, float(u_at), float(u_sa)


def resumen_cuadrantes(cat):
    con_senal, u_at, u_sa = cuadrantes(cat)
    if con_senal.empty:
        return pd.DataFrame()
    tabla = (con_senal.groupby("cuadrante")
             .agg(titulos=("titulo", "size"),
                  atencion_mediana=("atencion", "median"),
                  satisfaccion_mediana=("satisfaccion", "median"),
                  pct_series=("formato", lambda s: (s == "Serie").mean() * 100),
                  pct_no_ingles=("es_no_ingles", lambda s: s.mean() * 100))
             .reindex(CUADRANTES).dropna(how="all"))
    tabla["pct_catalogo"] = tabla.titulos / len(con_senal) * 100
    return tabla.round(2)


def por_segmento(cat):
    """Rendimiento por segmento de decisión (formato × idioma)."""
    con_senal = cat[~cat.sin_senal]
    base = cat.groupby("segmento").agg(
        titulos=("titulo", "size"),
        atencion_mediana=("atencion", "median"),
        invisible_pct=("sin_senal", lambda s: s.mean() * 100),
    )
    nota = con_senal.groupby("segmento").satisfaccion.median().rename("satisfaccion_mediana")
    return base.join(nota).sort_values("atencion_mediana", ascending=False).round(2)


def evolucion_idioma(cat):
    """Participación del contenido no inglés por año de estreno."""
    maduras = cat[cat.cohorte_madura]
    serie = maduras.groupby("anio").agg(
        pct_no_ingles=("es_no_ingles", lambda s: s.mean() * 100),
        titulos=("titulo", "size"),
    )
    return serie.round(2)


def invisible_por_anio(cat):
    return (cat.groupby(["anio", "formato"]).sin_senal.mean().unstack() * 100).round(2)


# --------------------------------------------------------------------------
# Capa financiera (sólo películas con presupuesto y recaudación informados)
# --------------------------------------------------------------------------
TRAMOS = [0, 1e6, 1e7, 5e7, 1e8, 1e10]
ETIQUETAS_TRAMO = ["< 1 M", "1 – 10 M", "10 – 50 M", "50 – 100 M", "> 100 M"]


def rentabilidad(cat):
    """Tabla de ROI por tramo de presupuesto. n se reporta siempre."""
    fin = cat[cat.roi.notna()].copy()
    fin["tramo_presupuesto"] = pd.cut(fin.budget, TRAMOS, labels=ETIQUETAS_TRAMO)
    tabla = (fin.groupby("tramo_presupuesto", observed=True)
             .agg(peliculas=("roi", "size"),
                  roi_mediano=("roi", "median"),
                  pct_bajo_equilibrio=("roi", lambda s: (s < 1).mean() * 100),
                  presupuesto_total_musd=("budget", lambda s: s.sum() / 1e6),
                  atencion_mediana=("atencion", "median"),
                  satisfaccion_mediana=("satisfaccion", "median")))
    return tabla.round(2)


def correlaciones(cat):
    """Spearman entre inversión, atención y satisfacción (relación monótona)."""
    fin = cat[cat.roi.notna()]
    cols = ["budget", "revenue", "atencion", "interacciones", "satisfaccion"]
    return fin[cols].corr(method="spearman").round(2)


# --------------------------------------------------------------------------
# Cifras del titular: las que se citan en informe y resumen ejecutivo
# --------------------------------------------------------------------------
def cifras_clave():
    cat = cargar()
    maduras = cat[cat.cohorte_madura]
    con_senal = maduras[~maduras.sin_senal]

    seg = por_segmento(maduras)
    serie_no_en = seg.loc["Serie · No inglés"]
    resto = maduras[maduras.segmento != "Serie · No inglés"]
    resto_senal = resto[~resto.sin_senal]

    rent = rentabilidad(maduras)
    tramo_critico = rent.loc["1 – 10 M"]
    cuad = resumen_cuadrantes(maduras)

    invisibles = maduras[maduras.sin_senal]
    ev = evolucion_idioma(cat)

    at_fmt = maduras.groupby("formato").atencion.median()
    nota_fmt = con_senal.groupby("formato").satisfaccion.median()
    inv_fmt = maduras.groupby("formato").sin_senal.mean() * 100

    return {
        "titulos_total": len(cat),
        "titulos_maduros": len(maduras),
        "anios": f"{cfg.ANIO_MIN}–{cfg.ANIO_MAX}",
        "atencion_top1": atencion_en_top(maduras, 1),
        "atencion_top10": atencion_en_top(maduras, 10),
        "atencion_top20": atencion_en_top(maduras, 20),
        "gini": gini(maduras.atencion),
        "invisible_pct_total": cat.sin_senal.mean() * 100,
        "invisible_pct_maduro": maduras.sin_senal.mean() * 100,
        "invisible_n_maduro": int(maduras.sin_senal.sum()),
        "invisible_pct_series": (invisibles.formato == "Serie").mean() * 100,
        "invisible_pct_2025": cat[cat.anio == 2025].sin_senal.mean() * 100,
        "serie_atencion": float(at_fmt["Serie"]),
        "pelicula_atencion": float(at_fmt["Película"]),
        "serie_nota": float(nota_fmt["Serie"]),
        "pelicula_nota": float(nota_fmt["Película"]),
        "multiplo_formato": float(at_fmt["Serie"] / at_fmt["Película"]),
        "invisible_pct_series_fmt": float(inv_fmt["Serie"]),
        "invisible_pct_peliculas_fmt": float(inv_fmt["Película"]),
        "no_ingles_inicio": float(ev.pct_no_ingles.iloc[0]),
        "no_ingles_fin": float(ev.pct_no_ingles.iloc[-1]),
        "serie_noen_n": int(serie_no_en.titulos),
        "serie_noen_atencion": serie_no_en.atencion_mediana,
        "serie_noen_satisfaccion": serie_no_en.satisfaccion_mediana,
        "resto_atencion": resto.atencion.median(),
        "resto_satisfaccion": resto_senal.satisfaccion.median(),
        "multiplo_atencion": serie_no_en.atencion_mediana / resto.atencion.median(),
        "peliculas_con_roi": int(maduras.roi.notna().sum()),
        "pct_peliculas_con_roi": maduras.roi.notna().sum() / (maduras.formato == "Película").sum() * 100,
        "roi_mediano_global": maduras.roi.median(),
        "pct_bajo_equilibrio_global": (maduras.roi.dropna() < 1).mean() * 100,
        "tramo_critico_n": int(tramo_critico.peliculas),
        "tramo_critico_roi": tramo_critico.roi_mediano,
        "tramo_critico_bajo_eq": tramo_critico.pct_bajo_equilibrio,
        "tramo_critico_musd": tramo_critico.presupuesto_total_musd,
        "roi_mayor_50m": rent.loc[["50 – 100 M", "> 100 M"], "roi_mediano"].median(),
        "corr_budget_satisfaccion": correlaciones(maduras).loc["budget", "satisfaccion"],
        "corr_budget_atencion": correlaciones(maduras).loc["budget", "atencion"],
        "joyas_n": int(cuad.loc["Joyas ocultas", "titulos"]),
        "rezagados_n": int(cuad.loc["Rezagados", "titulos"]),
        "motores_n": int(cuad.loc["Motores", "titulos"]),
        "ruido_n": int(cuad.loc["Ruido", "titulos"]),
        "motores_pct_series": cuad.loc["Motores", "pct_series"],
        "con_senal_n": len(con_senal),
    }


def exportar_tablas():
    """Escribe en data/processed las tablas que consumen informe y dashboard."""
    cat = cargar()
    maduras = cat[cat.cohorte_madura]
    salidas = {
        "kpi_resumen.csv": pd.DataFrame([kpis(maduras)]),
        "tabla_segmentos.csv": por_segmento(maduras).reset_index(),
        "tabla_cuadrantes.csv": resumen_cuadrantes(maduras).reset_index(),
        "tabla_rentabilidad.csv": rentabilidad(maduras).reset_index(),
        "tabla_evolucion_idioma.csv": evolucion_idioma(cat).reset_index(),
        "tabla_invisible_anio.csv": invisible_por_anio(cat).reset_index(),
        "tabla_correlaciones.csv": correlaciones(maduras).reset_index(),
    }
    for nombre, df in salidas.items():
        df.to_csv(cfg.DIR_PROC / nombre, index=False)
    return list(salidas)


if __name__ == "__main__":
    pd.set_option("display.width", 130)
    c = cifras_clave()
    print("\n=== CIFRAS CLAVE ===")
    for k, v in c.items():
        print(f"  {k:<28} {v:,.2f}" if isinstance(v, float) else f"  {k:<28} {v}")
    print("\n=== SEGMENTOS (cohorte 2010–2024) ===")
    print(por_segmento(cargar(solo_maduras=True)).to_string())
    print("\n=== CUADRANTES ===")
    print(resumen_cuadrantes(cargar(solo_maduras=True)).to_string())
    print("\n=== RENTABILIDAD ===")
    print(rentabilidad(cargar(solo_maduras=True)).to_string())
    print("\nTablas exportadas:", ", ".join(exportar_tablas()))
