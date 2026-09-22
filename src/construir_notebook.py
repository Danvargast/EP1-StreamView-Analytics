"""
construir_notebook.py — Arma y ejecuta notebooks/01_analisis_exploratorio.ipynb.

El cuaderno documenta el camino completo desde los dos CSV originales hasta los
hallazgos del informe, reutilizando los mismos módulos de `src/` para que no
exista una segunda versión del cálculo.

Ejecutar:  python src/construir_notebook.py
"""

import subprocess
import sys
from pathlib import Path

import nbformat as nbf

import config as cfg

DESTINO = cfg.RAIZ / "notebooks" / "01_analisis_exploratorio.ipynb"

MD = nbf.v4.new_markdown_cell
CODE = nbf.v4.new_code_cell

celdas = [
    MD("""# Análisis exploratorio · StreamView Analytics

**Evaluación Parcial N°1 · ADY1104 Visualización de Datos**
Escuela de Informática y Telecomunicaciones · DUOC UC, Sede Los Lagos
Equipo consultor: **Felipe Ángel · Daniel Vargas**

---

### Pregunta que guía el cuaderno

> Si el presupuesto de contenido se mantuviera igual, ¿dónde habría que moverlo
> para capturar más atención y mejor satisfacción por cada dólar invertido?

Este cuaderno recorre el camino desde los dos archivos originales hasta los
hallazgos que sostienen el informe ejecutivo. Reutiliza los módulos de `src/`
—no reimplementa ningún cálculo— para que el cuaderno, el informe, el dashboard
y la presentación no puedan dar cifras distintas."""),

    CODE("""import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent / "src"))

import config as cfg      # rutas, paleta y estilo compartidos
import etl                # integración y saneamiento
import metricas as M      # todos los indicadores del proyecto
import graficos as G      # las figuras del informe

import pandas as pd
import numpy as np

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 40)
print("Proyecto:", cfg.RAIZ.name)"""),

    MD("""## 1. Las fuentes en crudo

Antes de integrar nada conviene mirar qué llega. Dos archivos, mismo esquema
salvo la capa financiera, que sólo existe para películas."""),

    CODE("""peliculas = pd.read_csv(cfg.CSV_PELICULAS)
series = pd.read_csv(cfg.CSV_SERIES)

print(f"Películas: {peliculas.shape[0]:,} filas × {peliculas.shape[1]} columnas")
print(f"Series:    {series.shape[0]:,} filas × {series.shape[1]} columnas")
print("\\nSólo en películas:", sorted(set(peliculas.columns) - set(series.columns)))
peliculas.head(3)"""),

    MD("""## 2. Cuatro trampas en los datos

Las cuatro observaciones siguientes cambian por completo lo que se puede
graficar. Encontrarlas antes de dibujar evita construir un gráfico
conceptualmente incorrecto."""),

    MD("""### 2.1 `rating` es una copia exacta de `vote_average`

Dos columnas con la misma información inflan artificialmente el esquema y
pueden llevar a contar dos veces la misma variable en una matriz de
correlación."""),

    CODE("""for nombre, df in [("películas", peliculas), ("series", series)]:
    print(f"{nombre:<12} coincidencia rating == vote_average: "
          f"{(df.rating == df.vote_average).mean():.1%}")"""),

    MD("""### 2.2 La muestra está balanceada por diseño

Exactamente 1.000 títulos por año en cada archivo. **Cualquier gráfico de
volumen en el tiempo sería una línea plana por construcción** y no diría nada
sobre el negocio. Sólo se pueden leer composiciones y tasas dentro de cada
año."""),

    CODE("""conteo = pd.DataFrame({
    "Películas": peliculas.release_year.value_counts().sort_index(),
    "Series": series.release_year.value_counts().sort_index(),
})
print(conteo.T.to_string())
print("\\n¿Todos los años tienen exactamente 1.000 títulos?",
      bool((conteo == 1000).all().all()))"""),

    MD("""### 2.3 El 0 en presupuesto y recaudación significa «no informado»

Si se dejara como 0, el promedio de presupuesto caería a menos de un tercio de
su valor real y aparecerían películas «gratis» con recaudaciones millonarias."""),

    CODE("""print(f"budget  == 0: {(peliculas.budget == 0).mean():.1%}")
print(f"revenue == 0: {(peliculas.revenue == 0).mean():.1%}")

con_datos = peliculas[(peliculas.budget > 0) & (peliculas.revenue > 0)]
print(f"\\nPresupuesto medio contando los ceros : USD {peliculas.budget.mean():,.0f}")
print(f"Presupuesto medio sin los ceros       : USD {con_datos.budget.mean():,.0f}")"""),

    MD("""### 2.4 Sin nota no es lo mismo que mala nota

Cuando `vote_count = 0`, la nota también vale 0. Esos títulos no tienen una
evaluación pésima: **no tienen evaluación**. Incluirlos en un promedio de
satisfacción arrastra la media hacia abajo por una razón que no existe."""),

    CODE("""sin_votos = series.vote_count == 0
print(f"Series sin ninguna calificación: {sin_votos.sum():,} ({sin_votos.mean():.1%})")
print(f"De ellas, con nota 0: {(series.loc[sin_votos, 'vote_average'] == 0).sum():,}")

# Caso borde: unos pocos registros traen nota sin ningún voto que la respalde.
# Es una nota huérfana y el ETL la descarta junto con el resto de `sin_senal`.
huerfanas = sin_votos & (series.vote_average != 0)
print(f"Notas huérfanas (0 votos pero nota distinta de 0): {huerfanas.sum()}")

print(f"\\nNota media contando los ceros : {series.vote_average.mean():.2f}")
print(f"Nota media sólo con votos     : {series.loc[~sin_votos, 'vote_average'].mean():.2f}")
print("\\nLa diferencia de 1,6 puntos no refleja ninguna caída de calidad:")
print("es el efecto de tratar 'sin evaluación' como si fuera 'evaluación pésima'.")"""),

    MD("""### 2.5 La cohorte 2025 todavía no es comparable

Sus títulos no han tenido tiempo de acumular interacciones. Mezclarla con el
resto haría parecer que el catálogo empeoró de golpe."""),

    CODE("""todo = pd.concat([peliculas.assign(formato="Película"),
                  series.assign(formato="Serie")], ignore_index=True)
por_anio = (todo.assign(sin_votos=todo.vote_count == 0)
            .groupby("release_year").sin_votos.mean() * 100).round(1)
print(por_anio.to_string())"""),

    MD("""## 3. Integración y saneamiento

Las siete decisiones de saneamiento están documentadas en `src/etl.py`. Aquí
sólo se ejecuta el proceso y se revisa el resultado."""),

    CODE("""catalogo = etl.construir_catalogo()
print(f"Catálogo integrado: {catalogo.shape[0]:,} filas × {catalogo.shape[1]} columnas\\n")
etl.auditoria(catalogo)"""),

    CODE("""catalogo[["id_titulo", "formato", "titulo", "anio", "idioma_original",
          "segmento", "atencion", "interacciones", "satisfaccion",
          "sin_senal", "roi"]].head(8)"""),

    MD("""A partir de aquí se trabaja sobre la **cohorte madura** (2010–2024), que es la
base de todas las cifras del informe."""),

    CODE("""maduras = M.cargar(solo_maduras=True)
kpis = M.kpis(maduras)
for clave, valor in kpis.items():
    print(f"  {clave:<26} {valor:,.2f}" if isinstance(valor, float)
          else f"  {clave:<26} {valor:,}")"""),

    MD("""## 4. Hallazgo 1 · La atención está extremadamente concentrada

El índice de Gini y la curva de Lorenz son la forma estándar de medir
desigualdad en una distribución. Aplicados a la atención muestran que el
tamaño del catálogo no es una medida de salud."""),

    CODE("""for pct in (1, 5, 10, 20, 50):
    print(f"  El {pct:>2}% de los títulos concentra "
          f"{M.atencion_en_top(maduras, pct):.1f}% de la atención")
print(f"\\n  Índice de Gini de la atención: {M.gini(maduras.atencion):.3f}")
print(f"  Índice de Gini de las interacciones: {M.gini(maduras.interacciones):.3f}")"""),

    MD("""## 5. Hallazgo 2 · El formato es la variable que más explica el rendimiento

Se usa la **mediana** y no el promedio: la distribución de atención tiene cola
larga y unos pocos estrenos masivos desplazarían la media."""),

    CODE("""con_senal = maduras[~maduras.sin_senal]

resumen_formato = pd.DataFrame({
    "Títulos": maduras.groupby("formato").size(),
    "Atención mediana": maduras.groupby("formato").atencion.median(),
    "Atención promedio": maduras.groupby("formato").atencion.mean(),
    "Nota mediana": con_senal.groupby("formato").satisfaccion.median(),
    "Catálogo invisible %": maduras.groupby("formato").sin_senal.mean() * 100,
}).round(2)
print(resumen_formato.to_string())

multiplo = (resumen_formato.loc["Serie", "Atención mediana"]
            / resumen_formato.loc["Película", "Atención mediana"])
print(f"\\nUna serie capta {multiplo:.1f} veces la atención de una película.")
print("Nótese la diferencia entre mediana y promedio: por eso no se usa el promedio.")"""),

    MD("""### El formato que más rinde es también el más riesgoso

Una de cada cinco series no registra ninguna interacción. La recomendación no
puede ser «comprar series» sin más: hay que comprarlas con un filtro de
riesgo."""),

    CODE("""M.por_segmento(maduras)"""),

    CODE("""# Dentro de las series, el idioma modula el riesgo más que el techo de rendimiento
solo_series = maduras[maduras.formato == "Serie"]
por_idioma = (solo_series.groupby("idioma_original")
              .agg(titulos=("titulo", "size"),
                   atencion=("atencion", "median"),
                   invisible_pct=("sin_senal", lambda s: s.mean() * 100)))
por_idioma["nota"] = (solo_series[~solo_series.sin_senal]
                      .groupby("idioma_original").satisfaccion.median())
por_idioma.query("titulos >= 300").sort_values("invisible_pct").round(2)"""),

    MD("""Los idiomas de la parte superior de la tabla —bajo porcentaje de catálogo
invisible con atención y nota altas— son los candidatos naturales para
concentrar la inversión. Los del final exigen un piloto antes de comprometer
presupuesto."""),

    MD("""## 6. Hallazgo 3 · Hay inventario pagado que nadie ve

Cruzar atención y satisfacción sobre sus medianas convierte un conjunto de
30.000 títulos en cuatro decisiones distintas."""),

    CODE("""puntos, umbral_atencion, umbral_nota = M.cuadrantes(maduras)
print(f"Umbrales (medianas de la cohorte): atención {umbral_atencion:.2f} · "
      f"nota {umbral_nota:.2f}\\n")
M.resumen_cuadrantes(maduras)"""),

    CODE("""# Ejemplos del cuadrante que abre la oportunidad más barata
(puntos.query("cuadrante == 'Joyas ocultas'")
       .nlargest(10, "satisfaccion")
       [["titulo", "formato", "anio", "idioma_original",
         "atencion", "interacciones", "satisfaccion"]])"""),

    MD("""## 7. Hallazgo 4 · El dinero está en el tramo equivocado

Sólo una parte de las películas informa presupuesto y recaudación, de modo que
las conclusiones financieras aplican a ese subconjunto y así se declara en el
informe."""),

    CODE("""cobertura = maduras.roi.notna().sum() / (maduras.formato == "Película").sum()
print(f"Películas con ROI calculable: {maduras.roi.notna().sum():,} "
      f"({cobertura:.1%} de las películas)\\n")
M.rentabilidad(maduras)"""),

    MD("""El tramo de 1 a 10 millones de dólares es el que más presupuesto moviliza y el
que peor retorno entrega. Y subir el presupuesto tampoco mejora la nota:"""),

    CODE("""M.correlaciones(maduras)"""),

    CODE("""fin = maduras[maduras.roi.notna()].copy()
fin["decil"] = pd.qcut(fin.budget, 10, labels=range(1, 11))
evolucion = fin.groupby("decil", observed=True).agg(
    presupuesto_mediano=("budget", "median"),
    atencion=("atencion", "median"),
    nota=("satisfaccion", "median"))
indexado = (evolucion[["atencion", "nota"]] / evolucion[["atencion", "nota"]].iloc[0] * 100)
evolucion.join(indexado, rsuffix="_indice").round(1)"""),

    MD("""Del decil más barato al más caro la atención se multiplica por más de cinco y
la nota se mueve apenas tres puntos de índice. **El presupuesto compra
visibilidad, no agrado.**

Ambas series se indexan a base 100 porque miden en unidades distintas: un
gráfico de doble eje inventaría una correlación que los datos no tienen."""),

    MD("""## 8. Generación de las figuras del informe

Las ocho figuras se producen con el mismo módulo que usa el informe, de modo
que lo que se ve aquí es exactamente lo que se entrega."""),

    CODE("""G.generar_todo()"""),

    MD("""## 9. Síntesis

| Paso | Contenido |
|---|---|
| **Situación** | La inversión en contenido se decide por volumen, no por rendimiento. |
| **Hallazgo** | La atención está concentrada, una parte del catálogo no llega a nadie y el formato serie rinde varias veces más que la película. |
| **Implicancia** | Miles de millones están en el tramo de películas de peor retorno, y más presupuesto no mejora la satisfacción. |
| **Acción** | Reasignar ese tramo a series con filtro de riesgo, activar las joyas ocultas, instalar una puerta de 90 días e instrumentar telemetría propia. |

### Lo que estos datos **no** permiten afirmar

No existe telemetría propia de reproducción: «atención» es un índice externo de
popularidad, no horas vistas, y no hay variables de suscripción, dispositivo ni
churn. El análisis describe el rendimiento del **catálogo**, no el
comportamiento de los **usuarios**.

---

### Declaración de uso de inteligencia artificial

Se utilizó **Claude (Anthropic)** como apoyo en la exploración del conjunto de
datos, la revisión crítica de decisiones de diseño visual, la redacción del
informe y la depuración del código. Todas las cifras se calculan desde el
conjunto de datos original mediante el código de este proyecto y fueron
verificadas por el equipo, que asume la responsabilidad íntegra del contenido."""),
]


def construir():
    nb = nbf.v4.new_notebook(cells=celdas)
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]},
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, DESTINO)
    print(f"  ✓ {DESTINO.relative_to(cfg.RAIZ)} ({len(celdas)} celdas)")


def ejecutar():
    """Ejecuta el cuaderno en su propia carpeta para dejar las salidas guardadas."""
    orden = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
             "--execute", "--inplace", "--ExecutePreprocessor.timeout=600",
             str(DESTINO)]
    r = subprocess.run(orden, capture_output=True, text=True, cwd=DESTINO.parent)
    if r.returncode == 0:
        print("  ✓ cuaderno ejecutado con las salidas guardadas")
    else:
        print("  ! no se pudo ejecutar el cuaderno:\n", r.stderr[-1200:])
    return r.returncode == 0


if __name__ == "__main__":
    construir()
    ejecutar()
