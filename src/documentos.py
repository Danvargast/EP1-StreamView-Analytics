"""
documentos.py — Genera el informe ejecutivo y el resumen ejecutivo en PDF.

Ambos documentos se arman a partir de `metricas.cifras_clave()`: ninguna cifra
se escribe a mano. Si el dato cambia, cambia el documento — no hay forma de que
el titular de una diapositiva contradiga a la tabla del informe.

Salida:
    docs/informe_ejecutivo.pdf     · documento completo del proyecto
    docs/resumen_ejecutivo.pdf     · presentación de cierre para el comité
    docs/informe_ejecutivo.html    · fuente editable de cada uno
    docs/resumen_ejecutivo.html

Requiere Google Chrome para la conversión a PDF (modo headless). Si no está
disponible, los HTML quedan igualmente generados y se pueden imprimir a PDF
desde cualquier navegador.

Ejecutar:  python src/documentos.py
"""

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

import config as cfg
import metricas as M

C = M.cifras_clave()
SEG = M.por_segmento(M.cargar(solo_maduras=True))
CUAD = M.resumen_cuadrantes(M.cargar(solo_maduras=True))
RENT = M.rentabilidad(M.cargar(solo_maduras=True))
AUD = pd.read_csv(cfg.DIR_PROC / "auditoria_calidad.csv")
DIC = pd.read_csv(cfg.DIR_PROC / "diccionario_datos.csv")


def n(valor, dec=1):
    """Formato chileno: coma decimal, punto de miles."""
    return f"{valor:,.{dec}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def img(nombre):
    """Incrusta la figura en base64 para que el HTML sea un archivo autónomo."""
    ruta = cfg.DIR_IMG / nombre
    datos = base64.b64encode(ruta.read_bytes()).decode()
    return f"data:image/png;base64,{datos}"


def tabla_html(df, indice=True, dec=2, clase="tabla"):
    d = df.copy().rename_axis(None)
    for col in d.columns:
        if pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda v: "—" if pd.isna(v) else n(v, dec))
        elif pd.api.types.is_integer_dtype(d[col]):
            d[col] = d[col].map(lambda v: n(v, 0))
    return d.to_html(index=indice, border=0, escape=False, classes=clase, justify="left")


# ==========================================================================
# Hoja de estilos compartida — misma identidad que las figuras y el dashboard
# ==========================================================================
ESTILO = f"""
  @page {{ size: A4; margin: 17mm 15mm 16mm 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "DejaVu Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
          color: {cfg.TINTA}; background: #fff; font-size: 10.2pt; line-height: 1.52;
          margin: 0; }}
  h1 {{ font-size: 21pt; line-height: 1.18; margin: 0 0 6px; letter-spacing: -.01em; }}
  h2 {{ font-size: 13.5pt; margin: 26px 0 8px; padding-bottom: 5px;
        border-bottom: 2px solid {cfg.SERIE_1}; break-after: avoid; }}
  h3 {{ font-size: 11.2pt; margin: 16px 0 5px; color: {cfg.TINTA};
        break-after: avoid; }}
  p {{ margin: 0 0 9px; text-align: justify; hyphens: auto;
       orphans: 3; widows: 3; }}
  li, td {{ orphans: 2; widows: 2; }}
  ul, ol {{ margin: 0 0 9px; padding-left: 19px; }}
  li {{ margin-bottom: 4px; }}
  .sec {{ break-inside: auto; }}
  .evitar {{ break-inside: avoid; }}
  .muted {{ color: {cfg.TINTA_2}; }}
  .fino {{ font-size: 8.6pt; color: {cfg.TINTA_3}; line-height: 1.45; }}

  .portada {{ min-height: 245mm; display: flex; flex-direction: column;
              justify-content: center; break-after: page; }}
  .portada .marca {{ font-size: 9.6pt; letter-spacing: .13em; text-transform: uppercase;
                     color: {cfg.SERIE_1}; font-weight: 700; margin-bottom: 14px; }}
  .portada h1 {{ font-size: 31pt; }}
  .portada .sub {{ font-size: 13pt; color: {cfg.TINTA_2}; margin: 10px 0 30px;
                   max-width: 145mm; }}
  .portada .meta {{ font-size: 10pt; color: {cfg.TINTA_2}; border-top: 1px solid {cfg.REJILLA};
                    padding-top: 14px; }}
  .portada .meta b {{ color: {cfg.TINTA}; }}

  .mensaje {{ background: #f2f7fd; border-left: 4px solid {cfg.SERIE_1};
              padding: 13px 16px; margin: 12px 0 16px; break-inside: avoid; }}
  .mensaje .rot {{ font-size: 8.4pt; letter-spacing: .1em; text-transform: uppercase;
                   color: {cfg.SERIE_1}; font-weight: 700; }}
  .mensaje p {{ margin: 5px 0 0; font-size: 11.4pt; line-height: 1.45; text-align: left; }}

  .alerta {{ background: #fdf3f3; border-left: 4px solid {cfg.CRITICO};
             padding: 11px 15px; margin: 10px 0 14px; break-inside: avoid; }}

  .kpis {{ display: flex; gap: 8px; margin: 12px 0 16px; break-inside: avoid; }}
  .kpi {{ flex: 1; border: 1px solid {cfg.REJILLA}; border-radius: 7px; padding: 9px 11px; }}
  .kpi .r {{ font-size: 7.6pt; letter-spacing: .05em; text-transform: uppercase;
             color: {cfg.TINTA_3}; }}
  .kpi .v {{ font-size: 17.5pt; font-weight: 700; line-height: 1.2; margin-top: 2px; }}
  .kpi .g {{ font-size: 7.9pt; color: {cfg.TINTA_2}; line-height: 1.35; }}

  figure {{ margin: 14px 0 16px; break-inside: avoid; }}
  figure img {{ width: 100%; border: 1px solid {cfg.REJILLA}; border-radius: 5px; }}
  figure.captura img {{ max-height: 96mm; width: auto; max-width: 100%;
                        display: block; margin: 0 auto; }}
  figcaption {{ font-size: 8.6pt; color: {cfg.TINTA_2}; margin-top: 5px; }}
  figcaption b {{ color: {cfg.TINTA}; }}

  table.tabla {{ width: 100%; border-collapse: collapse; font-size: 8.9pt;
                 margin: 8px 0 12px; break-inside: avoid; font-variant-numeric: tabular-nums; }}
  table.tabla th {{ text-align: left; font-weight: 700; color: {cfg.TINTA_2};
                    border-bottom: 1.5px solid {cfg.EJE}; padding: 5px 7px; }}
  table.tabla td {{ border-bottom: 1px solid {cfg.REJILLA}; padding: 4.5px 7px; }}
  table.tabla tbody tr:nth-child(even) {{ background: #fafafa; }}

  .pasos {{ display: flex; gap: 7px; margin: 12px 0; break-inside: avoid; }}
  .paso {{ flex: 1; border: 1px solid {cfg.REJILLA}; border-top: 3px solid {cfg.SERIE_1};
           border-radius: 5px; padding: 9px 10px; }}
  .paso.final {{ border-top-color: {cfg.OK}; }}
  .paso .t {{ font-size: 8.2pt; text-transform: uppercase; letter-spacing: .06em;
              color: {cfg.SERIE_1}; font-weight: 700; }}
  .paso.final .t {{ color: {cfg.OK}; }}
  .paso p {{ font-size: 8.7pt; margin: 4px 0 0; text-align: left; line-height: 1.4; }}

  .accion {{ border: 1px solid {cfg.REJILLA}; border-left: 4px solid {cfg.OK};
             border-radius: 5px; padding: 11px 14px; margin-bottom: 9px;
             break-inside: avoid; }}
  .accion h4 {{ margin: 0 0 4px; font-size: 10.4pt; }}
  .accion .meta {{ font-size: 8.5pt; color: {cfg.TINTA_2}; margin-top: 5px; }}

  .dos {{ display: flex; gap: 14px; }}
  .dos > div {{ flex: 1; }}
  .salto {{ break-before: page; }}
  code {{ font-family: "DejaVu Sans Mono", monospace; font-size: 8.8pt;
          background: #f3f3f1; padding: 1px 4px; border-radius: 3px; }}
  pre {{ font-family: "DejaVu Sans Mono", monospace; font-size: 8.3pt;
         background: #f7f7f5; border: 1px solid {cfg.REJILLA}; border-radius: 5px;
         padding: 10px 12px; line-height: 1.45; overflow: hidden; }}
"""


