"""Punto de entrada del generador.

Existe para que `seed_kag` se importe siempre como modulo y no como `__main__`:
si se ejecutara directamente, `seed_casos` cargaria una segunda copia del modulo
con su propio estado y las listas compartidas llegarian vacias.
"""

from __future__ import annotations

import seed_kag

if __name__ == "__main__":
    raise SystemExit(seed_kag.main())
