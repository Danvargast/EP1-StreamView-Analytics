# StreamView Analytics · Rendimiento del catálogo

**Evaluación Parcial N°1 — ADY1104 Visualización de Datos**
Escuela de Informática y Telecomunicaciones · DUOC UC, Sede Los Lagos
Carrera: Ingeniería en Informática mención Ciencia de Datos

**Equipo consultor:** Felipe Ángel · Daniel Vargas
**Docente:** Claudio Andrés González Peñaloza

---

## El encargo en una frase

> **La decisión no es cuánto contenido comprar, sino de qué tipo.**
> Una serie capta **3,4 veces** más atención que una película y con mejor nota,
> mientras **US$ 6,6 mil millones** acumulados entre 2010 y 2024 siguen puestos en el
> tramo de películas de 1 a 10 millones de dólares, donde el **45,7%** no recupera la
> inversión.

StreamView Analytics decide su inversión en contenido por volumen —cuántos títulos
suma el catálogo— y no por rendimiento. Este proyecto diagnostica dónde se produce
realmente el retorno y propone una reasignación concreta del presupuesto, sin
aumentarlo.

---

## Entregables

| Entregable | Archivo |
|---|---|
| Informe ejecutivo (17 páginas) | `docs/informe_ejecutivo.pdf` |
| Resumen ejecutivo (8 láminas) | `docs/resumen_ejecutivo.pdf` |
| Dashboard interactivo | `dashboard/app.py` → `streamlit run dashboard/app.py` |
| Cuaderno de análisis exploratorio | `notebooks/01_analisis_exploratorio.ipynb` |
| Figuras del informe | `images/f1…f8_*.png` |
| Capturas del dashboard | `images/dashboard_0*.png` |
| Datos originales y procesados | `data/raw/` · `data/processed/` |

---

## Cómo ejecutar el proyecto

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt

python src/etl.py                  # integra y sanea las dos fuentes
python src/metricas.py             # calcula indicadores y tablas agregadas
python src/graficos.py             # genera las ocho figuras del informe
python src/documentos.py           # arma el informe y el resumen en PDF
python src/construir_notebook.py   # arma y ejecuta el cuaderno

