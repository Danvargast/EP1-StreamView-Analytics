"""
app.py — Dashboard interactivo StreamView Analytics (EP1 · ADY1104).

Ejecutar desde la raíz del proyecto:
    streamlit run dashboard/app.py

Arquitectura de la interfaz (decisiones de diseño justificadas):

  · Patrón de lectura Z: el mensaje principal arriba a la izquierda, la fila de
    KPIs inmediatamente debajo, el detalle explorable al final. El dato de mayor
    impacto se ve primero.
  · Una sola fila de filtros, en la barra lateral, que gobierna TODAS las vistas:
    nunca filtros dentro de una tarjeta, para que el usuario no compare
    inadvertidamente dos recortes distintos.
  · Navegación por pestañas según audiencia:
      1 · Visión ejecutiva      → Comité / CCO. Nivel de detalle bajo.
      2 · Diagnóstico de catálogo → Programación y Adquisición. Detalle medio-alto.
      3 · Rentabilidad          → Finanzas de contenido. Detalle alto.
      4 · Datos y calidad       → Equipo técnico. Detalle máximo + descarga.
  · Cada gráfico lleva título comunicacional y tooltip; ninguna cifra depende
    sólo del color (siempre hay etiqueta o tabla equivalente).
  · La cohorte 2025 viene desactivada por defecto: sus títulos aún no acumulan
    interacciones y mezclarla distorsiona cualquier comparación.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import config as cfg          # noqa: E402  (fija el tipo de texto de pandas)
import etl                    # noqa: E402
import metricas as M          # noqa: E402

st.set_page_config(page_title="StreamView Analytics · Catálogo",
                   page_icon="▮", layout="wide")

# --------------------------------------------------------------------------
# Identidad visual compartida con el informe (IE9: coherencia)
# --------------------------------------------------------------------------
PLANTILLA = go.layout.Template(layout=dict(
    paper_bgcolor=cfg.SUPERFICIE,
    plot_bgcolor=cfg.SUPERFICIE,
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif",
              size=13, color=cfg.TINTA_2),
    title=dict(font=dict(size=16, color=cfg.TINTA)),
    colorway=cfg.CATEGORICA,
    xaxis=dict(gridcolor=cfg.REJILLA, linecolor=cfg.EJE, zeroline=False,
               title=dict(font=dict(size=12))),
    yaxis=dict(gridcolor=cfg.REJILLA, linecolor=cfg.EJE, zeroline=False,
               title=dict(font=dict(size=12))),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.08, x=0),
    margin=dict(l=10, r=10, t=64, b=10),
    separators=",.",   # coma decimal, punto de miles
    hoverlabel=dict(bgcolor=cfg.SUPERFICIE, bordercolor=cfg.EJE,
                    font=dict(color=cfg.TINTA)),
))

st.markdown(f"""
<style>
  .stApp {{ background:{cfg.PLANO}; }}
  .kpi {{ background:{cfg.SUPERFICIE}; border:1px solid {cfg.REJILLA};
          border-radius:10px; padding:14px 16px; height:100%; }}
  .kpi .rotulo {{ font-size:12px; color:{cfg.TINTA_3}; text-transform:uppercase;
                  letter-spacing:.04em; }}
  .kpi .valor  {{ font-size:30px; font-weight:700; color:{cfg.TINTA};
                  line-height:1.15; margin-top:4px; }}
  .kpi .glosa  {{ font-size:11.5px; color:{cfg.TINTA_2}; margin-top:4px; }}
  .mensaje {{ background:{cfg.SUPERFICIE}; border-left:4px solid {cfg.SERIE_1};
              border-radius:6px; padding:16px 20px; margin-bottom:6px; }}
  .mensaje h3 {{ margin:0 0 6px 0; font-size:18px; color:{cfg.TINTA}; }}
  .mensaje p  {{ margin:0; font-size:14px; color:{cfg.TINTA_2}; }}
  .nota {{ font-size:11.5px; color:{cfg.TINTA_3}; }}
  table.tabla-proyecto {{ width:100%; border-collapse:collapse; font-size:13px;
        background:{cfg.SUPERFICIE}; font-variant-numeric:tabular-nums; }}
  table.tabla-proyecto th {{ text-align:left; font-weight:600; color:{cfg.TINTA_2};
        border-bottom:1.5px solid {cfg.EJE}; padding:7px 10px; white-space:nowrap;
        position:sticky; top:0; background:{cfg.SUPERFICIE}; }}
  table.tabla-proyecto td {{ color:{cfg.TINTA}; border-bottom:1px solid {cfg.REJILLA};
        padding:6px 10px; }}
  table.tabla-proyecto tbody tr:hover td {{ background:#f1f5fb; }}
</style>
""", unsafe_allow_html=True)


def es(valor, dec=1):
    """Formato numérico chileno."""
    return f"{valor:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def tarjeta(rotulo, valor, glosa):
    st.markdown(f"""<div class="kpi"><div class="rotulo">{rotulo}</div>
        <div class="valor">{valor}</div><div class="glosa">{glosa}</div></div>""",
                unsafe_allow_html=True)


def tabla(df, indice=True, dec=2, alto=None):
    """Renderiza un DataFrame como tabla HTML con la identidad del proyecto.

    Se evita `st.dataframe` de forma deliberada: su conversión interna a Apache
    Arrow provoca una falla de segmentación al re-ejecutar el script con la
    combinación pandas 3.0 + pyarrow 25 de este entorno, es decir, cada vez que
    el usuario mueve un filtro. La tabla HTML entrega la misma información,
    respeta la paleta del proyecto y no depende de Arrow.
    """
    d = df.copy().rename_axis(None)
    for col in d.columns:
        if pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else es(v, dec))
        elif pd.api.types.is_integer_dtype(d[col]):
            d[col] = d[col].map(lambda v: es(v, 0))
    estilo_alto = f"max-height:{alto}px;overflow:auto;" if alto else ""
    html = d.to_html(index=indice, border=0, escape=False,
                     classes="tabla-proyecto", justify="left")
    st.markdown(f'<div style="{estilo_alto}">{html}</div>', unsafe_allow_html=True)


def cargar_catalogo():
    return M.cargar()


cat = cargar_catalogo()

# --------------------------------------------------------------------------
# Filtros: una sola barra que gobierna todas las pestañas
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Filtros")
    st.caption("Todos los paneles responden a esta selección.")

    incluir_2025 = st.toggle(
        "Incluir cohorte 2025", value=False,
        help=f"El {es(cfg.PCT_SIN_VOTOS_2025)}% de los títulos de 2025 aún no registra "
             "interacciones. Incluirla distorsiona las comparaciones.")
    tope = cfg.ANIO_MAX if incluir_2025 else cfg.ANIO_CIERRE

    anios = st.slider("Año de estreno", cfg.ANIO_MIN, tope, (cfg.ANIO_MIN, tope))

    formatos = st.multiselect("Formato", ["Película", "Serie"],
                              default=["Película", "Serie"])

    bloques = st.multiselect("Idioma", ["Inglés", "No inglés"],
                             default=["Inglés", "No inglés"])

    top_idiomas = cat.idioma_original.value_counts().head(15).index.tolist()
    idiomas = st.multiselect("Idioma original (15 más frecuentes)", top_idiomas,
                             default=[],
                             help="Vacío = todos los idiomas.")

    generos_disp = sorted({g.strip() for fila in cat.generos.dropna()
                           for g in fila.split(",")} - {"Sin clasificar"})
    generos = st.multiselect("Género", generos_disp, default=[],
                             help="Vacío = todos los géneros. Un título con varios "
                                  "géneros aparece si coincide con cualquiera.")

    solo_senal = st.checkbox("Sólo títulos con interacciones", value=False,
                             help="Excluye el catálogo invisible del recuento.")

    st.divider()
    st.caption("StreamView Analytics · EP1 ADY1104\n\nFelipe Ángel · Daniel Vargas")

# Aplicación de filtros
f = cat[(cat.anio.between(*anios)) & (cat.formato.isin(formatos))
        & (cat.bloque_idioma.isin(bloques))]
if idiomas:
    f = f[f.idioma_original.isin(idiomas)]
if generos:
    f = f[f.generos.apply(lambda s: any(g in [x.strip() for x in s.split(",")]
                                        for g in generos))]
if solo_senal:
    f = f[~f.sin_senal]

st.title("StreamView Analytics · Rendimiento del catálogo")
st.caption(f"Selección activa: {es(len(f), 0)} de {es(len(cat), 0)} títulos · "
           f"estrenos {anios[0]}–{anios[1]} · {', '.join(formatos) or 'sin formato'}")

if f.empty:
    st.warning("La combinación de filtros no devuelve títulos. Amplíe la selección.")
    st.stop()

# --------------------------------------------------------------------------
# Fila de KPIs (siempre visible, encabeza la lectura)
# --------------------------------------------------------------------------
k = M.kpis(f)
cols = st.columns(5, gap="small")
with cols[0]:
    tarjeta("Títulos en la selección", es(k["titulos"], 0),
            f"{es(k['titulos'] / len(cat) * 100)}% del catálogo")
with cols[1]:
    tarjeta("Atención en el top 10%", f"{es(k['atencion_top10'])}%",
            f"Gini {es(k['gini_atencion'], 2)} · 0 = reparto igualitario")
with cols[2]:
    tarjeta("Catálogo invisible", f"{es(k['catalogo_invisible_pct'])}%",
            f"{es(k['catalogo_invisible_n'], 0)} títulos sin interacciones")
with cols[3]:
    tarjeta("Satisfacción mediana", es(k["satisfaccion_mediana"], 2),
            f"nota 0–10 · base {es(k['satisfaccion_n'], 0)} títulos")
with cols[4]:
    tarjeta("Atención mediana", es(k["atencion_mediana"], 1),
            "índice de popularidad por título")

st.write("")

t1, t2, t3, t4 = st.tabs(["1 · Visión ejecutiva", "2 · Diagnóstico de catálogo",
                          "3 · Rentabilidad", "4 · Datos y calidad"])

# --------------------------------------------------------------------------
# Pestaña 1 · Visión ejecutiva (audiencia: Comité / CCO)
# --------------------------------------------------------------------------
with t1:
    st.markdown(f"""<div class="mensaje">
      <h3>La decisión no es cuánto contenido comprar, sino de qué tipo</h3>
      <p>Las series captan varias veces más atención por título que las películas y con mejor
      nota, mientras el tramo de películas de 1 a 10 millones de dólares concentra miles de
      millones en el peor retorno del catálogo. En la selección activa, el
      {es(k['atencion_top10'])}% de la atención se concentra en el 10% de los títulos.</p>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.15, 1], gap="large")

    with c1:
        curva = M.curva_concentracion(f)
        muestra = curva.iloc[:: max(1, len(curva) // 600)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines",
                                 line=dict(color=cfg.NEUTRO, width=2),
                                 name="Reparto igualitario",
                                 hovertemplate="Reparto igualitario<extra></extra>"))
        fig.add_trace(go.Scatter(x=muestra.pct_titulos, y=muestra.pct_atencion,
                                 mode="lines", fill="tonexty",
                                 fillcolor="rgba(42,120,214,0.10)",
                                 line=dict(color=cfg.SERIE_1, width=3),
                                 name="Catálogo real",
                                 hovertemplate="El %{x:.0f}% de los títulos concentra "
                                               "el %{y:.1f}% de la atención<extra></extra>"))
        fig.update_layout(template=PLANTILLA, height=380,
                          title="La atención se concentra en una fracción del catálogo",
                          xaxis_title="% acumulado de títulos (de mayor a menor atención)",
                          yaxis_title="% acumulado de atención",
                          xaxis=dict(ticksuffix="%"), yaxis=dict(ticksuffix="%"))
        st.plotly_chart(fig, width="stretch")

    with c2:
        seg = M.por_segmento(f).reset_index()
        fig = px.bar(seg.sort_values("atencion_mediana"), x="atencion_mediana",
                     y="segmento", orientation="h", text="atencion_mediana",
                     custom_data=["titulos", "satisfaccion_mediana", "invisible_pct"])
        fig.update_traces(marker_color=cfg.SERIE_1, texttemplate="%{text:.1f}",
                          textposition="outside",
                          hovertemplate="<b>%{y}</b><br>Atención mediana: %{x:.1f}"
                                        "<br>Títulos: %{customdata[0]:,.0f}"
                                        "<br>Nota mediana: %{customdata[1]:.2f}"
                                        "<br>Catálogo invisible: %{customdata[2]:.1f}%"
                                        "<extra></extra>")
        fig.update_layout(template=PLANTILLA, height=380, showlegend=False,
                          title="Atención mediana por segmento de decisión",
                          xaxis_title="Atención mediana por título", yaxis_title="",
                          xaxis=dict(range=[0, seg.atencion_mediana.max() * 1.22]))
        st.plotly_chart(fig, width="stretch")

    st.markdown('<p class="nota">Se usa la mediana y no el promedio: la distribución de '
                'atención tiene cola larga y unos pocos estrenos masivos desplazarían el '
                'promedio. El segmento combina formato e idioma porque es la unidad sobre '
                'la que se decide el presupuesto de contenido.</p>',
                unsafe_allow_html=True)

    tabla(M.por_segmento(f).rename(columns={
        "titulos": "Títulos", "atencion_mediana": "Atención mediana",
        "invisible_pct": "Catálogo invisible (%)",
        "satisfaccion_mediana": "Nota mediana"}))

