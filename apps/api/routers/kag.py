"""Endpoints KAG: recuperacion fusionada, linea base RAG y catalogo de preguntas."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from kag import grafo, preguntas, recuperador, vector

router = APIRouter(prefix="/kag", tags=["kag"])


class Consulta(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)
    ancla: str | None = None
    profundidad: int = Field(2, ge=1, le=4)
    k: int = Field(8, ge=1, le=30)
    relaciones: list[str] | None = None
    dimensiones: list[str] | None = None
    enfocado: bool = True


@router.get("/preguntas")
async def catalogo() -> list[dict[str, Any]]:
    return preguntas.catalogo()


@router.post("/responder")
async def responder(c: Consulta) -> dict[str, Any]:
    try:
        return recuperador.responder(
            c.pregunta, c.ancla, c.profundidad, c.k, c.relaciones, c.dimensiones,
            c.enfocado)
    except grafo.ConsultaInvalida as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pregunta/{pregunta_id}")
async def por_id(pregunta_id: str, k: int = Query(8, ge=1, le=30),
                 enfocado: bool = True) -> dict[str, Any]:
    p = preguntas.buscar(pregunta_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"No existe la pregunta {pregunta_id}")
    res = recuperador.responder(p["pregunta"], p["ancla"], p["profundidad"], k,
                                enfocado=enfocado)
    return {"ficha": p, **res}


@router.get("/vectorial")
async def vectorial(q: str, k: int = Query(8, ge=1, le=50)) -> dict[str, Any]:
    """Linea base RAG sin grafo. Es el termino de comparacion."""
    return vector.buscar(q, k)


@router.get("/estado")
async def estado() -> dict[str, Any]:
    return vector.estado()
