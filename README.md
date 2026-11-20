# Palabra del día

La palabra del día de la RAE, su definición y su traducción al inglés y al
alemán. PWA estática: sin servidor ni base de datos.

Vive en https://vitoriox.github.io/palabraria/

## Cómo funciona

- `scripts/daily.py` consulta `dle.rae.es`, traduce con MyMemory (sin clave) y
  guarda `data/latest.json`.
- `scripts/build.py` genera `dist/` para GitHub Pages.
- GitHub Actions lo ejecuta cada día a las 05:30 UTC.

## Corregir una traducción

Edita `overrides/terms.json` con el término y la definición correctos.

## Pruebas

    python -m unittest discover -s tests -v