streamlit run dashboard/app.py     # levanta el dashboard interactivo
```

Los datos originales están incluidos en `data/raw/`, de modo que el proyecto se
ejecuta de principio a fin sin pasos ni descargas adicionales. Cada script escribe
su salida en la carpeta correspondiente y puede volver a ejecutarse sin efectos
secundarios.

---

## Estructura del proyecto

```
EP1_StreamView_Analytics/
├── README.md                     Este archivo
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
└── docs/                         Informe y resumen ejecutivo (PDF y HTML)
```

**Regla de arquitectura:** toda cifra del informe, del dashboard, del cuaderno y de
la presentación se calcula en `src/metricas.py` y sólo ahí. No hay números escritos
a mano en ningún documento, de modo que el titular de una figura no puede
contradecir a la tabla que tiene al lado.

---

## Fuentes de datos

Dos fuentes corporativas de catálogo, integradas en una base única de **31.991
títulos** estrenados entre 2010 y 2025.

| Archivo | Contenido | Filas | Columnas |
|---|---|---|---|
| `netflix_movies_detailed_up_to_2025.csv` | Películas | 16.000 | 18 (incluye presupuesto y recaudación) |
| `netflix_tv_shows_detailed_up_to_2025.csv` | Series | 16.000 | 16 |

El diccionario completo de variables está en `data/processed/diccionario_datos.csv`
y la auditoría de calidad en `data/processed/auditoria_calidad.csv`.

### Cuatro trampas detectadas antes de graficar

1. **El 0 no es un valor, es un dato faltante.** Presupuesto y recaudación traen 0
   donde el dato no fue informado (69,7% y 64,7%). Se convirtió a nulo: mantenerlo
   haría creer que la película no costó nada.
2. **Sin nota no es mala nota.** Cuando `vote_count = 0` la nota también vale 0.
   Esos títulos se marcan como `sin_senal` y quedan fuera de todo promedio de
   satisfacción. Incluirlos bajaba la nota media de las series de 7,02 a 5,42 por
   una razón que no existe.
3. **La muestra está balanceada por diseño.** Exactamente 1.000 títulos por año y
   por archivo. Por eso **ningún gráfico de este proyecto lee volumen en el
   tiempo**: sería una línea plana por construcción.
4. **La cohorte 2025 no es comparable.** El 68,2% de sus títulos aún no acumula
   interacciones. Se excluye de toda lectura de tendencia y el análisis trabaja
   sobre 30.000 títulos (2010–2024).

---

## Hallazgos principales

| Hallazgo | Evidencia |
|---|---|
| La atención está extremadamente concentrada | El 10% de los títulos concentra el **47,5%** de la atención; el 1% más visto ya se lleva el 17,7%. Gini = 0,58 |
| El formato es la variable que más explica el rendimiento | Atención mediana **37,4** en series contra **11,1** en películas (×3,4); nota **7,2** contra **6,4** |
| El formato que más rinde es el más riesgoso | El **20,3%** de las series no registra ninguna interacción, contra el 1,1% de las películas |
| Hay inventario pagado que nadie ve | **5.088 títulos** con nota sobre la mediana y atención por debajo |
| El dinero está en el tramo equivocado | **US$ 6,6 mil millones** acumulados en 1.196 películas de 1–10 MUSD (2010–2024), ROI mediano 1,20 y 45,7% bajo el punto de equilibrio |
| El presupuesto compra visibilidad, no agrado | ρ de Spearman presupuesto–atención = **0,56**; presupuesto–satisfacción = **0,06** |
| El catálogo se internacionalizó | El contenido no inglés pasó de **53,8%** a **61,2%** de los estrenos |

---

## Recomendaciones

| | Recomendación | Responsable · plazo | Métrica de control |
|---|---|---|---|
| **R1** | Reasignar el tramo de películas de 1–10 MUSD hacia series, priorizando idiomas de alto rendimiento y bajo riesgo | Dirección de Contenidos · presupuesto 2026 | Atención mediana de los estrenos ≥ 25 a doce meses |
| **R2** | Activar las 5.088 joyas ocultas en recomendación y CRM antes de comprar contenido nuevo | Programación + CRM · seis meses | 1.500 títulos por sobre la mediana de atención |
| **R3** | Instalar una puerta de 90 días: sin interacciones, el estreno entra a revisión | Programación · doce meses | Catálogo invisible bajo el 6% (hoy 10,7%) |
| **R4** | Instrumentar telemetría propia de reproducción | Ingeniería de Datos · un trimestre | 100% de los estrenos con telemetría |

---

## El dashboard

Cuatro pestañas con niveles de detalle crecientes, una para cada audiencia:

1. **Visión ejecutiva** — mensaje, cinco KPIs, concentración de la atención y
   rendimiento por segmento de decisión.
2. **Diagnóstico de catálogo** — matriz de cuadrantes título por título, evolución
   del catálogo invisible y mapa de riesgo y rendimiento por idioma.
3. **Rentabilidad** — ROI por tramo de presupuesto, proporción bajo el punto de
   equilibrio y dispersión presupuesto–recaudación.
4. **Datos y calidad** — tabla de detalle ordenable, descarga en CSV, control de
   calidad y diccionario de variables.

**Decisiones de diseño.** Los filtros viven en una sola barra lateral y gobiernan
todas las pestañas: nunca hay filtros dentro de una tarjeta, para que el usuario no
compare sin darse cuenta dos recortes distintos. La cohorte 2025 viene desactivada
por defecto, con la explicación en el propio control. Los umbrales de los cuadrantes
se recalculan con cada filtro, de modo que el diagnóstico siempre es relativo al
recorte que el usuario está mirando.

---

## Criterios de diseño visual aplicados

- **Titulación comunicacional.** El título de cada figura enuncia la conclusión, no
  el tema: «Una serie capta 3,4 veces más atención que una película» en lugar de
  «Atención por formato».
- **Jerarquía por peso visual.** Cada figura destaca un único dato en color y deja
  el resto en gris neutro.
- **Color funcional, nunca decorativo.** Un solo azul de serie, un gris para «todo
  lo demás» y un rojo reservado exclusivamente para estado crítico. El rojo nunca
  identifica una categoría.
- **Nunca doble eje.** Dos magnitudes de escala distinta se resuelven con small
  multiples o indexando a una base común.
- **Denominador siempre explícito.** Cada figura declara *n*, la cohorte y la base
  de cálculo. Ningún porcentaje aparece sin la población sobre la que se calculó.
- **Accesibilidad verificada.** La paleta se validó para daltonismo (separación
  ΔE ≥ 8 entre colores adyacentes bajo simulación deutan y tritan) y la identidad
  nunca depende sólo del color.

---

## Limitaciones declaradas

- **No existe telemetría propia de reproducción.** «Atención» es un índice externo
  de popularidad, no horas vistas; «interacciones» son calificaciones emitidas, no
  sesiones. No hay variables de suscripción, dispositivo ni churn. El proyecto
  describe el rendimiento del **catálogo**, no el comportamiento de los **usuarios**.
- **Cobertura financiera parcial.** Sólo el 23,4% de las películas informa
  presupuesto y recaudación.
- **Muestra balanceada.** Válida para comparar composiciones y tasas; no lo es para
  estimar volúmenes.
- **Sin fecha real de alta en catálogo.** `date_added` cae siempre dentro del año de
  estreno, así que no se puede medir antigüedad ni velocidad de incorporación.
- **Sesgo de exposición.** La atención observada ya está influida por el propio
  motor de recomendación: un título con poca atención puede no ser malo, sino no
  haber sido mostrado.
- **Correlación no es causalidad.** Que el presupuesto se asocie a la atención no
  prueba que la produzca.

---

## Notas técnicas

- **pandas 3.x y Streamlit.** El tipo de texto respaldado por PyArrow provoca una
  falla de segmentación al construir DataFrames dentro del hilo de trabajo que
  Streamlit crea en cada re-ejecución, es decir, cada vez que se mueve un filtro.
  `src/config.py` desactiva ese backend antes de crear cualquier DataFrame. Por la
  misma razón las tablas del dashboard se renderizan como HTML en lugar de
  `st.dataframe`, que convierte a Apache Arrow.
- **Exportación a PDF.** `src/documentos.py` usa Google Chrome en modo headless. Si
  no está instalado, deja igualmente los HTML en `docs/`, que pueden imprimirse a
  PDF desde cualquier navegador.

---

## Declaración de uso de inteligencia artificial

En conformidad con la normativa de la asignatura, el equipo declara el uso de
herramientas de inteligencia artificial generativa durante el desarrollo de este
encargo.

| Herramienta | Uso dado | Verificación |
|---|---|---|
| Claude (Anthropic) | Apoyo en la exploración del conjunto de datos, revisión crítica de decisiones de diseño visual, redacción y ordenamiento del informe, y depuración del código del dashboard | Todo el análisis fue verificado ejecutando el código sobre los datos originales. Las cifras se generan desde el propio conjunto de datos, no desde la herramienta. La definición del problema, la selección de hallazgos y las recomendaciones finales son del equipo |

El equipo asume la responsabilidad íntegra por el contenido, las cifras y las
conclusiones presentadas.
