"""
etl.py — Integración y saneamiento de las dos fuentes corporativas.

Entrada : data/raw/netflix_movies_detailed_up_to_2025.csv   (16.000 filas, 18 col.)
          data/raw/netflix_tv_shows_detailed_up_to_2025.csv (16.000 filas, 16 col.)
Salida  : data/processed/catalogo_integrado.csv
          data/processed/diccionario_datos.csv
          data/processed/auditoria_calidad.csv

Decisiones de saneamiento (todas documentadas, ninguna silenciosa):

  D1. `rating` es copia exacta de `vote_average` (coincidencia 100%). Se elimina.
  D2. `duration` está vacía en el 100% de las películas y vale la constante
      "1 Seasons" en el 100% de las series. No aporta varianza: se elimina.
  D3. `date_added` cae siempre dentro del año de `release_year` (coincidencia
      100%), por lo que NO representa la fecha real de incorporación al
      catálogo. Se conserva sólo como fecha de referencia y se prohíbe su uso
      para medir antigüedad en catálogo.
  D4. `budget` y `revenue` traen 0 donde el dato no fue informado
      (69,7% y 64,7%). El 0 se convierte en nulo: un 0 real haría creer que la
      película no costó nada y contaminaría cualquier promedio.
  D5. `vote_count = 0` viene acompañado de `vote_average = 0`. Esos títulos NO
      tienen nota mala: no tienen nota. Se marcan con `sin_senal = True` y su
      satisfacción pasa a nulo, de modo que quedan excluidos de todo promedio.
      Caso borde: 13 series traen una nota sin ningún voto que la respalde
      (nota huérfana); la regla también las descarta, que es lo correcto.
  D6. 9 `show_id` duplicados en series: se conserva la primera aparición.
  D7. Cada archivo trae exactamente 1.000 títulos por año (2010–2025). El
      conjunto es una MUESTRA BALANCEADA, no el catálogo completo. Se marca con
      `muestra_balanceada = True` para impedir lecturas de volumen en el tiempo.

Ejecutar:  python src/etl.py
"""

import numpy as np
import pandas as pd

import config as cfg

COLUMNAS_COMUNES = [
    "show_id", "title", "director", "cast", "country", "date_added",
    "release_year", "genres", "language", "description",
    "popularity", "vote_count", "vote_average",
]


def _cargar_fuente(ruta, formato):
    df = pd.read_csv(ruta)
    df["formato"] = formato
    return df


def construir_catalogo(guardar=True):
    """Integra ambas fuentes en un único catálogo saneado y lo devuelve."""
    pel = _cargar_fuente(cfg.CSV_PELICULAS, "Película")
    ser = _cargar_fuente(cfg.CSV_SERIES, "Serie")

    # D1 — verificación explícita antes de descartar la columna redundante
    for nombre, df in (("películas", pel), ("series", ser)):
        coincidencia = (df["rating"] == df["vote_average"]).mean()
        assert coincidencia == 1.0, f"`rating` ya no es copia de `vote_average` en {nombre}"

    # Presupuesto y recaudación sólo existen en películas (D4)
    pel_fin = pel[["show_id", "budget", "revenue"]].copy()
    pel_fin["budget"] = pel_fin["budget"].replace(0, np.nan)
    pel_fin["revenue"] = pel_fin["revenue"].replace(0, np.nan)

    cat = pd.concat(
        [pel[COLUMNAS_COMUNES + ["formato"]], ser[COLUMNAS_COMUNES + ["formato"]]],
        ignore_index=True,
    )

    # D6 — el identificador sólo es único dentro de cada fuente
    cat = cat.drop_duplicates(subset=["formato", "show_id"], keep="first")
    cat["id_titulo"] = cat["formato"].str[:3].str.upper() + "-" + cat["show_id"].astype(str)

    # D3 — fecha de referencia, nunca fecha de alta en catálogo
    cat["fecha_referencia"] = pd.to_datetime(cat["date_added"], errors="coerce")
    cat = cat.drop(columns=["date_added"])

    # D5 — separar "sin nota" de "nota baja"
    cat["sin_senal"] = cat["vote_count"] == 0
    cat.loc[cat["sin_senal"], "vote_average"] = np.nan

    # Variables derivadas de negocio
    cat["idioma_original"] = cat["language"].fillna("desconocido")
    cat["es_no_ingles"] = cat["idioma_original"].ne("en")
    cat["bloque_idioma"] = np.where(cat["es_no_ingles"], "No inglés", "Inglés")
    cat["pais_principal"] = (
        cat["country"].fillna("Sin informar").str.split(",").str[0].str.strip()
    )
    cat["genres"] = cat["genres"].fillna("Sin clasificar")
    cat["genero_principal"] = cat["genres"].str.split(",").str[0].str.strip()
    cat["cohorte_madura"] = cat["release_year"] <= cfg.ANIO_CIERRE  # D7 / 2025 parcial
    cat["muestra_balanceada"] = True

    # Segmento de negocio: la unidad sobre la que se decide el presupuesto
    cat["segmento"] = cat["formato"] + " · " + cat["bloque_idioma"]

    # Anexar la capa financiera (sólo películas; series quedan en nulo por diseño)
    cat = cat.merge(pel_fin, how="left", on="show_id")
    cat.loc[cat["formato"] == "Serie", ["budget", "revenue"]] = np.nan
    cat["roi"] = cat["revenue"] / cat["budget"]

    cat = cat.rename(columns={
        "title": "titulo",
        "country": "pais",
        "release_year": "anio",
        "genres": "generos",
        "popularity": "atencion",       # proxy de interés/engagement
        "vote_count": "interacciones",  # nº de calificaciones emitidas
        "vote_average": "satisfaccion",  # nota media (0–10)
    })

    orden = [
        "id_titulo", "formato", "titulo", "anio", "fecha_referencia",
        "pais_principal", "pais", "idioma_original", "bloque_idioma", "es_no_ingles",
        "genero_principal", "generos", "segmento",
        "atencion", "interacciones", "satisfaccion", "sin_senal",
        "budget", "revenue", "roi",
        "cohorte_madura", "muestra_balanceada", "director", "cast", "description",
    ]
    cat = cat[orden].sort_values(["anio", "formato", "titulo"]).reset_index(drop=True)

    if guardar:
        cat.to_csv(cfg.CATALOGO, index=False)
        _diccionario().to_csv(cfg.DIR_PROC / "diccionario_datos.csv", index=False)
        auditoria(cat).to_csv(cfg.DIR_PROC / "auditoria_calidad.csv", index=False)

    return cat