# --------------------------------------------------------------------------
# Pestaña 2 · Diagnóstico (audiencia: Programación y Adquisición)
# --------------------------------------------------------------------------
with t2:
    puntos, u_at, u_sa = M.cuadrantes(f)
    if puntos.empty:
        st.info("La selección no contiene títulos con interacciones registradas.")
    else:
        resumen = M.resumen_cuadrantes(f)
        st.markdown(
            f"""<div class="mensaje"><h3>Cuatro decisiones distintas sobre un mismo catálogo</h3>
            <p>Los umbrales son las medianas de la selección activa: atención
            {es(u_at)} y nota {es(u_sa, 2)}. Cambian con los filtros, de modo que el
            diagnóstico siempre es relativo al recorte que el usuario está mirando.</p>
            </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns([1.5, 1], gap="large")
        with c1:
            muestra = puntos.sample(n=min(4000, len(puntos)), random_state=7)
            fig = px.scatter(muestra, x="atencion", y="satisfaccion", log_x=True,
                             color="cuadrante",
                             category_orders={"cuadrante": M.CUADRANTES},
                             color_discrete_map={
                                 "Motores": cfg.SERIE_1, "Joyas ocultas": cfg.SERIE_2,
                                 "Ruido": cfg.NEUTRO, "Rezagados": cfg.TINTA_3},
                             hover_data={"titulo": True, "formato": True,
                                         "anio": True, "idioma_original": True,
                                         "atencion": ":.1f", "satisfaccion": ":.2f"},
                             opacity=0.55)
            fig.update_traces(marker=dict(size=6, line=dict(width=0)))
            fig.add_vline(x=u_at, line_color=cfg.EJE, line_width=1.5)
            fig.add_hline(y=u_sa, line_color=cfg.EJE, line_width=1.5)
            fig.update_layout(template=PLANTILLA, height=470,
                              title="Atención frente a satisfacción, título por título",
                              xaxis_title="Atención (escala logarítmica)",
                              yaxis_title="Satisfacción (nota 0–10)",
                              legend_title="")
            st.plotly_chart(fig, width="stretch")
            st.markdown('<p class="nota">Se grafica una muestra aleatoria de hasta 4.000 '
                        'puntos para evitar el solapamiento; la tabla de la derecha usa el '
                        'universo completo de la selección. Pase el cursor sobre un punto '
                        'para ver el título.</p>', unsafe_allow_html=True)
        with c2:
            tabla(resumen.rename(columns={
                "titulos": "Títulos", "atencion_mediana": "Atención",
                "satisfaccion_mediana": "Nota", "pct_series": "% series",
                "pct_no_ingles": "% no inglés", "pct_catalogo": "% del total"}), dec=1)
            st.markdown(
                f"""<p class="nota"><b>Motores</b>: renovar y escalar.<br>
                <b>Joyas ocultas</b>: inventario ya pagado, activar en recomendación
                y CRM antes de comprar contenido nuevo.<br>
                <b>Ruido</b>: atraen pero decepcionan, revisar expectativa y ficha.<br>
                <b>Rezagados</b>: candidatos a poda o renegociación.</p>""",
                unsafe_allow_html=True)

        st.divider()
        c3, c4 = st.columns(2, gap="large")
        with c3:
            inv = (f.groupby(["anio", "formato"]).sin_senal.mean() * 100).reset_index()
            fig = px.line(inv, x="anio", y="sin_senal", color="formato", markers=True,
                          color_discrete_map={"Serie": cfg.SERIE_1,
                                              "Película": cfg.SERIE_2})
            fig.update_traces(line_width=2.5, marker_size=7,
                              hovertemplate="%{fullData.name} · %{x}<br>"
                                            "Sin interacciones: %{y:.1f}%<extra></extra>")
            fig.update_layout(template=PLANTILLA, height=360, legend_title="",
                              title="Catálogo invisible por año y formato",
                              xaxis_title="Año de estreno",
                              yaxis_title="% de títulos sin interacciones",
                              yaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig, width="stretch")
        with c4:
            idi = (f.groupby("idioma_original")
                   .agg(titulos=("titulo", "size"), atencion=("atencion", "median"),
                        invisible=("sin_senal", lambda s: s.mean() * 100))
                   .query("titulos >= 100").nlargest(12, "titulos").reset_index())
            fig = px.scatter(idi, x="invisible", y="atencion", size="titulos",
                             text="idioma_original", size_max=42,
                             custom_data=["titulos"])
            fig.update_traces(marker_color=cfg.SERIE_1, marker_line_width=0,
                              textposition="top center",
                              textfont=dict(size=11, color=cfg.TINTA_2),
                              hovertemplate="<b>%{text}</b><br>Atención mediana: %{y:.1f}"
                                            "<br>Catálogo invisible: %{x:.1f}%"
                                            "<br>Títulos: %{customdata[0]:,.0f}<extra></extra>")
            fig.update_layout(template=PLANTILLA, height=360,
                              title="Riesgo y rendimiento por idioma (≥100 títulos)",
                              xaxis_title="% de títulos sin interacciones (riesgo)",
                              yaxis_title="Atención mediana (rendimiento)",
                              xaxis=dict(ticksuffix="%"))
            st.plotly_chart(fig, width="stretch")
            st.markdown('<p class="nota">El tamaño de la burbuja es el número de títulos. '
                        'Arriba a la izquierda: alto rendimiento y bajo riesgo — los '
                        'idiomas donde conviene concentrar la inversión.</p>',
                        unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Pestaña 3 · Rentabilidad (audiencia: Finanzas de contenido)
# --------------------------------------------------------------------------
with t3:
    fin = f[f.roi.notna()]
    if fin.empty:
        st.info("La selección no contiene películas con presupuesto y recaudación "
                "informados. Incluya el formato Película para ver este análisis.")
    else:
        cobertura = len(fin) / max(1, (f.formato == "Película").sum()) * 100
        st.markdown(
            f"""<div class="mensaje"><h3>Más presupuesto compra visibilidad, no mejores notas</h3>
            <p>Análisis sobre {es(len(fin), 0)} películas con presupuesto y recaudación
            informados ({es(cobertura)}% de las películas de la selección). El resto no
            informa datos financieros y queda fuera: las conclusiones de esta pestaña
            aplican sólo a ese subconjunto.</p></div>""", unsafe_allow_html=True)

        rent = M.rentabilidad(f).reset_index()
        c1, c2 = st.columns(2, gap="large")
        with c1:
            fig = px.bar(rent, x="tramo_presupuesto", y="roi_mediano",
                         text="roi_mediano", custom_data=["peliculas",
                                                          "pct_bajo_equilibrio"])
            fig.update_traces(
                marker_color=[cfg.CRITICO if t == "1 – 10 M" else cfg.SERIE_1
                              for t in rent.tramo_presupuesto],
                texttemplate="%{text:.2f}", textposition="outside",
                hovertemplate="<b>%{x}</b><br>ROI mediano: %{y:.2f}"
                              "<br>Películas: %{customdata[0]:,.0f}"
                              "<br>Bajo el equilibrio: %{customdata[1]:.1f}%<extra></extra>")
            fig.add_hline(y=1, line_color=cfg.TINTA_2, line_width=1.6,
                          annotation_text="Punto de equilibrio (ROI = 1)",
                          annotation_position="top left",
                          annotation_font=dict(size=11, color=cfg.TINTA_2))
            fig.update_layout(template=PLANTILLA, height=380, showlegend=False,
                              title="ROI mediano por tramo de presupuesto",
                              xaxis_title="Tramo de presupuesto (USD)",
                              yaxis_title="Recaudación / presupuesto",
                              yaxis=dict(range=[0, rent.roi_mediano.max() * 1.18]))
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = px.bar(rent, x="pct_bajo_equilibrio", y="tramo_presupuesto",
                         orientation="h", text="pct_bajo_equilibrio")
            fig.update_traces(
                marker_color=[cfg.CRITICO if t == "1 – 10 M" else cfg.NEUTRO
                              for t in rent.tramo_presupuesto],
                texttemplate="%{text:.1f}%", textposition="outside",
                hovertemplate="<b>%{y}</b><br>No recupera la inversión: "
                              "%{x:.1f}%<extra></extra>")
            fig.update_layout(template=PLANTILLA, height=380, showlegend=False,
                              title="% de películas que no recupera la inversión",
                              xaxis_title="", yaxis_title="",
                              xaxis=dict(ticksuffix="%",
                                         range=[0, rent.pct_bajo_equilibrio.max() * 1.25]))
            st.plotly_chart(fig, width="stretch")

        st.divider()
        corr = M.correlaciones(f)
        c3, c4 = st.columns([1.4, 1], gap="large")
        with c3:
            muestra = fin.sample(n=min(2500, len(fin)), random_state=3)
            fig = px.scatter(muestra, x="budget", y="revenue", log_x=True, log_y=True,
                             color="satisfaccion", color_continuous_scale=cfg.SECUENCIAL,
                             hover_data={"titulo": True, "anio": True, "roi": ":.2f"},
                             opacity=0.6)
            fig.update_traces(marker=dict(size=6, line=dict(width=0)))
            tope = [fin.budget.min(), fin.budget.max()]
            fig.add_trace(go.Scatter(x=tope, y=tope, mode="lines",
                                     line=dict(color=cfg.TINTA_2, width=1.6),
                                     name="Punto de equilibrio",
                                     hovertemplate="Punto de equilibrio<extra></extra>"))
            fig.update_layout(template=PLANTILLA, height=430,
                              title="Presupuesto frente a recaudación (bajo la línea = pérdida)",
                              xaxis_title="Presupuesto (USD, escala log)",
                              yaxis_title="Recaudación (USD, escala log)",
                              coloraxis_colorbar_title="Nota")
            st.plotly_chart(fig, width="stretch")
        with c4:
            st.markdown("**Correlación de Spearman**")
            etiquetas = {"budget": "Presupuesto", "revenue": "Recaudación",
                         "atencion": "Atención", "interacciones": "Interacciones",
                         "satisfaccion": "Satisfacción"}
            tabla(corr.rename(index=etiquetas, columns=etiquetas))
            st.markdown(
                f"""<p class="nota">El presupuesto se asocia con la atención
                (ρ = {es(corr.loc['budget', 'atencion'], 2)}) pero prácticamente no con la
                satisfacción (ρ = {es(corr.loc['budget', 'satisfaccion'], 2)}).
                Se usa Spearman y no Pearson porque las distribuciones son muy
                asimétricas y sólo interesa la relación monótona, no la lineal.<br><br>
                Correlación no implica causalidad: un presupuesto mayor viene acompañado
                de más marketing y más salas, que son parte del efecto observado.</p>""",
                unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Pestaña 4 · Datos y calidad (audiencia: equipo técnico)
# --------------------------------------------------------------------------
with t4:
    st.markdown("""<div class="mensaje">
      <h3>Trazabilidad: de dónde sale cada cifra</h3>
      <p>Toda métrica del tablero se calcula en <code>src/metricas.py</code> sobre el
      catálogo integrado por <code>src/etl.py</code>. Aquí están los datos filtrados,
      el control de calidad y el diccionario de variables.</p>
    </div>""", unsafe_allow_html=True)

    columnas = ["id_titulo", "titulo", "formato", "anio", "pais_principal",
                "idioma_original", "genero_principal", "atencion", "interacciones",
                "satisfaccion", "sin_senal", "budget", "revenue", "roi"]
    orden = st.selectbox("Ordenar por", ["atencion", "interacciones", "satisfaccion",
                                         "roi", "budget", "anio"], index=0)
    n = st.slider("Filas a mostrar", 20, 500, 100, step=20)
    vista = f[columnas].sort_values(orden, ascending=False, na_position="last").head(n)
    tabla(vista.rename(columns={
        "id_titulo": "ID", "titulo": "Título", "formato": "Formato", "anio": "Año",
        "pais_principal": "País", "idioma_original": "Idioma",
        "genero_principal": "Género", "atencion": "Atención",
        "interacciones": "Interacciones", "satisfaccion": "Nota",
        "sin_senal": "Sin señal", "budget": "Presupuesto", "revenue": "Recaudación",
        "roi": "ROI"}), indice=False, alto=430)

    st.download_button(
        "Descargar la selección completa en CSV",
        data=f[columnas].to_csv(index=False).encode("utf-8"),
        file_name="streamview_seleccion.csv", mime="text/csv")

    st.divider()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Control de calidad de la selección**")
        tabla(etl.auditoria(f), indice=False)
    with c2:
        st.markdown("**Diccionario de variables**")
        tabla(pd.read_csv(cfg.DIR_PROC / "diccionario_datos.csv"),
              indice=False, alto=330)

    st.markdown("""<p class="nota"><b>Limitaciones declaradas.</b>
    (1) El conjunto trae exactamente 1.000 títulos por año y por fuente: es una muestra
    balanceada, no el catálogo completo, por lo que no se puede leer volumen en el tiempo.
    (2) <code>date_added</code> cae siempre dentro del año de estreno, así que no
    representa la fecha real de alta en catálogo. (3) No existen datos de reproducción,
    horas vistas ni churn: "atención" es un proxy externo de popularidad, no telemetría
    propia. (4) El 0 en presupuesto y recaudación significa "no informado" y fue
    convertido a nulo.</p>""", unsafe_allow_html=True)
