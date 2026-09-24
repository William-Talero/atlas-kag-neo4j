"""Conexion a Neo4j.

El contraste con la version AGE es casi todo lo que no hay que hacer aqui: el
driver mantiene el pool, los parametros viajan como parametros nativos de Cypher
y los nodos llegan como objetos, no como texto con sufijo de tipo.
"""

from __future__ import annotations

import threading
from typing import Any

from neo4j import Driver, GraphDatabase

from settings import load_settings

_lock = threading.Lock()
_driver: Driver | None = None


def obtener_driver() -> Driver:
    global _driver
    with _lock:
        if _driver is None:
            s = load_settings()
            _driver = GraphDatabase.driver(
                s["NEO4J_URI"],
                auth=(s["NEO4J_USER"], s["NEO4J_PASSWORD"]),
                max_connection_pool_size=16,
                connection_timeout=20,
            )
        return _driver


def correr(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    s = load_settings()
    registros, _, _ = obtener_driver().execute_query(
        cypher, parameters_=params or {}, database_=s["NEO4J_DB"])
    return [r.data() for r in registros]


def correr_crudo(cypher: str, params: dict[str, Any] | None = None) -> list[Any]:
    """Devuelve los registros sin aplanar, para conservar nodos y relaciones."""
    s = load_settings()
    registros, _, _ = obtener_driver().execute_query(
        cypher, parameters_=params or {}, database_=s["NEO4J_DB"])
    return list(registros)


def cerrar() -> None:
    global _driver
    with _lock:
        if _driver is not None:
            _driver.close()
            _driver = None


def ping() -> dict[str, Any]:
    try:
        obtener_driver().verify_connectivity()
        fila = correr(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name AS nombre, versions[0] AS version, edition AS edicion")[0]
        indices = correr(
            "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN count(*) AS n")
        return {
            "ok": True,
            "producto": fila["nombre"],
            "version": fila["version"],
            "edicion": fila["edicion"],
            "indices_vectoriales": indices[0]["n"] if indices else 0,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
