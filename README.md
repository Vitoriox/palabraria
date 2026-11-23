# Palabra del día

La palabra del día de la RAE, su definición y su traducción al inglés y al
alemán. PWA estática: sin servidor ni base de datos.

Vive en https://vitoriox.github.io/palabraria/

## Cómo funciona

- `scripts/daily.py` consulta `dle.rae.es`, traduce con MyMemory (sin clave) y
  guarda `data/latest.json`.
- `scripts/build.py` genera `dist/` para GitHub Pages.
- GitHub Actions lo ejecuta cada día a las 01:00 de Madrid (CET/CEST).

## Pruebas

    python -m unittest discover -s tests -v