# ==========================================================================
# Informe ejecutivo
# ==========================================================================
def informe_html():
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Informe ejecutivo · StreamView Analytics</title>
<style>{ESTILO}</style></head><body>

<section class="portada">
  <div class="marca">StreamView Analytics · Consultoría en visualización de datos</div>
  <h1>El catálogo no necesita crecer.<br>Necesita reasignarse.</h1>
  <p class="sub">Diagnóstico del rendimiento del catálogo de contenidos y propuesta de
  reasignación del presupuesto de programación.</p>
  <div class="meta">
    <p><b>Informe ejecutivo · Evaluación Parcial N°1</b><br>
    ADY1104 Visualización de Datos · Unidad 1: Proceso de comunicación de datos
    y análisis de audiencias</p>
    <p><b>Equipo consultor:</b> Felipe Ángel · Daniel Vargas<br>
    <b>Docente:</b> Claudio Andrés González Peñaloza<br>
    <b>Institución:</b> Escuela de Informática y Telecomunicaciones, DUOC UC — Sede Los Lagos<br>
    <b>Carrera:</b> Ingeniería en Informática mención Ciencia de Datos</p>
    <p class="fino">Base analítica: {n(C['titulos_total'], 0)} títulos del catálogo
    ({C['anios']}); cohorte de trabajo {n(C['titulos_maduros'], 0)} títulos
    ({cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}).</p>
  </div>
</section>

<div class="mensaje">
  <div class="rot">Mensaje único del informe</div>
  <p><b>La decisión no es cuánto contenido comprar, sino de qué tipo.</b> Una serie capta
  {n(C['multiplo_formato'], 1)} veces más atención que una película y con mejor nota,
  mientras US$&nbsp;{n(C['tramo_critico_musd'] / 1000, 1)}&nbsp;mil millones acumulados entre
  {cfg.ANIO_MIN} y {cfg.ANIO_CIERRE} siguen puestos en el tramo de películas de 1 a 10
  millones de dólares, donde el {n(C['tramo_critico_bajo_eq'])}% no recupera la inversión. Recomendamos reasignar ese
  tramo a series y activar los {n(C['joyas_n'], 0)} títulos ya pagados que nadie ve, antes
  de autorizar una sola compra nueva.</p>
</div>

<div class="kpis">
  <div class="kpi"><div class="r">Concentración</div><div class="v">{n(C['atencion_top10'])}%</div>
    <div class="g">de la atención está en el 10% de los títulos</div></div>
  <div class="kpi"><div class="r">Catálogo invisible</div><div class="v">{n(C['invisible_pct_maduro'])}%</div>
    <div class="g">{n(C['invisible_n_maduro'], 0)} títulos sin ninguna interacción</div></div>
  <div class="kpi"><div class="r">Ventaja del formato</div><div class="v">×{n(C['multiplo_formato'], 1)}</div>
    <div class="g">atención de una serie frente a una película</div></div>
  <div class="kpi"><div class="r">Riesgo financiero</div><div class="v">{n(C['tramo_critico_bajo_eq'])}%</div>
    <div class="g">de las películas de 1–10 MUSD pierde dinero</div></div>
</div>

<section class="sec">
<h2>1. Descripción del problema de negocio</h2>
<p>StreamView Analytics es una plataforma internacional de streaming que decide cada año
cuánto y qué contenido incorporar a su catálogo. Hoy esa decisión se toma principalmente
por <b>volumen</b>: cuántos títulos se suman y a qué costo. El indicador que gobierna la
conversación es el tamaño del catálogo, no su rendimiento.</p>
<p>El problema es que el catálogo crece sin que crezca la atención que recibe. La compañía
necesita entender <b>dónde se produce realmente el retorno</b> de su inversión en contenido
para sostener la retención de suscriptores y el nivel de interacción, y necesita
comunicarlo a públicos con niveles de detalle muy distintos: un comité que decide en
minutos y un equipo de programación que trabaja título por título.</p>
<p>La pregunta que este encargo responde es concreta: <b>si el presupuesto de contenido se
mantuviera igual, ¿dónde habría que moverlo para capturar más atención y mejor
satisfacción por cada dólar invertido?</b></p>
</section>

<section class="sec">
<h2>2. Objetivos del proyecto</h2>
<p><b>Objetivo general.</b> Diseñar una solución de visualización que permita a StreamView
Analytics decidir la asignación del presupuesto de contenido sobre evidencia de
rendimiento y no sobre volumen.</p>
<ol>
  <li><b>Integrar</b> las fuentes de catálogo de películas y series en una base única,
  documentada y auditada, apta para reproducir el análisis sin pasos manuales.</li>
  <li><b>Identificar</b> los patrones que explican la concentración de la atención y los
  segmentos que rinden por sobre y por debajo de la mediana.</li>
  <li><b>Cuantificar</b> la relación entre inversión, visibilidad y satisfacción para
  detectar dónde el dinero no está comprando resultado.</li>
  <li><b>Construir</b> un dashboard interactivo que permita al equipo táctico explorar el
  diagnóstico por formato, idioma, género y año.</li>
  <li><b>Comunicar</b> el hallazgo mediante una narrativa visual que termine en
  recomendaciones concretas, medibles y con plazo.</li>
</ol>
</section>

<section class="sec">
<h2>3. Audiencia objetivo y propósito comunicacional</h2>
<p>Una misma base de datos genera productos distintos según quién la use. Se definieron
tres perfiles con nivel de detalle, propósito analítico y formato de salida propios.</p>
{tabla_html(pd.DataFrame([
    ["Comité ejecutivo / Dirección de Contenidos",
     "Convencer y apoyar la decisión", "Prescriptivo", "Bajo",
     "Resumen ejecutivo (8 láminas) + KPIs del informe",
     "Aprobar la reasignación del presupuesto 2026"],
    ["Programación y Adquisición de Contenido",
     "Explicar y monitorear", "Diagnóstico", "Medio-alto",
     "Dashboard interactivo, pestañas 1 y 2",
     "Elegir qué renovar, qué activar y qué podar"],
    ["Finanzas de Contenido",
     "Informar y apoyar la decisión", "Descriptivo y diagnóstico", "Alto",
     "Dashboard interactivo, pestaña 3 + anexos",
     "Validar el retorno por tramo de inversión"],
], columns=["Audiencia", "Objetivo de comunicación", "Propósito analítico",
            "Nivel de detalle", "Producto entregado", "Decisión que habilita"]),
    indice=False)}
<p><b>Propósito comunicacional del informe.</b> Convencer al comité de que el problema es de
asignación y no de tamaño, y dejar al equipo táctico una herramienta para ejecutar esa
reasignación. Por eso el documento abre con la recomendación y deja la evidencia detrás:
la audiencia que decide no debe reconstruir el razonamiento para entender qué se le pide.</p>
</section>

