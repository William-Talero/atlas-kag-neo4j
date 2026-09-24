"""Endpoints por dimension: la misma base proyectada sobre seis ejes distintos."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from kag import dimensiones as D
from kag import grafo

router = APIRouter(prefix="/dimensiones", tags=["dimensiones"])


@router.get("")
async def catalogo() -> list[dict[str, Any]]:
    return D.catalogo()


@router.get("/{consulta_id}")
async def correr(consulta_id: str, clave: str | None = None) -> dict[str, Any]:
    try:
        return D.correr(consulta_id, clave)
    except grafo.ConsultaInvalida as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
