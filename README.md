# Palabra del día

Proyecto personal no oficial que muestra la palabra del día publicada por la
RAE, su definición y una traducción automática al inglés y al alemán. PWA
estática: sin servidor ni base de datos.

No está afiliado ni respaldado por la Real Academia Española (RAE) ni por la
Asociación de Academias de la Lengua Española (ASALE). La definición procede
del *Diccionario de la lengua española* (RAE-ASALE); las traducciones son
automáticas y pueden contener errores. Consulta `NOTICE` para los
derechos sobre el contenido.

Vive en https://vitoriox.github.io/palabraria/

## Aviso

El código de este repositorio se distribuye bajo la licencia MIT. Las
definiciones del DLE no están cubiertas por esa licencia y siguen siendo
titularidad de la RAE y de ASALE.

## Cómo funciona

- `scripts/daily.py` consulta `dle.rae.es`, traduce con MyMemory (sin clave) y
  guarda `data/latest.json`.
- `scripts/build.py` genera `dist/` para GitHub Pages.
- GitHub Actions lo ejecuta cada día a las 02:00 CET (03:00 CEST en verano).

## Pruebas

    python -m unittest discover -s tests -v
