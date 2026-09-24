"""Endpoints del grafo. Todo lo que devuelven trae el Cypher exacto y la latencia."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from kag import grafo
from kag.ontologia import DIMENSIONES, ETIQUETAS, RELACIONES

router = APIRouter(prefix="/grafo", tags=["grafo"])


def _proteger(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except grafo.ConsultaInvalida as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/esquema")
async def esquema() -> dict[str, Any]:
    return grafo.esquema()


@router.get("/ontologia")
async def ontologia() -> dict[str, Any]:
    return {
        "dimensiones": [{"dimension": k, **v} for k, v in DIMENSIONES.items()],
        "etiquetas": [{"etiqueta": e, "dimension": d, "campoNombre": c}
                      for e, (d, c) in ETIQUETAS.items()],
        "relaciones": [{"relacion": r, **meta} for r, meta in RELACIONES.items()],
    }


@router.get("/nodo/{clave}")
async def nodo(clave: str) -> dict[str, Any]:
    n = _proteger(grafo.nodo, clave)
    if not n:
        raise HTTPException(status_code=404, detail=f"No existe el nodo {clave}")
    return n


@router.get("/buscar")
async def buscar(q: str, limite: int = Query(15, ge=1, le=100)) -> dict[str, Any]:
    return dict(_proteger(grafo.buscar, q, limite))


@router.get("/expandir")
async def expandir(clave: str, profundidad: int = Query(1, ge=1, le=4),
                   relaciones: str | None = None,
                   limite: int = Query(220, ge=1, le=1500)) -> dict[str, Any]:
    tipos = [t for t in (relaciones or "").split(",") if t] or None
    return dict(_proteger(grafo.expandir, clave, profundidad, tipos, limite))


@router.get("/camino")
async def camino(desde: str, hasta: str,
                 max_saltos: int = Query(5, ge=1, le=8)) -> dict[str, Any]:
    return dict(_proteger(grafo.camino, desde, hasta, max_saltos))


@router.get("/subgrafo")
async def subgrafo(limite: int = Query(900, ge=10, le=6000)) -> dict[str, Any]:
    return dict(_proteger(grafo.subgrafo, limite))


@router.get("/muestra")
async def muestra(por_relacion: int = Query(10, ge=1, le=60)) -> dict[str, Any]:
    """Muestra representativa: N aristas de cada relacion de la ontologia."""
    return dict(_proteger(grafo.muestra, por_relacion))