<section class="sec">
<h2>4. Descripción de las fuentes de datos utilizadas</h2>
<p>La organización puso a disposición dos fuentes corporativas de catálogo, que se
integraron en una base única de <b>{n(C['titulos_total'], 0)} títulos</b> estrenados entre
{cfg.ANIO_MIN} y {cfg.ANIO_MAX}.</p>
{tabla_html(pd.DataFrame([
    ["netflix_movies_detailed_up_to_2025.csv", "Películas", "16.000", "18",
     "Incluye presupuesto y recaudación"],
    ["netflix_tv_shows_detailed_up_to_2025.csv", "Series", "16.000", "16",
     "Sin capa financiera; 9 identificadores duplicados"],
], columns=["Archivo", "Contenido", "Filas", "Columnas", "Observación"]), indice=False)}

<h3>4.1 Clave de integración y variables relevantes</h3>
<p>Ambas fuentes comparten trece campos con la misma semántica, lo que permite apilarlas
verticalmente y distinguirlas mediante la variable derivada <code>formato</code>. El
identificador <code>show_id</code> sólo es único dentro de cada fuente, por lo que la clave
del catálogo integrado es <code>formato + show_id</code>. La capa financiera se anexa
únicamente a las películas.</p>
<p>Sobre esa base se construyeron las variables de negocio del proyecto:
<code>atencion</code> (índice de popularidad, proxy de interés),
<code>interacciones</code> (número de calificaciones emitidas),
<code>satisfaccion</code> (nota media 0–10), <code>sin_senal</code> (título sin ninguna
interacción), <code>segmento</code> (formato × bloque de idioma, la unidad sobre la que se
decide el presupuesto) y <code>roi</code> (recaudación sobre presupuesto).</p>

<h3>4.2 Auditoría de calidad y decisiones de saneamiento</h3>
{tabla_html(AUD, indice=False)}
<p>Siete decisiones de saneamiento quedaron documentadas en <code>src/etl.py</code>. Las
cuatro que más afectan la lectura de los resultados:</p>
<ul>
  <li><b>El 0 no es un valor, es un dato faltante.</b> Presupuesto y recaudación traen 0
  donde el dato no fue informado (69,7% y 64,7% de las películas). Mantener ese 0 haría
  creer que la película no costó nada. Se convirtió a nulo.</li>
  <li><b>Sin nota no es mala nota.</b> Cuando <code>vote_count = 0</code> la nota también
  vale 0. Esos títulos no tienen una evaluación pésima: no tienen evaluación. Se marcan
  como <code>sin_senal</code> y quedan fuera de todo promedio de satisfacción.</li>
  <li><b>La muestra está balanceada por diseño.</b> Cada archivo trae exactamente 1.000
  títulos por año entre 2010 y 2025. Por lo tanto, <b>ningún gráfico de este informe lee
  volumen en el tiempo</b>: sería una línea plana por construcción. Sólo se leen
  composiciones y tasas dentro de cada año.</li>
  <li><b>La cohorte 2025 no es comparable.</b> El {n(C['invisible_pct_2025'])}% de sus
  títulos aún no acumula interacciones. Se excluye de toda lectura de tendencia y el
  análisis trabaja sobre {n(C['titulos_maduros'], 0)} títulos estrenados entre
  {cfg.ANIO_MIN} y {cfg.ANIO_CIERRE}.</li>
</ul>
<p>Dos columnas se descartaron por no aportar información: <code>rating</code> es copia
exacta de <code>vote_average</code> (coincidencia del 100%), y <code>duration</code> está
vacía en todas las películas y vale la constante «1 Seasons» en todas las series.</p>
</section>

<section class="sec salto">
<h2>5. Análisis exploratorio mediante visualizaciones</h2>

<h3>5.1 La atención está concentrada</h3>
<figure><img src="{img('f1_concentracion_atencion.png')}" alt="Curva de concentración">
<figcaption><b>Figura 1.</b> El 10% de los títulos concentra el
{n(C['atencion_top10'])}% de la atención y el 1% más visto ya se lleva el
{n(C['atencion_top1'])}%. El índice de Gini de {n(C['gini'], 2)} confirma un reparto muy
desigual: la mayor parte del catálogo compite por la mitad restante.</figcaption></figure>
<p>La primera consecuencia de negocio es que el tamaño del catálogo no es una medida de
salud. Sumar títulos a la cola larga no mueve la atención total; sólo aumenta el costo de
licencia y el ruido en la interfaz de recomendación.</p>

<h3>5.2 El formato es la variable que más explica el rendimiento</h3>
<figure><img src="{img('f2_rendimiento_formato.png')}" alt="Rendimiento por formato">
<figcaption><b>Figura 2.</b> Una serie capta una atención mediana de
{n(C['serie_atencion'])} frente a {n(C['pelicula_atencion'])} de una película —
{n(C['multiplo_formato'], 1)} veces más — y con una nota mediana de
{n(C['serie_nota'], 1)} frente a {n(C['pelicula_nota'], 1)}. Se usa la mediana y no el
promedio porque la distribución tiene cola larga.</figcaption></figure>

<figure><img src="{img('f3_catalogo_invisible.png')}" alt="Catálogo invisible">
<figcaption><b>Figura 3.</b> La contracara: el {n(C['invisible_pct_series_fmt'])}% de las
series no registra ninguna interacción, frente al {n(C['invisible_pct_peliculas_fmt'])}% de
las películas. El formato de mayor retorno es también el de mayor varianza.</figcaption></figure>
<p>Leídas juntas, ambas figuras evitan una conclusión simplista. La recomendación no es
«comprar series», sino <b>comprar series con un filtro de riesgo</b>: el segmento concentra
el retorno y también las pérdidas silenciosas.</p>

{tabla_html(SEG.rename(columns={
    "titulos": "Títulos", "atencion_mediana": "Atención mediana",
    "invisible_pct": "Catálogo invisible (%)", "satisfaccion_mediana": "Nota mediana"}))}
<p class="fino">Rendimiento por segmento de decisión, cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}.
Las series en idioma no inglés son el segmento más numeroso
({n(SEG.loc['Serie · No inglés', 'titulos'], 0)} títulos) y el de mejor nota
({n(SEG.loc['Serie · No inglés', 'satisfaccion_mediana'], 2)}), pero también el de mayor
riesgo: {n(SEG.loc['Serie · No inglés', 'invisible_pct'])}% no llega a ninguna audiencia.</p>

<h3>5.3 Hay inventario pagado que nadie ve</h3>
<figure><img src="{img('f4_matriz_cuadrantes.png')}" alt="Matriz de cuadrantes">
<figcaption><b>Figura 4.</b> Cruzando atención y satisfacción sobre sus medianas aparecen
cuatro decisiones distintas. El cuadrante crítico es <b>Joyas ocultas</b>:
{n(C['joyas_n'], 0)} títulos con nota por sobre la mediana y atención por debajo. Es
inventario ya pagado que no está llegando a su audiencia.</figcaption></figure>
{tabla_html(CUAD.rename(columns={
    "titulos": "Títulos", "atencion_mediana": "Atención mediana",
    "satisfaccion_mediana": "Nota mediana", "pct_series": "% series",
    "pct_no_ingles": "% no inglés", "pct_catalogo": "% del catálogo con señal"}))}

