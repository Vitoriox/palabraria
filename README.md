# Palabra del día

Proyecto personal no oficial: palabra del día, definición y traducción
automática al inglés y al alemán. No está afiliado ni respaldado por la RAE
ni por ASALE.

Vive en https://vitoriox.github.io/palabraria/

## Cómo funciona

- `scripts/daily.py` obtiene la palabra, traduce con MyMemory y genera
  `data/latest.json` en local.
- `scripts/build.py` genera `dist/` para GitHub Pages.
- GitHub Actions ejecuta ambos pasos y despliega `dist/`; el archivo de datos
  no se guarda en Git.

## Desarrollo local

    python scripts/daily.py
    python scripts/build.py

## Pruebas

    python -m unittest discover -s tests -v

## Licencia

El código es MIT. Las definiciones del DLE no están cubiertas por esa
licencia; consulta `NOTICE`.
