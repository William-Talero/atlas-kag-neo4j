"""Recuperacion vectorial sobre el indice nativo de Neo4j.

El contraste con la version PostgreSQL esta en como se expresa la restriccion:

    pgvector ->  WHERE entidades && $claves_del_subgrafo::text[]
    Neo4j    ->  MATCH (f:Fragmento)-[:MENCIONA]->(n) WHERE n.clave IN $claves

En pgvector la pertenencia al subgrafo hay que materializarla en una columna de
arreglo y mantenerla sincronizada con el grafo. Aqui es el propio patron, asi que
no puede quedar desfasada.

El precio: el indice vectorial nativo (`db.index.vector.queryNodes`) no acepta un
filtro previo, igual que HNSW en pgvector. Para la busqueda restringida se
recorre el patron y se calcula la similitud con `vector.similarity.cosine`, que
es exacta y barata porque el grafo ya redujo el conjunto.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from kag.conexion import correr
from kag.embeddings import Embebedor, es_nulo
from settings import load_settings

INDICE = "fragmento_embedding"

SIN_VOCABULARIO = ("Ningún término de la consulta está en el vocabulario del "
                   "corpus: la búsqueda vectorial no puede opinar.")


@lru_cache(maxsize=1)
def embebedor() -> Embebedor:
    return Embebedor.cargar(load_settings()["DATA"] / "embeddings.npz")


def _extracto(texto: str, limite: int = 320) -> str:
    t = (texto or "").strip()
    return t if len(t) <= limite else t[:limite].rsplit(" ", 1)[0] + "…"


def _coseno(score: float) -> float:
    """Neo4j normaliza el coseno a [0,1] con (1 + cos) / 2; pgvector devuelve el
    coseno crudo. Se deshace la normalizacion para que las dos implementaciones
    reporten el mismo numero y los pesos de fusion signifiquen lo mismo."""
    return 2.0 * float(score) - 1.0


def _fila(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "clave": f["clave"], "documento": f["documento"], "titulo": f["titulo"],
        "extracto": _extracto(f["texto"]), "dimension": f["dimension"],
        "entidades": list(f["entidades"] or []),
        "similitud": round(_coseno(f["score"]), 4),
    }


CYPHER_RAG = (
    "CALL db.index.vector.queryNodes($indice, $k, $consulta) YIELD node AS f, score "
    "RETURN f.clave AS clave, f.documento AS documento, f.titulo AS titulo, "
    "       f.texto AS texto, f.dimension AS dimension, f.entidades AS entidades, "
    "       score"
)

CYPHER_KAG = (
    "MATCH (f:Fragmento)-[:MENCIONA]->(n) WHERE n.clave IN $claves "
    "WITH DISTINCT f "
    "WITH f, vector.similarity.cosine(f.embedding, $consulta) AS score "
    "RETURN f.clave AS clave, f.documento AS documento, f.titulo AS titulo, "
    "       f.texto AS texto, f.dimension AS dimension, f.entidades AS entidades, "
    "       score "
    "ORDER BY score DESC LIMIT $k"
)


def buscar(consulta: str, k: int = 8) -> dict[str, Any]:
    """Linea base RAG: el indice vectorial sobre todo el corpus."""
    k = max(1, min(int(k), 60))
    crudo = embebedor().vector(consulta)
    if es_nulo(crudo):
        return {"modo": "rag", "consulta": consulta, "resultados": [],
                "degenerado": True, "nota": SIN_VOCABULARIO, "ms": 0.0, "sql": ""}
    v = [float(x) for x in crudo]
    t0 = time.perf_counter()
    filas = correr(CYPHER_RAG, {"indice": INDICE, "k": k, "consulta": v})
    return {
        "modo": "rag", "consulta": consulta,
        "resultados": [_fila(f) for f in filas],
        "ms": round((time.perf_counter() - t0) * 1000, 2),
        "sql": CYPHER_RAG,
    }


def buscar_en_subgrafo(consulta: str, claves: list[str], k: int = 8) -> dict[str, Any]:
    """KAG: la misma similitud, restringida a lo que el grafo demostro conexo."""
    k = max(1, min(int(k), 60))
    crudo = embebedor().vector(consulta)
    if es_nulo(crudo):
        return {"modo": "kag", "consulta": consulta, "resultados": [],
                "degenerado": True, "nota": SIN_VOCABULARIO,
                "anclas": len(claves), "ms": 0.0, "sql": ""}
    v = [float(x) for x in crudo]
    t0 = time.perf_counter()
    filas = correr(CYPHER_KAG, {"claves": list(claves), "consulta": v, "k": k})
    return {
        "modo": "kag", "consulta": consulta,
        "resultados": [_fila(f) for f in filas],
        "anclas": len(claves),
        "ms": round((time.perf_counter() - t0) * 1000, 2),
        "sql": CYPHER_KAG,
    }


def cobertura(claves: list[str]) -> dict[str, Any]:
    fila = correr(
        "MATCH (f:Fragmento) WITH count(f) AS corpus "
        "MATCH (g:Fragmento)-[:MENCIONA]->(n) WHERE n.clave IN $claves "
        "WITH corpus, count(DISTINCT g) AS alcanzados "
        "RETURN corpus, alcanzados", {"claves": list(claves)})
    if not fila:
        return {"corpus": 0, "alcanzados": 0, "reduccion": 0.0}
    corpus, alcanzados = fila[0]["corpus"], fila[0]["alcanzados"]
    return {
        "corpus": corpus, "alcanzados": alcanzados,
        "reduccion": round((1 - alcanzados / corpus) * 100, 1) if corpus else 0.0,
    }


def documentos_que_relacionan(claves: list[str]) -> list[str]:
    """Fragmentos que mencionan a la vez TODAS las claves dadas.

    Cuando devuelve cero, la relacion existe como aristas y no fue redactada en
    ningun documento: es la prueba de por que el vector solo no alcanza.
    """
    if len(claves) < 2:
        return []
    filas = correr(
        "MATCH (f:Fragmento) "
        "WHERE all(c IN $claves WHERE (f)-[:MENCIONA]->({clave: c})) "
        "RETURN DISTINCT f.documento AS documento LIMIT 20", {"claves": list(claves)})
    return sorted({f["documento"] for f in filas})


def estado() -> dict[str, Any]:
    try:
        e = embebedor()
        dims, vocab = e.dimensiones, len(e.vocabulario)
    except Exception:
        dims, vocab = 0, 0
    try:
        total = correr("MATCH (f:Fragmento) RETURN count(f) AS n")[0]["n"]
    except Exception:
        total = 0
    return {"fragmentos": total, "dimensiones": dims, "vocabulario": vocab,
            "indice": f"{INDICE} · cosine", "modelo": "embeddings.npz"}