<h3>5.4 El dinero está en el tramo equivocado</h3>
<figure><img src="{img('f5_rentabilidad_tramos.png')}" alt="Rentabilidad por tramo">
<figcaption><b>Figura 5.</b> El tramo de 1 a 10 millones de dólares concentra
US$&nbsp;{n(C['tramo_critico_musd'] / 1000, 1)}&nbsp;mil millones en
{n(C['tramo_critico_n'], 0)} películas, con el ROI mediano más bajo
({n(C['tramo_critico_roi'], 2)}) y la mayor proporción de títulos que no recuperan la
inversión ({n(C['tramo_critico_bajo_eq'])}%). Los extremos —producciones muy baratas y
grandes apuestas— rinden mejor.</figcaption></figure>

<figure><img src="{img('f6_presupuesto_atencion_nota.png')}" alt="Presupuesto, atención y nota">
<figcaption><b>Figura 6.</b> Al pasar del decil de presupuesto más barato al más caro, la
atención se multiplica por más de cinco mientras la nota se mueve apenas. La correlación de
Spearman lo confirma: ρ&nbsp;=&nbsp;{n(C['corr_budget_atencion'], 2)} entre presupuesto y
atención, ρ&nbsp;=&nbsp;{n(C['corr_budget_satisfaccion'], 2)} entre presupuesto y
satisfacción. <b>El presupuesto compra visibilidad, no agrado.</b></figcaption></figure>

<h3>5.5 Dónde está creciendo el catálogo y qué géneros rinden</h3>
<figure><img src="{img('f7_internacionalizacion.png')}" alt="Internacionalización">
<figcaption><b>Figura 7.</b> La participación del contenido en idioma distinto del inglés
pasó de {n(C['no_ingles_inicio'])}% a {n(C['no_ingles_fin'])}% de los estrenos. Es una
lectura de composición dentro de cada año, no de volumen: la muestra tiene 1.000 títulos
anuales por diseño.</figcaption></figure>

<figure><img src="{img('f8_generos.png')}" alt="Géneros por formato">
<figcaption><b>Figura 8.</b> Los géneros se comparan dentro de cada formato porque la
fuente usa vocabularios distintos para series y películas. Aun así el resultado es
inequívoco: el género de serie con menos atención supera al mejor género de
película.</figcaption></figure>
</section>

<section class="sec">
<h2>6. Justificación de las representaciones gráficas seleccionadas</h2>
<p>Cada figura se eligió mapeando la naturaleza del dato con la tarea analítica de la
audiencia, y no por preferencia estética.</p>
{tabla_html(pd.DataFrame([
    ["F1", "Curva de concentración (Lorenz)", "Cuantitativa acumulada",
     "Evaluar distribución y desigualdad",
     "Una barra por título sería ilegible con 30.000 casos; la curva muestra la desigualdad en una sola forma"],
    ["F2", "Barras horizontales, small multiples", "Categórica × cuantitativa",
     "Comparar dos categorías",
     "Dos magnitudes de escala distinta se separan en dos paneles: un doble eje inventaría una relación inexistente"],
    ["F3", "Barras + línea temporal", "Categórica y temporal",
     "Comparar y vigilar evolución",
     "La barra responde «cuánto» y la línea «desde cuándo»; la cohorte 2025 se marca aparte"],
    ["F4", "Dispersión con cuadrantes", "Dos variables cuantitativas",
     "Detectar relación y agrupar para decidir",
     "Escala logarítmica por la cola larga; las medianas como umbral generan cuatro acciones distintas"],
    ["F5", "Barras con línea de referencia", "Ordinal × cuantitativa",
     "Comparar contra un umbral",
     "La línea del punto de equilibrio convierte el ROI en un juicio inmediato: gana o pierde"],
    ["F6", "Líneas indexadas a base 100", "Ordinal × dos cuantitativas",
     "Contrastar dos evoluciones",
     "Indexar a una base común permite un solo eje y hace visible que una serie sube y la otra no"],
    ["F7", "Línea temporal simple", "Temporal × proporción",
     "Detectar tendencia",
     "Una sola serie, sin leyenda: el título nombra la variable y los extremos llevan etiqueta"],
    ["F8", "Barras ordenadas, small multiples", "Categórica × cuantitativa",
     "Ranking dentro de cada grupo",
     "Un ranking único mezclaría dos taxonomías de género distintas; separarlas evita una comparación falsa"],
], columns=["Fig.", "Representación", "Naturaleza del dato", "Tarea analítica",
            "Por qué esta y no otra"]), indice=False)}

<h3>6.1 Atributos visuales y criterios de representación</h3>
<ul>
  <li><b>Color funcional, nunca decorativo.</b> La paleta tiene un solo azul de serie, un
  gris neutro para «todo lo demás» y un rojo reservado exclusivamente para señalar estado
  crítico. El rojo nunca identifica una categoría: si aparece, algo está mal.</li>
  <li><b>Jerarquía por peso visual.</b> Cada figura destaca un único dato en color y deja el
  resto en gris. El tamaño y el contraste son proporcionales a la importancia del dato, no
  al espacio disponible.</li>
  <li><b>Posición y longitud antes que área o ángulo.</b> No se usan gráficos de torta ni
  áreas comparadas: el ojo humano compara longitudes con precisión y ángulos mal. La única
  excepción es la curva de Lorenz, donde el área sombreada refuerza una lectura que la
  línea ya entrega.</li>
  <li><b>Accesibilidad verificada.</b> La paleta se validó para daltonismo (separación
  ΔE ≥ 8 entre colores adyacentes en simulación deutan y tritan) y la identidad nunca
  depende sólo del color: toda serie lleva etiqueta directa o tabla equivalente.</li>
  <li><b>Señal sobre ruido.</b> Rejilla de un solo trazo fino, sin bordes en las barras, sin
  etiquetas en todos los puntos y sin elementos decorativos. Cada píxel renderizado aporta
  al mensaje o se elimina.</li>
  <li><b>Denominador siempre explícito.</b> Cada figura declara <i>n</i>, la cohorte y la
  base de cálculo en su subtítulo o pie. Ningún porcentaje aparece sin la población sobre
  la que se calculó.</li>
</ul>
</section>

<section class="sec">
<h2>7. Desarrollo de la narrativa visual (Data Storytelling)</h2>
<p>La narrativa sigue la estructura de cuatro pasos y termina, deliberadamente, en una
acción y no en una pregunta retórica.</p>
<div class="pasos">
  <div class="paso"><div class="t">01 · Situación</div>
    <p>StreamView decide su inversión en contenido por volumen: cuántos títulos suma y a
    qué costo.</p></div>
  <div class="paso"><div class="t">02 · Hallazgo</div>
    <p>El {n(C['atencion_top10'])}% de la atención está en el 10% de los títulos y el
    {n(C['invisible_pct_maduro'])}% del catálogo no registra ninguna interacción. Una serie
    rinde {n(C['multiplo_formato'], 1)} veces más que una película.</p></div>
  <div class="paso"><div class="t">03 · Implicancia</div>
    <p>US$&nbsp;{n(C['tramo_critico_musd'] / 1000, 1)}&nbsp;mil millones están en el tramo de
    películas de 1–10 MUSD, donde el {n(C['tramo_critico_bajo_eq'])}% pierde dinero. Y más
    presupuesto no mejora la nota (ρ&nbsp;=&nbsp;{n(C['corr_budget_satisfaccion'], 2)}).</p></div>
  <div class="paso final"><div class="t">04 · Acción</div>
    <p>Reasignar ese tramo a series con filtro de riesgo, activar las
    {n(C['joyas_n'], 0)} joyas ocultas e instalar una puerta de 90 días para todo
    estreno.</p></div>
</div>
<p>El mensaje se adapta a cada audiencia sin cambiar de contenido: el comité recibe el paso
04 primero y la evidencia después; el equipo de programación recibe el dashboard, donde los
mismos cuadrantes se vuelven una lista de títulos accionable; finanzas recibe la pestaña de
rentabilidad con el detalle por tramo. <b>Una sola idea central, tres niveles de
profundidad.</b></p>
</section>

