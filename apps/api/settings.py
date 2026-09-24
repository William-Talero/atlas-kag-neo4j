"""Configuracion tipada del proyecto Neo4j."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")


class Settings(TypedDict):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_DB: str
    EMBED_DIM: int
    DEMO_MODE: Literal["live", "offline"]
    RAIZ: Path
    DATA: Path


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    modo = os.getenv("DEMO_MODE", "offline").strip().lower()
    return Settings(
        NEO4J_URI=os.getenv("NEO4J_URI", "bolt://localhost:7687").strip(),
        NEO4J_USER=os.getenv("NEO4J_USER", "neo4j"),
        NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD", ""),
        NEO4J_DB=os.getenv("NEO4J_DB", "neo4j"),
        EMBED_DIM=int(os.getenv("EMBED_DIM", "256")),
        DEMO_MODE=modo if modo in ("live", "offline") else "offline",  # type: ignore[arg-type]
        RAIZ=RAIZ,
        DATA=RAIZ / "data",
    )


def host_enmascarado(uri: str) -> str:
    """Oculta el host manteniendo el esquema y el puerto, para mostrarlo en la UI."""
    if not uri:
        return ""
    esquema, _, resto = uri.partition("://")
    host, _, puerto = resto.partition(":")
    partes = host.split(".")
    if partes and len(partes[0]) > 4:
        partes[0] = partes[0][:3] + "•" * (len(partes[0]) - 3)
    visible = ".".join(partes)
    return f"{esquema}://{visible}" + (f":{puerto}" if puerto else "")
