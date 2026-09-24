"""ATLAS · KAG sobre Neo4j."""

from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Thread
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kag import grafo as motor_grafo
from kag.conexion import cerrar, ping
from kag.ontologia import DIMENSIONES, ETIQUETAS, RELACIONES
from kag.vector import INDICE
from routers import dimensiones, grafo, kag
from settings import host_enmascarado, load_settings


def _precalentar() -> None:
    """La muestra del grafo cuesta segundos y no cambia: se deja lista antes de
    que el navegador la pida."""
    try:
        motor_grafo.muestra()
    except Exception:
        pass


@asynccontextmanager
async def ciclo(_: FastAPI):
    Thread(target=_precalentar, daemon=True).start()
    yield
    cerrar()


app = FastAPI(title="ATLAS · KAG multidimensional (Neo4j)", version="1.0.0",
              lifespan=ciclo)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grafo.router)
app.include_router(kag.router)
app.include_router(dimensiones.router)


def _motor() -> dict[str, Any]:
    s = load_settings()
    estado = ping()
    return {
        "motor": "Neo4j · Cypher nativo",
        "host": host_enmascarado(s["NEO4J_URI"]),
        "base": s["NEO4J_DB"],
        "grafo": s["NEO4J_DB"],
        "autenticacion": "usuario y contraseña",
        "modelo": {
            "dimensiones": len(DIMENSIONES),
            "etiquetas": len(ETIQUETAS),
            "relaciones": len(RELACIONES),
        },
        "componentes": [
            {"etiqueta": "Neo4j", "valor": estado.get("version", "—")},
            {"etiqueta": "edición", "valor": estado.get("edicion", "—")},
            {"etiqueta": "índice vectorial", "valor": INDICE},
        ],
        "conectado": estado.get("ok", False),
        "error": estado.get("error", ""),
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"estado": "ok", "motor": _motor()}


@app.get("/motor")
async def motor() -> dict[str, Any]:
    return _motor()