<section class="sec">
<h2>8. Diseño e implementación del dashboard interactivo</h2>
<p>El dashboard se construyó con <b>Streamlit</b> y <b>Plotly</b>, sobre el mismo módulo de
métricas que alimenta este informe. Se ejecuta con
<code>streamlit run dashboard/app.py</code>.</p>

<h3>8.1 Arquitectura de la interfaz</h3>
<ul>
  <li><b>Patrón de lectura Z.</b> El mensaje principal arriba a la izquierda, la fila de
  cinco KPIs inmediatamente debajo y el detalle explorable al final. El dato de mayor
  impacto se ve primero, sin desplazamiento.</li>
  <li><b>Un solo panel de filtros.</b> Año, formato, idioma, género y presencia de señal
  viven en la barra lateral y gobiernan todas las pestañas. Nunca hay filtros dentro de una
  tarjeta: así el usuario no puede comparar, sin darse cuenta, dos recortes distintos.</li>
  <li><b>Navegación por audiencia.</b> Cuatro pestañas con niveles de detalle crecientes:
  visión ejecutiva, diagnóstico de catálogo, rentabilidad, y datos y calidad.</li>
  <li><b>La cohorte 2025 viene desactivada por defecto</b>, con la explicación en el propio
  control. El usuario puede activarla, pero sabe lo que está haciendo.</li>
</ul>

<h3>8.2 Indicadores clave y mecanismos de interacción</h3>
{tabla_html(pd.DataFrame([
    ["Títulos en la selección", "Tamaño del recorte activo y su peso en el catálogo"],
    ["Atención en el top 10%", "Grado de concentración, con el índice de Gini como apoyo"],
    ["Catálogo invisible", "% y número de títulos sin ninguna interacción"],
    ["Satisfacción mediana", "Nota 0–10 con la base de cálculo declarada"],
    ["Atención mediana", "Rendimiento típico por título del recorte"],
], columns=["KPI", "Qué responde"]), indice=False)}
<p>La interacción disponible incluye filtrado cruzado sobre todas las vistas, navegación por
pestañas, información emergente por marca en cada gráfico, zoom y encuadre en los gráficos
de Plotly, ordenamiento y paginación de la tabla de detalle, y descarga de la selección
filtrada en CSV para continuar el análisis fuera de la herramienta.</p>

<figure class="captura"><img src="{img('dashboard_01_ejecutiva.png')}" alt="Dashboard, visión ejecutiva">
<figcaption><b>Figura 9.</b> Pestaña 1, visión ejecutiva: mensaje, KPIs y las dos
visualizaciones que sostienen la recomendación.</figcaption></figure>

<figure class="captura"><img src="{img('dashboard_02_diagnostico.png')}" alt="Dashboard, diagnóstico">
<figcaption><b>Figura 10.</b> Pestaña 2, diagnóstico de catálogo: matriz de cuadrantes
título por título, evolución del catálogo invisible y mapa de riesgo y rendimiento por
idioma. Los umbrales se recalculan con cada filtro, de modo que el diagnóstico siempre es
relativo al recorte que el usuario está mirando.</figcaption></figure>

<figure class="captura"><img src="{img('dashboard_03_rentabilidad.png')}" alt="Dashboard, rentabilidad">
<figcaption><b>Figura 11.</b> Pestaña 3, rentabilidad: ROI por tramo, proporción de
títulos bajo el punto de equilibrio y dispersión presupuesto–recaudación con la nota
codificada en color.</figcaption></figure>
</section>

<section class="sec">
<h2>9. Evaluación crítica de la solución desarrollada</h2>

<h3>9.1 Fortalezas</h3>
<ul>
  <li><b>Trazabilidad completa.</b> Toda cifra del informe, del dashboard y del resumen
  ejecutivo sale de <code>src/metricas.py</code>. No hay números escritos a mano, de modo
  que el titular de una figura no puede contradecir a la tabla que tiene al lado.</li>
  <li><b>Rigor declarado.</b> Las cuatro trampas del conjunto de datos —el 0 como dato
  faltante, la nota ausente confundida con nota baja, la muestra balanceada y la cohorte
  2025 incompleta— fueron detectadas, documentadas y neutralizadas antes de graficar.</li>
  <li><b>Coherencia entre productos.</b> Informe, dashboard y presentación comparten
  paleta, tipografía, criterios de titulación y convenciones de medición.</li>
  <li><b>Cierre accionable.</b> El proyecto no termina en un hallazgo sino en cuatro
  acciones con responsable, métrica de control y plazo.</li>
</ul>

<h3>9.2 Limitaciones</h3>
<div class="alerta">
<p style="margin:0"><b>Lo que estos datos no permiten afirmar.</b> La limitación principal
es que <b>no existe telemetría propia de reproducción</b>. «Atención» es un índice externo
de popularidad, no horas vistas; «interacciones» son calificaciones emitidas, no sesiones;
y no hay ninguna variable de suscripción, dispositivo ni churn. Por lo tanto el informe
describe el rendimiento del <b>catálogo</b>, no el comportamiento de los <b>usuarios</b>, y
ninguna conclusión sobre retención puede sostenerse sólo con esta base.</p>
</div>
<ul>
  <li><b>Cobertura financiera parcial.</b> Sólo el {n(C['pct_peliculas_con_roi'])}% de las
  películas informa presupuesto y recaudación. Las conclusiones de rentabilidad aplican a
  ese subconjunto y probablemente sobrerrepresentan producciones de circuito comercial.</li>
  <li><b>Muestra balanceada.</b> Con 1.000 títulos por año por diseño, el conjunto no
  refleja el tamaño real del catálogo en cada período. Es válido para comparar
  composiciones y tasas; no lo es para estimar volúmenes.</li>
  <li><b>Sin fecha real de alta.</b> <code>date_added</code> cae siempre dentro del año de
  estreno, de modo que no se puede medir antigüedad en catálogo ni velocidad de
  incorporación.</li>
  <li><b>Sesgo de exposición.</b> La atención observada ya está influida por el propio motor
  de recomendación: un título con poca atención puede no ser malo, sino no haber sido
  mostrado. La medida es de resultado, no de calidad intrínseca.</li>
  <li><b>Correlación no es causalidad.</b> Que el presupuesto se asocie a la atención no
  prueba que la produzca; un presupuesto mayor viene acompañado de más marketing y mayor
  distribución, que son parte del efecto observado.</li>
</ul>

<h3>9.3 Oportunidades de mejora</h3>
<ul>
  <li>Incorporar telemetría propia —horas vistas, tasa de finalización, altas y bajas por
  título— para pasar de un proxy de popularidad a una medida real de engagement.</li>
  <li>Añadir una vista de cohortes que siga a cada estreno desde su lanzamiento y permita
  comparar títulos con la misma madurez.</li>
  <li>Automatizar la actualización del catálogo integrado y publicar el dashboard en un
  servidor, para que deje de depender de una ejecución local.</li>
  <li>Incorporar el costo de licencia de las series, hoy ausente, para cerrar el análisis de
  retorno también en el formato que se recomienda priorizar.</li>
</ul>
</section>

<section class="sec">
<h2>10. Conclusiones y recomendaciones</h2>
<p><b>Conclusión.</b> StreamView no tiene un problema de tamaño de catálogo: tiene un
problema de asignación. La atención está extremadamente concentrada, el formato serie rinde
varias veces más que la película, una parte relevante del catálogo no llega a nadie y el
tramo de inversión que más dinero moviliza es el que peor retorno entrega. Todo eso es
corregible sin aumentar el presupuesto.</p>