def _diccionario():
    filas = [
        ("id_titulo", "texto", "Identificador único (formato + show_id de origen)", "Derivada"),
        ("formato", "categórica", "Película o Serie", "Ambas fuentes"),
        ("titulo", "texto", "Nombre del contenido", "Ambas fuentes"),
        ("anio", "temporal", "Año de estreno (2010–2025)", "release_year"),
        ("fecha_referencia", "temporal", "Fecha dentro del año de estreno. NO es la fecha de alta en catálogo", "date_added"),
        ("pais_principal", "categórica", "Primer país listado en la coproducción", "country"),
        ("idioma_original", "categórica", "Código ISO del idioma original", "language"),
        ("bloque_idioma", "categórica", "Inglés / No inglés", "Derivada"),
        ("genero_principal", "categórica", "Primer género declarado", "genres"),
        ("segmento", "categórica", "Formato × bloque de idioma: unidad de decisión presupuestaria", "Derivada"),
        ("atencion", "cuantitativa continua", "Índice de popularidad (proxy de interés/engagement)", "popularity"),
        ("interacciones", "cuantitativa discreta", "Nº de calificaciones emitidas por la audiencia", "vote_count"),
        ("satisfaccion", "cuantitativa continua", "Nota media 0–10. Nula si no hay interacciones", "vote_average"),
        ("sin_senal", "booleana", "True si el título no registra ninguna interacción", "Derivada"),
        ("budget", "cuantitativa continua", "Presupuesto en USD. Sólo películas. 0 → nulo", "budget"),
        ("revenue", "cuantitativa continua", "Recaudación en USD. Sólo películas. 0 → nulo", "revenue"),
        ("roi", "cuantitativa continua", "revenue / budget. 1,0 = punto de equilibrio", "Derivada"),
        ("cohorte_madura", "booleana", "True para 2010–2024. 2025 se excluye de tendencias", "Derivada"),
        ("muestra_balanceada", "booleana", "Marca que el conjunto tiene 1.000 títulos por año por diseño", "Derivada"),
    ]
    return pd.DataFrame(filas, columns=["variable", "naturaleza", "descripcion", "origen"])


def auditoria(cat):
    """Tabla de control de calidad que se publica junto al informe.

    Funciona también sobre un subconjunto filtrado, por eso los denominadores
    se protegen: una selección sin películas dejaría la cobertura financiera
    sin base de cálculo.
    """
    n = len(cat)
    n_pel = max(1, int((cat.formato == "Película").sum()))
    hay_pel = (cat.formato == "Película").any()
    filas = [
        ("Registros integrados", n, "100%"),
        ("Películas", int((cat.formato == "Película").sum()), f"{(cat.formato=='Película').mean()*100:.1f}%"),
        ("Series", int((cat.formato == "Serie").sum()), f"{(cat.formato=='Serie').mean()*100:.1f}%"),
        ("Títulos sin ninguna interacción", int(cat.sin_senal.sum()), f"{cat.sin_senal.mean()*100:.1f}%"),
        ("Títulos sin género declarado", int((cat.genero_principal == "Sin clasificar").sum()),
         f"{(cat.genero_principal=='Sin clasificar').mean()*100:.1f}%"),
        ("Títulos sin país informado", int((cat.pais_principal == "Sin informar").sum()),
         f"{(cat.pais_principal=='Sin informar').mean()*100:.1f}%"),
        ("Películas con presupuesto informado", int(cat.budget.notna().sum()),
         f"{cat.budget.notna().sum()/n_pel*100:.1f}% de las películas" if hay_pel
         else "sin películas en la selección"),
        ("Películas con ROI calculable", int(cat.roi.notna().sum()),
         f"{cat.roi.notna().sum()/n_pel*100:.1f}% de las películas" if hay_pel
         else "sin películas en la selección"),
        ("Cohorte 2025 (parcial, excluida de tendencias)", int((cat.anio == 2025).sum()),
         f"{(cat.anio==2025).mean()*100:.1f}%"),
    ]
    return pd.DataFrame(filas, columns=["control", "n", "cobertura"])


if __name__ == "__main__":
    catalogo = construir_catalogo()
    print(f"Catálogo integrado: {catalogo.shape[0]:,} filas × {catalogo.shape[1]} columnas")
    print(f"Guardado en: {cfg.CATALOGO}")
    print()
    print(auditoria(catalogo).to_string(index=False))
