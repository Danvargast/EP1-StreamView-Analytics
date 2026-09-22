"""
graficos.py — Genera las 8 figuras del informe ejecutivo en images/.

Reglas de diseño aplicadas en todas las figuras (Unidad 1 del curso):

  · Titulación comunicacional: el título enuncia la CONCLUSIÓN, no el tema.
    "Ventas por región" es descriptivo; "La región Centro concentra el 45% de
    las ventas" es comunicacional. Se usa siempre el segundo.
  · Jerarquía visual: un solo dato destacado por figura (color de énfasis);
    todo lo demás en gris neutro. El peso visual es proporcional a la
    importancia del dato.
  · Señal sobre ruido: rejilla hairline sólida, sin bordes en las marcas,
    sin etiquetas en todos los puntos, sin decoración.
  · Denominador explícito: cada figura declara n y la cohorte usada.
  · Nunca doble eje: dos magnitudes de escala distinta se resuelven con
    small multiples o indexando a una base común.
  · Nunca se comparan categorías de vocabularios distintos: los géneros de
    series y de películas vienen de taxonomías diferentes en la fuente, así
    que se comparan por separado (F8).
  · Paleta validada para daltonismo (ΔE CVD ≥ 8 entre pares adyacentes).

Ejecutar:  python src/graficos.py
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

import config as cfg
import metricas as M

cfg.estilo_matplotlib()

ANCHO = 9.6


# --------------------------------------------------------------------------
# Utilidades de presentación
# --------------------------------------------------------------------------
def num(valor, dec=1):
    """Formato chileno: coma decimal, punto de miles."""
    s = f"{valor:,.{dec}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def titular(fig, titulo, bajada, y=1.035):
    """Título comunicacional + subtítulo de contexto (período, unidad, n)."""
    fig.text(0.012, y, titulo, fontsize=15, fontweight="bold",
             color=cfg.TINTA, va="bottom", ha="left")
    fig.text(0.012, y - 0.018, bajada, fontsize=10, color=cfg.TINTA_2,
             va="top", ha="left")


def pie(fig, nota, y=-0.055):
    fig.text(0.012, y, nota, fontsize=8, color=cfg.TINTA_3, va="top", ha="left")


def limpiar(ax, ejes=("top", "right")):
    for e in ejes:
        ax.spines[e].set_visible(False)


def guardar(fig, nombre):
    ruta = cfg.DIR_IMG / nombre
    fig.savefig(ruta, bbox_inches="tight", pad_inches=0.45)
    plt.close(fig)
    print(f"  ✓ {nombre}")
    return ruta


# --------------------------------------------------------------------------
# F1 · Concentración de la atención (curva de Lorenz)
#      Tarea visual: distribución acumulada → curva de concentración
#      Un solo dato destacado: el punto del 10%.
# --------------------------------------------------------------------------
def f1_concentracion(cat):
    curva = M.curva_concentracion(cat)
    top10 = M.atencion_en_top(cat, 10)
    top1 = M.atencion_en_top(cat, 1)

    fig, ax = plt.subplots(figsize=(ANCHO, 5.0))
    ax.plot([0, 100], [0, 100], color=cfg.NEUTRO, lw=1.6, zorder=1)
    ax.text(78, 72, "Reparto perfectamente igualitario", fontsize=9,
            color=cfg.TINTA_3, rotation=30, ha="center", va="center")

    ax.plot(curva.pct_titulos, curva.pct_atencion, color=cfg.SERIE_1, lw=2.2, zorder=3)
    ax.fill_between(curva.pct_titulos, curva.pct_atencion, curva.pct_titulos,
                    color=cfg.SERIE_1, alpha=0.08, zorder=2)

    ax.plot([10, 10], [0, top10], color=cfg.CRITICO, lw=2, zorder=4)
    ax.scatter([10], [top10], s=75, color=cfg.CRITICO, zorder=5,
               edgecolor=cfg.SUPERFICIE, linewidth=2)
    ax.annotate(f"El 10% de los títulos\nconcentra el {num(top10)}% de la atención",
                xy=(10.8, top10), xytext=(26, 33), fontsize=11,
                color=cfg.TINTA, fontweight="bold", linespacing=1.4,
                arrowprops=dict(arrowstyle="-", color=cfg.CRITICO, lw=1.4))

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("% acumulado de títulos, ordenados de mayor a menor atención")
    ax.set_ylabel("% acumulado de atención")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    limpiar(ax)

    titular(fig,
            "La atención está concentrada: 1 de cada 10 títulos se lleva la mitad del catálogo",
            f"Curva de concentración de la atención · {num(len(cat), 0)} títulos · estrenos "
            f"{cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · índice de Gini {num(M.gini(cat.atencion), 2)} · "
            f"el 1% más visto ya concentra el {num(top1)}%")
    pie(fig, "Atención = índice de popularidad del título. " + cfg.FUENTE_DATO)
    return guardar(fig, "f1_concentracion_atencion.png")


# --------------------------------------------------------------------------
# F2 · Rendimiento por formato (small multiples: dos escalas, nunca doble eje)
# --------------------------------------------------------------------------
def f2_formato(mad):
    con_senal = mad[~mad.sin_senal]
    at = mad.groupby("formato").atencion.median().reindex(["Serie", "Película"])
    sa = con_senal.groupby("formato").satisfaccion.median().reindex(["Serie", "Película"])
    multiplo = at["Serie"] / at["Película"]

    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 3.1))
    paneles = [
        (axes[0], at, "Atención mediana por título", at.max() * 1.45),
        (axes[1], sa, "Satisfacción mediana (nota 0–10)", 10.0),
    ]
    for ax, serie, subtitulo, tope in paneles:
        barras = ax.barh(serie.index, serie.values, color=[cfg.SERIE_1, cfg.NEUTRO],
                         height=0.36, zorder=3)
        for barra, valor in zip(barras, serie.values):
            ax.text(valor + tope * 0.022, barra.get_y() + barra.get_height() / 2,
                    num(valor, 1), va="center", ha="left", fontsize=12.5,
                    fontweight="bold", color=cfg.TINTA)
        ax.set_xlim(0, tope)
        ax.set_ylim(1.55, -0.55)
        ax.set_title(subtitulo, fontsize=10.5, color=cfg.TINTA_2, loc="left", pad=8)
        ax.grid(visible=False)
        ax.set_xticks([])
        limpiar(ax, ("top", "right", "bottom"))
        ax.tick_params(axis="y", labelsize=11.5, labelcolor=cfg.TINTA, length=0)

    axes[0].text(at.max() * 1.10, 0.5, f"×{num(multiplo, 1)}", fontsize=21,
                 fontweight="bold", color=cfg.SERIE_1, ha="center", va="center")
    axes[0].text(at.max() * 1.10, 1.06, "más atención\npor título", fontsize=8.5,
                 color=cfg.TINTA_2, ha="center", va="center", linespacing=1.3)

    titular(fig,
            f"Una serie capta {num(multiplo, 1)} veces más atención que una película, y con mejor nota",
            f"Cohorte madura {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · {num(len(mad), 0)} títulos · "
            f"la satisfacción se calcula sobre los {num(len(con_senal), 0)} títulos con al menos "
            "una interacción", y=1.10)
    pie(fig, "Se usa la mediana y no el promedio porque la distribución de atención tiene cola larga: "
             "unos pocos estrenos masivos desplazarían el promedio. " + cfg.FUENTE_DATO, y=-0.16)
    return guardar(fig, "f2_rendimiento_formato.png")


# --------------------------------------------------------------------------
# F3 · El riesgo del formato ganador (catálogo invisible)
# --------------------------------------------------------------------------
def f3_invisible(mad, cat, cifras):
    inv = (mad.groupby("formato").sin_senal.mean() * 100).reindex(["Serie", "Película"])
    n_inv = mad.groupby("formato").sin_senal.sum().reindex(["Serie", "Película"])

    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 3.6),
                             gridspec_kw={"width_ratios": [1, 1.15], "wspace": 0.30})

    ax = axes[0]
    barras = ax.barh(inv.index, inv.values, color=[cfg.CRITICO, cfg.NEUTRO],
                     height=0.34, zorder=3)
    for barra, valor, n in zip(barras, inv.values, n_inv.values):
        ax.text(valor + 0.8, barra.get_y() + barra.get_height() / 2,
                f"{num(valor)}%   {num(n, 0)} títulos", va="center", ha="left",
                fontsize=11, fontweight="bold", color=cfg.TINTA)
    ax.set_xlim(0, inv.max() * 2.35)
    ax.set_ylim(1.55, -0.55)
    ax.set_xticks([])
    ax.grid(visible=False)
    limpiar(ax, ("top", "right", "bottom"))
    ax.tick_params(axis="y", labelsize=11.5, labelcolor=cfg.TINTA, length=0)
    ax.set_title("Títulos sin ninguna interacción registrada", fontsize=10.5,
                 color=cfg.TINTA_2, loc="left", pad=8)

    # Panel derecho: la cohorte 2025 no es comparable y se declara explícitamente
    ax2 = axes[1]
    serie_anual = cat.groupby("anio").sin_senal.mean() * 100
    maduro = serie_anual[serie_anual.index <= cfg.ANIO_CIERRE]
    ax2.plot(maduro.index, maduro.values, color=cfg.SERIE_1, lw=2.2, zorder=3)
    ax2.scatter([2025], [serie_anual.loc[2025]], s=55, color=cfg.TINTA_3, zorder=4)
    ax2.annotate("2025: cohorte aún inmadura,\nexcluida del análisis",
                 xy=(2024.7, serie_anual.loc[2025]), xytext=(2013.6, 56),
                 fontsize=8.5, color=cfg.TINTA_2, linespacing=1.35,
                 arrowprops=dict(arrowstyle="-", color=cfg.TINTA_3, lw=0.9))
    ax2.set_ylim(0, 82)
    ax2.set_yticks([0, 20, 40, 60, 80])
    ax2.set_xticks(range(2010, 2026, 3))
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    limpiar(ax2)
    ax2.set_title("Catálogo invisible por año de estreno", fontsize=10.5,
                  color=cfg.TINTA_2, loc="left", pad=8)

    titular(fig,
            "El formato que más rinde es también el más riesgoso: 1 de cada 5 series no llega a nadie",
            f"Catálogo invisible = títulos con cero interacciones · cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} "
            f"({num(len(mad), 0)} títulos) · {num(cifras['invisible_pct_series'])}% del catálogo "
            "invisible son series", y=1.09)
    pie(fig, "La cohorte 2025 se muestra sólo como referencia: sus títulos aún no han tenido tiempo de "
             "acumular interacciones y no son comparables con los años anteriores. " + cfg.FUENTE_DATO,
        y=-0.14)
    return guardar(fig, "f3_catalogo_invisible.png")


# --------------------------------------------------------------------------
# F4 · Matriz de decisión atención × satisfacción
# --------------------------------------------------------------------------
def f4_cuadrantes(mad):
    puntos, u_at, u_sa = M.cuadrantes(mad)
    tabla = M.resumen_cuadrantes(mad)
    muestra = puntos.sample(n=min(6000, len(puntos)), random_state=7)

    fig, ax = plt.subplots(figsize=(ANCHO, 6.2))
    otros = muestra[muestra.cuadrante != "Joyas ocultas"]
    joyas = muestra[muestra.cuadrante == "Joyas ocultas"]
    ax.scatter(otros.atencion, otros.satisfaccion, s=7, alpha=0.14,
               color=cfg.TINTA_3, linewidths=0, zorder=2)
    ax.scatter(joyas.atencion, joyas.satisfaccion, s=8, alpha=0.30,
               color=cfg.SERIE_1, linewidths=0, zorder=3)

    ax.axvline(u_at, color=cfg.EJE, lw=1.2, zorder=4)
    ax.axhline(u_sa, color=cfg.EJE, lw=1.2, zorder=4)

    ax.set_xscale("log")
    ax.set_xlim(0.8, 3000)
    ax.set_ylim(1.2, 11.6)

    etiquetas = {
        "Joyas ocultas": (2.6, 11.0, cfg.SERIE_1, "Inventario ya pagado que nadie descubre"),
        "Motores": (330, 11.0, cfg.TINTA, "Renovar y escalar"),
        "Rezagados": (2.6, 3.0, cfg.TINTA_2, "Candidatos a poda o renegociación"),
        "Ruido": (330, 3.0, cfg.TINTA_2, "Atraen, pero decepcionan"),
    }
    for nombre, (x, y, color, glosa) in etiquetas.items():
        if nombre not in tabla.index:
            continue
        fila = tabla.loc[nombre]
        ax.text(x, y, nombre.upper(), fontsize=10.5, fontweight="bold", color=color,
                ha="center", va="center")
        ax.text(x, y - 0.42, f"{num(fila.titulos, 0)} títulos · {num(fila.pct_catalogo)}%",
                fontsize=9.5, color=color, ha="center", va="center")
        ax.text(x, y - 0.86, glosa, fontsize=8.5, color=cfg.TINTA_3,
                ha="center", va="center")

    ax.set_xlabel(f"Atención por título (escala logarítmica) — la línea marca la mediana: {num(u_at)}")
    ax.set_ylabel(f"Satisfacción (nota 0–10) — la línea marca la mediana: {num(u_sa)}")
    ax.grid(visible=False)
    limpiar(ax)

    titular(fig,
            f"{num(tabla.loc['Joyas ocultas', 'titulos'], 0)} títulos ya pagados gustan más que la "
            "mediana y, aun así, nadie los ve",
            f"Cada punto es un título · {num(len(puntos), 0)} títulos con al menos una interacción · "
            f"cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · en azul, el cuadrante de Joyas ocultas",
            y=1.025)
    pie(fig, "Se grafica una muestra aleatoria de 6.000 puntos para evitar el solapamiento; los recuentos "
             "de cada cuadrante corresponden al universo completo. Los umbrales son las medianas del "
             "propio conjunto filtrado. " + cfg.FUENTE_DATO, y=-0.045)
    return guardar(fig, "f4_matriz_cuadrantes.png")


# --------------------------------------------------------------------------
# F5 · Rentabilidad por tramo de presupuesto
# --------------------------------------------------------------------------
def f5_rentabilidad(mad, cifras):
    rent = M.rentabilidad(mad)
    critico = "1 – 10 M"
    etiquetas_x = [f"{i}\nn={num(n, 0)}" for i, n in zip(rent.index, rent.peliculas)]

    fig, axes = plt.subplots(1, 2, figsize=(ANCHO, 4.2),
                             gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.42})

    ax = axes[0]
    colores = [cfg.CRITICO if i == critico else cfg.SERIE_1 for i in rent.index]
    barras = ax.bar(range(len(rent)), rent.roi_mediano, color=colores, width=0.5, zorder=3)
    ax.axhline(1, color=cfg.TINTA_2, lw=1.4, zorder=4)
    ax.text(len(rent) - 0.55, 0.88, "Punto de equilibrio (ROI = 1)", fontsize=8.5,
            color=cfg.TINTA_2, ha="right", va="top")
    for barra, valor in zip(barras, rent.roi_mediano):
        ax.text(barra.get_x() + barra.get_width() / 2, valor + 0.08, num(valor, 2),
                ha="center", va="bottom", fontsize=11, fontweight="bold", color=cfg.TINTA)
    ax.set_xticks(range(len(rent)))
    ax.set_xticklabels(etiquetas_x, fontsize=9)
    ax.set_ylim(0, 3.6)
    ax.set_ylabel("ROI mediano (recaudación / presupuesto)")
    ax.set_xlabel("Tramo de presupuesto de la película (USD)", labelpad=8)
    ax.grid(axis="x", visible=False)
    limpiar(ax)

    ax2 = axes[1]
    pct = rent.pct_bajo_equilibrio
    colores2 = [cfg.CRITICO if i == critico else cfg.NEUTRO for i in pct.index]
    barras2 = ax2.barh(range(len(pct)), pct.values, color=colores2, height=0.5, zorder=3)
    for barra, valor in zip(barras2, pct.values):
        ax2.text(valor + 1.4, barra.get_y() + barra.get_height() / 2, f"{num(valor)}%",
                 va="center", ha="left", fontsize=10.5, fontweight="bold", color=cfg.TINTA)
    ax2.set_yticks(range(len(pct)))
    ax2.set_yticklabels(pct.index, fontsize=9.5)
    ax2.set_xlim(0, 66)
    ax2.invert_yaxis()
    ax2.set_xticks([])
    ax2.grid(visible=False)
    limpiar(ax2, ("top", "right", "bottom"))
    ax2.tick_params(axis="y", labelcolor=cfg.TINTA_2, length=0)
    ax2.set_title("% de películas que no recupera la inversión", fontsize=10.5,
                  color=cfg.TINTA_2, loc="left", pad=8)

    musd = rent.loc[critico, "presupuesto_total_musd"]
    fuera = 100 - cifras["pct_peliculas_con_roi"]
    titular(fig,
            f"US$ {num(musd / 1000, 1)} mil millones acumulados están puestos en el tramo "
            "menos rentable del catálogo",
            f"Películas de la cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} con presupuesto y recaudación "
            f"informados · {num(rent.peliculas.sum(), 0)} películas "
            f"({num(cifras['pct_peliculas_con_roi'])}% del total de películas)", y=1.055)
    pie(fig, f"El {num(fuera)}% restante de las películas no informa presupuesto o recaudación y queda "
             "fuera de este análisis: la conclusión aplica al subconjunto con datos financieros "
             "completos. " + cfg.FUENTE_DATO, y=-0.085)
    return guardar(fig, "f5_rentabilidad_tramos.png")


# --------------------------------------------------------------------------
# F6 · El presupuesto compra visibilidad, no agrado
#      Dos magnitudes de escala distinta → se indexan a una base común (=100)
# --------------------------------------------------------------------------
def f6_presupuesto(mad):
    fin = mad[mad.roi.notna()].copy()
    fin["decil"] = pd.qcut(fin.budget, 10, labels=range(1, 11))
    g = fin.groupby("decil", observed=True).agg(
        atencion=("atencion", "median"), satisfaccion=("satisfaccion", "median"))
    idx = g / g.iloc[0] * 100
    corr = M.correlaciones(mad)

    fig, ax = plt.subplots(figsize=(ANCHO, 4.4))
    ax.axhline(100, color=cfg.EJE, lw=1.2, zorder=2)
    ax.plot(idx.index.astype(int), idx.atencion, color=cfg.SERIE_1, lw=2.4,
            marker="o", markersize=5, markeredgecolor=cfg.SUPERFICIE,
            markeredgewidth=1.5, label="Atención", zorder=4)
    ax.plot(idx.index.astype(int), idx.satisfaccion, color=cfg.SERIE_2, lw=2.4,
            marker="o", markersize=5, markeredgecolor=cfg.SUPERFICIE,
            markeredgewidth=1.5, label="Satisfacción (nota)", zorder=4)

    ax.text(10.22, idx.atencion.iloc[-1], f" Atención\n {num(idx.atencion.iloc[-1], 0)}",
            fontsize=10.5, fontweight="bold", color=cfg.SERIE_1, va="center", linespacing=1.3)
    ax.text(10.22, idx.satisfaccion.iloc[-1] + 14,
            f" Satisfacción\n {num(idx.satisfaccion.iloc[-1], 0)}",
            fontsize=10.5, fontweight="bold", color=cfg.SERIE_2, va="center", linespacing=1.3)

    ax.set_xlim(0.6, 12.1)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("Decil de presupuesto de la película (1 = más barato · 10 = más caro)")
    ax.set_ylabel("Índice, decil 1 = 100")
    ax.legend(loc="upper left", fontsize=10, labelcolor=cfg.TINTA_2)
    limpiar(ax)

    titular(fig,
            "Multiplicar el presupuesto por 10 multiplica la visibilidad, pero no mueve la nota",
            f"Películas con datos financieros completos, cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · "
            f"ρ de Spearman presupuesto–atención = {num(corr.loc['budget', 'atencion'], 2)} · "
            f"presupuesto–satisfacción = {num(corr.loc['budget', 'satisfaccion'], 2)}")
    pie(fig, "Ambas series se indexan a base 100 en el decil más barato porque miden en unidades "
             "distintas: un gráfico de doble eje inventaría una correlación que los datos no tienen. "
             + cfg.FUENTE_DATO)
    return guardar(fig, "f6_presupuesto_atencion_nota.png")


# --------------------------------------------------------------------------
# F7 · Internacionalización del catálogo
#      Tarea visual: variación en el tiempo → línea
# --------------------------------------------------------------------------
def f7_idioma(cat):
    ev = M.evolucion_idioma(cat)
    ini, fin = ev.pct_no_ingles.iloc[0], ev.pct_no_ingles.iloc[-1]

    fig, ax = plt.subplots(figsize=(ANCHO, 4.2))
    ax.plot(ev.index, ev.pct_no_ingles, color=cfg.SERIE_1, lw=2.4, zorder=3)
    ax.fill_between(ev.index, 50, ev.pct_no_ingles, color=cfg.SERIE_1, alpha=0.09, zorder=2)
    ax.axhline(50, color=cfg.EJE, lw=1.2, zorder=1)
    ax.text(2010, 50.35, "Paridad 50%", fontsize=8.5, color=cfg.TINTA_3, va="bottom")

    for x, y, dx, dy, ha, va in ((ev.index[0], ini, 0.15, 0.55, "left", "bottom"),
                                 (ev.index[-1], fin, 0.20, 0.0, "left", "center")):
        ax.scatter([x], [y], s=60, color=cfg.SERIE_1, zorder=4,
                   edgecolor=cfg.SUPERFICIE, linewidth=2)
        ax.text(x + dx, y + dy, f"{num(y)}%", fontsize=12, fontweight="bold",
                color=cfg.TINTA, ha=ha, va=va)

    ax.set_xlim(2009.1, 2025.2)
    ax.set_ylim(48, 65)
    ax.set_xticks(range(2010, 2025, 2))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Año de estreno")
    ax.set_ylabel("% de estrenos en idioma distinto del inglés")
    limpiar(ax)

    titular(fig,
            f"El catálogo se internacionalizó: el contenido no inglés pasó de {num(ini)}% a "
            f"{num(fin)}% de los estrenos",
            f"Cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · participación dentro de cada año · "
            "1.000 títulos por año y por fuente (muestra balanceada)")
    pie(fig, "Se lee la COMPOSICIÓN de cada año, no el volumen: el conjunto trae exactamente 1.000 "
             "títulos por año por diseño muestral, de modo que un gráfico de volumen sería plano por "
             "construcción y no diría nada. " + cfg.FUENTE_DATO)
    return guardar(fig, "f7_internacionalizacion.png")


# --------------------------------------------------------------------------
# F8 · Géneros dentro de cada formato (small multiples, escala x compartida)
#      Series y películas usan vocabularios de género distintos en la fuente:
#      compararlos en un solo ranking mezclaría taxonomías. Se separan.
# --------------------------------------------------------------------------
def f8_generos(mad, minimo=250, top=8):
    def ranking(formato):
        d = mad[mad.formato == formato]
        ex = d.assign(g=d.generos.str.split(", ")).explode("g")
        t = ex.groupby("g").agg(titulos=("titulo", "size"), atencion=("atencion", "median"))
        t["nota"] = ex[~ex.sin_senal].groupby("g").satisfaccion.median()
        t = t[(t.titulos >= minimo) & (t.index != "Sin clasificar")]
        return t.nlargest(top, "atencion").sort_values("atencion")

    series, peliculas = ranking("Serie"), ranking("Película")
    tope = series.atencion.max() * 1.42
    peor_serie, mejor_peli = series.atencion.min(), peliculas.atencion.max()

    fig, axes = plt.subplots(2, 1, figsize=(ANCHO, 6.4),
                             gridspec_kw={"hspace": 0.48})
    for ax, tabla, titulo, color in (
        (axes[0], series, f"SERIES — {top} géneros de mayor atención", cfg.SERIE_1),
        (axes[1], peliculas, f"PELÍCULAS — {top} géneros de mayor atención", cfg.NEUTRO),
    ):
        barras = ax.barh(tabla.index, tabla.atencion, color=color, height=0.55, zorder=3)
        for barra, (_, fila) in zip(barras, tabla.iterrows()):
            ax.text(fila.atencion + tope * 0.012, barra.get_y() + barra.get_height() / 2,
                    f"{num(fila.atencion)}", va="center", ha="left", fontsize=10,
                    fontweight="bold", color=cfg.TINTA)
            ax.text(fila.atencion + tope * 0.075, barra.get_y() + barra.get_height() / 2,
                    f"{num(fila.titulos, 0)} tít. · nota {num(fila.nota, 1)}",
                    va="center", ha="left", fontsize=8.5, color=cfg.TINTA_3)
        ax.set_xlim(0, tope)
        ax.set_title(titulo, fontsize=10, color=cfg.TINTA_2, loc="left", pad=6)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", labelsize=10, labelcolor=cfg.TINTA, length=0)
        limpiar(ax)

    axes[1].set_xlabel("Atención mediana por título — misma escala en ambos paneles")
    axes[1].axvline(peor_serie, color=cfg.CRITICO, lw=1.3, zorder=5)
    axes[1].annotate(f"Peor género de serie: {num(peor_serie)}\nNingún género de película lo alcanza",
                     xy=(peor_serie, top - 2.5), xytext=(peor_serie + tope * 0.17, top - 2.5),
                     fontsize=8.5, color=cfg.CRITICO, va="center", ha="left", linespacing=1.4,
                     arrowprops=dict(arrowstyle="-", color=cfg.CRITICO, lw=0.9))

    titular(fig,
            "Hasta el género de serie que menos atención capta más que duplica al mejor de las películas",
            f"Cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE} · géneros con al menos {minimo} apariciones "
            f"dentro de su formato · peor serie {num(peor_serie)} vs. mejor película {num(mejor_peli)}",
            y=1.03)
    pie(fig, "Series y películas usan vocabularios de género distintos en la fuente (\"Action & "
             "Adventure\" sólo existe en series; \"Action\" sólo en películas), por lo que se comparan "
             "por separado: un ranking único mezclaría dos taxonomías. Un título con varios géneros "
             "cuenta en cada uno. " + cfg.FUENTE_DATO, y=-0.05)
    return guardar(fig, "f8_generos.png")


# --------------------------------------------------------------------------
def generar_todo():
    cat = M.cargar()
    mad = cat[cat.cohorte_madura].copy()
    cifras = M.cifras_clave()
    print("Generando figuras en", cfg.DIR_IMG)
    f1_concentracion(mad)
    f2_formato(mad)
    f3_invisible(mad, cat, cifras)
    f4_cuadrantes(mad)
    f5_rentabilidad(mad, cifras)
    f6_presupuesto(mad)
    f7_idioma(cat)
    f8_generos(mad)
    print("Listo.")


if __name__ == "__main__":
    generar_todo()