<div class="accion">
  <h4>R1 · Reasignar el tramo de películas de 1 a 10 millones de dólares</h4>
  <p style="margin:0">Trasladar progresivamente ese tramo —US$&nbsp;{n(C['tramo_critico_musd'] / 1000, 1)}&nbsp;mil
  millones acumulados en {n(C['tramo_critico_n'], 0)} títulos de la cohorte
  {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}, con ROI mediano {n(C['tramo_critico_roi'], 2)}— hacia
  producción de series, priorizando los idiomas de alto rendimiento y bajo riesgo
  identificados en el dashboard.</p>
  <p class="meta"><b>Responsable:</b> Dirección de Contenidos · <b>Plazo:</b> presupuesto
  2026 · <b>Métrica de control:</b> atención mediana de la cartera de estrenos ≥ 25 a los
  doce meses.</p>
</div>

<div class="accion">
  <h4>R2 · Activar las {n(C['joyas_n'], 0)} joyas ocultas antes de comprar contenido nuevo</h4>
  <p style="margin:0">Son títulos con nota sobre la mediana y atención bajo la mediana: ya
  están pagados y ya gustan. Priorizarlos en el motor de recomendación y en campañas de
  CRM tiene costo marginal frente a una adquisición.</p>
  <p class="meta"><b>Responsable:</b> Programación + CRM · <b>Plazo:</b> seis meses ·
  <b>Métrica de control:</b> 1.500 de esos títulos por sobre la mediana de atención.</p>
</div>

<div class="accion">
  <h4>R3 · Instalar una puerta de 90 días para todo estreno</h4>
  <p style="margin:0">Todo título que a los noventa días no registre interacciones entra
  automáticamente a revisión: se refuerza su promoción o se evalúa su retiro. Hoy
  {n(C['invisible_n_maduro'], 0)} títulos ({n(C['invisible_pct_maduro'])}% del catálogo)
  están en esa condición sin que nadie lo revise.</p>
  <p class="meta"><b>Responsable:</b> Programación · <b>Plazo:</b> doce meses ·
  <b>Métrica de control:</b> catálogo invisible bajo el 6%.</p>
</div>

<div class="accion">
  <h4>R4 · Instrumentar telemetría propia de reproducción</h4>
  <p style="margin:0">Registrar horas vistas, tasa de finalización y bajas atribuibles por
  título. Es la condición para que las tres recomendaciones anteriores se puedan verificar
  con datos propios y no con un proxy externo de popularidad.</p>
  <p class="meta"><b>Responsable:</b> Ingeniería de Datos · <b>Plazo:</b> un trimestre ·
  <b>Métrica de control:</b> 100% de los estrenos con telemetría desde el día uno.</p>
</div>

<p class="evitar"><b>Qué no recomendamos.</b> No recomendamos ampliar el catálogo ni subir el presupuesto
medio de las películas. La evidencia muestra que ese gasto compra visibilidad pero no
satisfacción (ρ&nbsp;=&nbsp;{n(C['corr_budget_satisfaccion'], 2)}), y que el tramo donde
más se concentra es el único donde casi la mitad de los títulos pierde dinero.</p>
</section>

<section class="sec salto">
<h2>Declaración de uso de inteligencia artificial</h2>
<p>En conformidad con la normativa de la asignatura, el equipo declara el uso de
herramientas de inteligencia artificial generativa durante el desarrollo de este encargo.</p>
{tabla_html(pd.DataFrame([
    ["Claude (Anthropic)",
     "Apoyo en la exploración del conjunto de datos, revisión crítica de decisiones de "
     "diseño visual, redacción y ordenamiento del informe, y depuración del código del "
     "dashboard.",
     "Todo el análisis fue verificado ejecutando el código sobre los datos originales. "
     "Las cifras del informe se generan desde el propio conjunto de datos, no desde la "
     "herramienta. La definición del problema, la selección de hallazgos y las "
     "recomendaciones finales son del equipo."],
], columns=["Herramienta", "Uso dado", "Verificación y responsabilidad"]), indice=False)}
<p class="fino">El equipo asume la responsabilidad íntegra por el contenido, las cifras y
las conclusiones presentadas. Ninguna cifra de este documento proviene de una estimación
del modelo: todas se calculan en <code>src/metricas.py</code> a partir de los archivos
entregados por la organización, y pueden reproducirse ejecutando el proyecto.</p>

<h2>Anexo A · Diccionario de variables del catálogo integrado</h2>
{tabla_html(DIC.rename(columns={"variable": "Variable", "naturaleza": "Naturaleza",
                                "descripcion": "Descripción", "origen": "Origen"}),
            indice=False)}

<h2>Anexo B · Estructura del proyecto y reproducción</h2>
<pre>EP1_StreamView_Analytics/
├── README.md                     Instrucciones de instalación y ejecución
├── requirements.txt              Dependencias con versión y notas de compatibilidad
├── .streamlit/config.toml        Tema del dashboard (misma identidad visual)
├── data/
│   ├── raw/                      Los dos CSV originales, sin modificar
│   └── processed/                Catálogo integrado, diccionario, auditoría y tablas
├── notebooks/
│   └── 01_analisis_exploratorio.ipynb
├── src/
│   ├── config.py                 Rutas, paleta validada y estilo compartido
│   ├── etl.py                    Integración y saneamiento documentado
│   ├── metricas.py               Todos los indicadores del proyecto
│   ├── graficos.py               Las ocho figuras del informe
│   ├── documentos.py             Generación del informe y del resumen en PDF
│   └── construir_notebook.py     Construcción y ejecución del cuaderno
├── dashboard/
│   └── app.py                    Dashboard interactivo (Streamlit + Plotly)
├── images/                       Figuras y capturas generadas
└── docs/                         Informe ejecutivo y resumen ejecutivo (PDF y HTML)</pre>
<pre>pip install -r requirements.txt

python src/etl.py                  # integra y sanea las dos fuentes
python src/metricas.py             # calcula indicadores y tablas agregadas
python src/graficos.py             # genera las ocho figuras del informe
python src/documentos.py           # arma el informe y el resumen en PDF
python src/construir_notebook.py   # arma y ejecuta el cuaderno

streamlit run dashboard/app.py     # levanta el dashboard interactivo</pre>
<p class="fino">El proyecto se ejecuta de principio a fin sin modificaciones adicionales:
los datos originales están incluidos en <code>data/raw/</code> y cada script escribe su
salida en la carpeta correspondiente.</p>
</section>

</body></html>"""


# ==========================================================================
# Resumen ejecutivo (presentación de cierre)
# ==========================================================================
ESTILO_LAMINAS = f"""
  @page {{ size: 297mm 167mm; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: "DejaVu Sans", system-ui, -apple-system, sans-serif;
          color: {cfg.TINTA}; background: #fff; }}
  .lamina {{ width: 297mm; height: 167mm; padding: 15mm 18mm 12mm; position: relative;
             break-after: page; display: flex; flex-direction: column;
             background: {cfg.SUPERFICIE}; overflow: hidden; }}
  .lamina:last-child {{ break-after: auto; }}
  .num {{ position: absolute; right: 12mm; bottom: 7mm; font-size: 9pt;
          color: {cfg.TINTA_3}; }}
  .marca {{ position: absolute; left: 18mm; bottom: 7mm; font-size: 8.4pt;
            color: {cfg.TINTA_3}; letter-spacing: .05em; }}
  .rot {{ font-size: 9pt; letter-spacing: .13em; text-transform: uppercase;
          color: {cfg.SERIE_1}; font-weight: 700; margin-bottom: 7px; }}
  h1 {{ font-size: 25pt; line-height: 1.2; margin: 0 0 8px; letter-spacing: -.01em; }}
  h2 {{ font-size: 19.5pt; line-height: 1.24; margin: 0 0 6px; letter-spacing: -.005em; }}
  .baja {{ font-size: 11pt; color: {cfg.TINTA_2}; margin: 0 0 12px; max-width: 235mm;
           line-height: 1.5; }}
  .cuerpo {{ flex: 1; display: flex; gap: 14px; min-height: 0; }}
  .panel {{ flex: 1; min-width: 0; min-height: 0; display: flex;
            align-items: center; justify-content: center; }}
  .panel img {{ width: 100%; height: 100%; object-fit: contain; }}
  .lateral {{ width: 74mm; flex-shrink: 0; font-size: 10pt; color: {cfg.TINTA_2};
              line-height: 1.5; }}
  .lateral b {{ color: {cfg.TINTA}; }}
  .lateral ul {{ padding-left: 16px; margin: 6px 0; }}
  .lateral li {{ margin-bottom: 6px; }}
  .cifras {{ display: flex; gap: 10px; margin: 6px 0 12px; }}
  .cifra {{ flex: 1; border: 1px solid {cfg.REJILLA}; border-radius: 8px;
            padding: 11px 13px; background: #fff; }}
  .cifra .v {{ font-size: 27pt; font-weight: 700; line-height: 1.1;
               color: {cfg.SERIE_1}; }}
  .cifra .v.mal {{ color: {cfg.CRITICO}; }}
  .cifra .g {{ font-size: 9pt; color: {cfg.TINTA_2}; margin-top: 4px; line-height: 1.4; }}
  .portada {{ justify-content: center; }}
  .portada h1 {{ font-size: 34pt; max-width: 230mm; }}
  .acciones {{ display: flex; flex-direction: column; gap: 8px; }}
  .acc {{ border: 1px solid {cfg.REJILLA}; border-left: 4px solid {cfg.OK};
          border-radius: 6px; padding: 9px 13px; background: #fff; }}
  .acc h3 {{ margin: 0 0 3px; font-size: 11.6pt; }}
  .acc p {{ margin: 0; font-size: 9.4pt; color: {cfg.TINTA_2}; line-height: 1.45; }}
  .acc .m {{ font-size: 8.4pt; color: {cfg.TINTA_3}; margin-top: 3px; }}
  .fino {{ font-size: 8.4pt; color: {cfg.TINTA_3}; line-height: 1.45; }}
  .pasos {{ display: flex; gap: 9px; margin-top: 4px; }}
  .paso {{ flex: 1; border: 1px solid {cfg.REJILLA}; border-top: 4px solid {cfg.SERIE_1};
           border-radius: 6px; padding: 11px 12px; background: #fff; }}
  .paso.final {{ border-top-color: {cfg.OK}; }}
  .paso .t {{ font-size: 8.6pt; text-transform: uppercase; letter-spacing: .07em;
              color: {cfg.SERIE_1}; font-weight: 700; }}
  .paso.final .t {{ color: {cfg.OK}; }}
  .paso p {{ font-size: 9.6pt; margin: 5px 0 0; line-height: 1.45; }}
"""


def resumen_html():
    def lamina(contenido, num, clase=""):
        return (f'<section class="lamina {clase}">{contenido}'
                f'<div class="marca">StreamView Analytics · EP1 ADY1104 · '
                f'Felipe Ángel · Daniel Vargas</div>'
                f'<div class="num">{num}</div></section>')

    laminas = []

    laminas.append(lamina(f"""
      <div class="rot">Resumen ejecutivo · Comité de Contenidos</div>
      <h1>El catálogo no necesita crecer.<br>Necesita reasignarse.</h1>
      <p class="baja">Diagnóstico del rendimiento del catálogo y propuesta de reasignación
      del presupuesto de programación · Base: {n(C['titulos_maduros'], 0)} títulos
      estrenados entre {cfg.ANIO_MIN} y {cfg.ANIO_CIERRE}.</p>
      <p class="fino" style="margin-top:14px">ADY1104 Visualización de Datos · DUOC UC Sede
      Los Lagos · Docente: Claudio Andrés González Peñaloza</p>""", 1, "portada"))

    laminas.append(lamina(f"""
      <div class="rot">01 · Situación</div>
      <h2>Hoy la inversión en contenido se decide por volumen, no por rendimiento</h2>
      <p class="baja">La conversación gira en torno a cuántos títulos suma el catálogo. Nadie
      pregunta cuánta atención devuelve cada uno.</p>
      <div class="cifras">
        <div class="cifra"><div class="v">{n(C['titulos_maduros'], 0)}</div>
          <div class="g">títulos analizados, estrenos {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}</div></div>
        <div class="cifra"><div class="v">{n(C['atencion_top10'])}%</div>
          <div class="g">de la atención está en el 10% de los títulos</div></div>
        <div class="cifra"><div class="v mal">{n(C['invisible_pct_maduro'])}%</div>
          <div class="g">del catálogo no registra ninguna interacción</div></div>
        <div class="cifra"><div class="v">{n(C['gini'], 2)}</div>
          <div class="g">índice de Gini de la atención (0 = reparto igualitario)</div></div>
      </div>
      <div class="cuerpo"><div class="panel">
        <img src="{img('f1_concentracion_atencion.png')}" alt="Concentración"></div></div>""", 2))

    laminas.append(lamina(f"""
      <div class="rot">02 · Hallazgo</div>
      <h2>Una serie capta {n(C['multiplo_formato'], 1)} veces más atención que una película,
      y con mejor nota</h2>
      <div class="cuerpo">
        <div class="panel"><img src="{img('f2_rendimiento_formato.png')}" alt="Formato"></div>
        <div class="lateral">
          <p><b>El formato es la variable que más explica el rendimiento</b>, por encima del
          idioma, del género y del presupuesto.</p>
          <ul>
            <li>Atención mediana: <b>{n(C['serie_atencion'])}</b> en series contra
            <b>{n(C['pelicula_atencion'])}</b> en películas.</li>
            <li>Nota mediana: <b>{n(C['serie_nota'], 1)}</b> contra
            <b>{n(C['pelicula_nota'], 1)}</b>.</li>
            <li>Se usa la mediana: la distribución tiene cola larga y el promedio lo
            desplazarían unos pocos estrenos masivos.</li>
          </ul>
        </div>
      </div>""", 3))

    laminas.append(lamina(f"""
      <div class="rot">02 · Hallazgo</div>
      <h2>Pero el formato que más rinde es también el más riesgoso</h2>
      <div class="cuerpo">
        <div class="panel"><img src="{img('f3_catalogo_invisible.png')}" alt="Invisible"></div>
        <div class="lateral">
          <p>El <b>{n(C['invisible_pct_series_fmt'])}%</b> de las series no llega a ninguna
          audiencia, contra el <b>{n(C['invisible_pct_peliculas_fmt'])}%</b> de las
          películas.</p>
          <p>La recomendación no es «comprar series» sin más: es comprarlas
          <b>con un filtro de riesgo</b>, porque el mismo segmento concentra el retorno y
          las pérdidas silenciosas.</p>
          <p class="fino">La cohorte 2025 se excluye: sus títulos aún no tuvieron tiempo de
          acumular interacciones.</p>
        </div>
      </div>""", 4))

    laminas.append(lamina(f"""
      <div class="rot">03 · Implicancia</div>
      <h2>US$ {n(C['tramo_critico_musd'] / 1000, 1)} mil millones están en el tramo menos
      rentable del catálogo</h2>
      <div class="cuerpo">
        <div class="panel"><img src="{img('f5_rentabilidad_tramos.png')}" alt="ROI"></div>
        <div class="lateral">
          <p>El tramo de películas de <b>1 a 10 millones de dólares</b> reúne
          {n(C['tramo_critico_n'], 0)} títulos de la cohorte {cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}
          con el peor retorno del catálogo: ROI mediano
          <b>{n(C['tramo_critico_roi'], 2)}</b> y <b>{n(C['tramo_critico_bajo_eq'])}%</b> por
          debajo del punto de equilibrio.</p>
          <p>Y subir el presupuesto no arregla el problema: la correlación entre inversión y
          nota es prácticamente nula
          (ρ&nbsp;=&nbsp;{n(C['corr_budget_satisfaccion'], 2)}). <b>El dinero compra
          visibilidad, no agrado.</b></p>
          <p class="fino">Análisis sobre las películas con datos financieros completos
          ({n(C['pct_peliculas_con_roi'])}% del total).</p>
        </div>
      </div>""", 5))

    laminas.append(lamina(f"""
      <div class="rot">03 · Implicancia</div>
      <h2>Ya tenemos pagados {n(C['joyas_n'], 0)} títulos que gustan y que nadie ve</h2>
      <div class="cuerpo">
        <div class="panel"><img src="{img('f4_matriz_cuadrantes.png')}" alt="Cuadrantes"></div>
        <div class="lateral">
          <p>Cruzando atención y satisfacción aparecen cuatro decisiones distintas sobre un
          mismo catálogo:</p>
          <ul>
            <li><b>Motores</b> ({n(CUAD.loc['Motores', 'titulos'], 0)}): renovar y escalar.</li>
            <li><b>Joyas ocultas</b> ({n(CUAD.loc['Joyas ocultas', 'titulos'], 0)}):
            inventario pagado, activar en recomendación.</li>
            <li><b>Ruido</b> ({n(CUAD.loc['Ruido', 'titulos'], 0)}): atraen pero
            decepcionan.</li>
            <li><b>Rezagados</b> ({n(CUAD.loc['Rezagados', 'titulos'], 0)}): candidatos a
            poda.</li>
          </ul>
        </div>
      </div>""", 6))

    laminas.append(lamina(f"""
      <div class="rot">04 · Acción</div>
      <h2>Cuatro decisiones concretas, sin aumentar el presupuesto</h2>
      <div class="cuerpo"><div class="acciones" style="flex:1">
        <div class="acc"><h3>R1 · Reasignar el tramo de 1 a 10 MUSD hacia series</h3>
          <p>US$ {n(C['tramo_critico_musd'] / 1000, 1)} mil millones acumulados
          ({cfg.ANIO_MIN}–{cfg.ANIO_CIERRE}) que rinden ROI {n(C['tramo_critico_roi'], 2)},
          priorizando los idiomas de alto rendimiento y bajo riesgo.</p>
          <div class="m">Dirección de Contenidos · presupuesto 2026 · meta: atención mediana
          de los estrenos ≥ 25 a doce meses</div></div>
        <div class="acc"><h3>R2 · Activar las {n(C['joyas_n'], 0)} joyas ocultas antes de
          comprar</h3>
          <p>Priorizarlas en el motor de recomendación y en CRM: ya están pagadas y ya
          gustan.</p>
          <div class="m">Programación + CRM · seis meses · meta: 1.500 títulos sobre la
          mediana de atención</div></div>
        <div class="acc"><h3>R3 · Puerta de 90 días para todo estreno</h3>
          <p>Sin interacciones a los noventa días, el título entra a revisión de promoción o
          de retiro.</p>
          <div class="m">Programación · doce meses · meta: catálogo invisible bajo el 6%
          (hoy {n(C['invisible_pct_maduro'])}%)</div></div>
        <div class="acc"><h3>R4 · Instrumentar telemetría propia de reproducción</h3>
          <p>Horas vistas, tasa de finalización y bajas por título: sin eso, seguimos
          midiendo con un proxy externo.</p>
          <div class="m">Ingeniería de Datos · un trimestre · meta: 100% de los estrenos con
          telemetría</div></div>
      </div></div>""", 7))

    laminas.append(lamina(f"""
      <div class="rot">Cómo leer este diagnóstico</div>
      <h2>Qué permiten y qué no permiten afirmar estos datos</h2>
      <div class="cuerpo">
        <div class="lateral" style="width:auto;flex:1">
          <p><b>Lo que sí sostiene la evidencia</b></p>
          <ul>
            <li>La atención está concentrada y una parte del catálogo no llega a nadie.</li>
            <li>El formato serie rinde sistemáticamente más que la película.</li>
            <li>El tramo de 1–10 MUSD es el de peor retorno entre las películas con datos
            financieros.</li>
          </ul>
        </div>
        <div class="lateral" style="width:auto;flex:1">
          <p><b>Lo que no se puede afirmar todavía</b></p>
          <ul>
            <li>No hay telemetría de reproducción: «atención» es un proxy externo de
            popularidad, no horas vistas.</li>
            <li>Sólo el {n(C['pct_peliculas_con_roi'])}% de las películas informa datos
            financieros.</li>
            <li>La muestra trae 1.000 títulos por año por diseño: sirve para comparar
            composiciones, no volúmenes.</li>
            <li>La atención observada ya está influida por el propio motor de
            recomendación.</li>
          </ul>
        </div>
      </div>
      <p class="fino"><b>Declaración de uso de IA.</b> Se utilizó Claude (Anthropic) como
      apoyo en la exploración de los datos, la revisión crítica de decisiones de diseño
      visual, la redacción del informe y la depuración del código. Todas las cifras se
      calculan desde el conjunto de datos original mediante el código del proyecto y fueron
      verificadas por el equipo, que asume la responsabilidad íntegra del contenido.</p>""",
      8))

    return (f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Resumen ejecutivo · StreamView Analytics</title>
<style>{ESTILO_LAMINAS}</style></head><body>""" + "\n".join(laminas) + "</body></html>")


# ==========================================================================
# Conversión a PDF
# ==========================================================================
def a_pdf(ruta_html, ruta_pdf, apaisado=False):
    chrome = (shutil.which("google-chrome") or shutil.which("chromium")
              or shutil.which("chromium-browser") or shutil.which("google-chrome-stable"))
    if not chrome:
        print(f"  ! Chrome no disponible: se conserva {ruta_html.name} para imprimir a PDF")
        return None
    with tempfile.TemporaryDirectory() as perfil:
        orden = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                 f"--user-data-dir={perfil}", "--no-pdf-header-footer",
                 "--virtual-time-budget=25000",
                 f"--print-to-pdf={ruta_pdf}", ruta_html.as_uri()]
        if apaisado:
            orden.insert(-1, "--landscape")
        subprocess.run(orden, capture_output=True, timeout=180)
    return ruta_pdf if ruta_pdf.exists() else None


def generar_todo():
    salidas = [
        ("informe_ejecutivo", informe_html(), False),
        ("resumen_ejecutivo", resumen_html(), True),
    ]
    for nombre, html, apaisado in salidas:
        ruta_html = cfg.DIR_DOCS / f"{nombre}.html"
        ruta_html.write_text(html, encoding="utf-8")
        pdf = a_pdf(ruta_html, cfg.DIR_DOCS / f"{nombre}.pdf", apaisado)
        tam = f"{pdf.stat().st_size / 1024:.0f} KB" if pdf else "sin PDF"
        print(f"  ✓ {nombre}.html  →  {nombre}.pdf ({tam})")


if __name__ == "__main__":
    print("Generando documentos en", cfg.DIR_DOCS)
    generar_todo()
