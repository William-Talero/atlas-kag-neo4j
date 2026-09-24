"""Motor de grafo sobre Neo4j.

Misma regla que en la version AGE: el texto Cypher es estatico y todo valor
dinamico viaja como parametro. La diferencia es que aqui los parametros son
nativos y las etiquetas tambien se pueden filtrar sin componer texto, salvo en
el patron de relaciones de longitud variable, que sigue pasando por lista blanca.
"""

from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Any

from neo4j.graph import Node, Relationship

from kag.conexion import correr, correr_crudo
from kag.ontologia import (DIMENSIONES, ETIQUETAS, RELACIONES,
                           dimension_de_relacion, fuente_de, nombre_visible)

_CLAVE_VALIDA = re.compile(r"^[a-z]{3,12}:[A-Za-z0-9_\-]{1,48}$")


class ConsultaInvalida(ValueError):
    pass


def validar_clave(clave: str) -> str:
    if not _CLAVE_VALIDA.match(clave or ""):
        raise ConsultaInvalida(f"Clave de nodo no valida: {clave!r}")
    return clave


def validar_etiqueta(etiqueta: str) -> str:
    if etiqueta not in ETIQUETAS:
        raise ConsultaInvalida(f"Etiqueta desconocida: {etiqueta!r}")
    return etiqueta


def validar_relaciones(relaciones: list[str] | None) -> list[str]:
    if not relaciones:
        return []
    malas = [r for r in relaciones if r not in RELACIONES]
    if malas:
        raise ConsultaInvalida(f"Relaciones desconocidas: {malas}")
    return relaciones


class Resultado(dict):
    """Filas, el Cypher exacto que se ejecuto y la latencia medida."""


def ejecutar(texto: str, params: dict[str, Any] | None = None,
             columnas: list[str] | None = None) -> Resultado:
    t0 = time.perf_counter()
    filas = correr(texto, params or {})
    if columnas:
        filas = [{c: f.get(c) for c in columnas} for f in filas]
    return Resultado(
        cypher=texto.strip(), params=params or {}, filas=filas, total=len(filas),
        ms=round((time.perf_counter() - t0) * 1000, 2), motor="neo4j",
    )


# --------------------------------------------------------------------- esquema

def esquema() -> dict[str, Any]:
    t0 = time.perf_counter()
    # apoc no esta en la edicion community; los conteos salen del propio grafo.
    conteo_nodos = {f["etiqueta"]: f["n"] for f in correr(
        "MATCH (n) UNWIND labels(n) AS etiqueta "
        "RETURN etiqueta, count(*) AS n")}
    conteo_aristas = {f["relacion"]: f["n"] for f in correr(
        "MATCH ()-[r]->() RETURN type(r) AS relacion, count(*) AS n")}

    nodos = [{"etiqueta": e, "dimension": d, "conteo": conteo_nodos.get(e, 0)}
             for e, (d, _) in ETIQUETAS.items()]
    aristas = [{"relacion": r, "dimension": meta["dimension"],
                "fuente": meta["fuente"], "conteo": conteo_aristas.get(r, 0)}
               for r, meta in RELACIONES.items()]
    nodos.sort(key=lambda n: -n["conteo"])
    aristas.sort(key=lambda a: -a["conteo"])

    por_dimension = [{
        "dimension": clave, **meta,
        "nodos": sum(n["conteo"] for n in nodos if n["dimension"] == clave),
        "aristas": sum(a["conteo"] for a in aristas if a["dimension"] == clave),
        "etiquetas": [n["etiqueta"] for n in nodos if n["dimension"] == clave],
    } for clave, meta in DIMENSIONES.items()]

    return {
        "nodos": nodos, "aristas": aristas, "dimensiones": por_dimension,
        "totales": {
            "vertices": sum(n["conteo"] for n in nodos),
            "aristas": sum(a["conteo"] for a in aristas),
            "etiquetas": len(nodos), "relaciones": len(aristas),
            "dimensiones": len(DIMENSIONES),
        },
        "ms": round((time.perf_counter() - t0) * 1000, 2),
    }


# ---------------------------------------------------------------------- lectura

def _resumen(n: Node) -> dict[str, Any]:
    etiqueta = next(iter(n.labels), "")
    props = {k: v for k, v in dict(n).items() if k != "embedding"}
    plano = {"clave": props.get("clave", ""), "label": etiqueta, "props": props}
    return {
        "clave": plano["clave"], "label": etiqueta,
        "nombre": nombre_visible(plano),
        "dimension": ETIQUETAS.get(etiqueta, ("entidad", ""))[0],
        "props": props,
    }


def nodo(clave: str) -> dict[str, Any] | None:
    validar_clave(clave)
    registros = correr_crudo(
        "MATCH (n {clave: $clave}) RETURN n LIMIT 1", {"clave": clave})
    return _resumen(registros[0]["n"]) if registros else None


def buscar(termino: str, limite: int = 15) -> Resultado:
    limite = max(1, min(int(limite), 100))
    t = (termino or "").strip().lower()
    t0 = time.perf_counter()
    texto = (
        "MATCH (n) WHERE any(campo IN "
        "  [n.nombre, n.titulo, n.documento, n.nit, n.referencia, n.tipo, n.etiqueta, n.clave] "
        "  WHERE campo IS NOT NULL AND toLower(campo) CONTAINS $t) "
        "RETURN n LIMIT $limite"
    )
    registros = correr_crudo(texto, {"t": t, "limite": limite})
    return Resultado(
        cypher=texto, params={"t": t, "limite": limite},
        filas=[_resumen(r["n"]) for r in registros], total=len(registros),
        ms=round((time.perf_counter() - t0) * 1000, 2), motor="neo4j",
    )


def _arista(r: Relationship) -> dict[str, Any]:
    props = dict(r)
    return {
        "desde": r.start_node.get("clave", ""),
        "hasta": r.end_node.get("clave", ""),
        "relacion": r.type,
        "dimension": dimension_de_relacion(r.type),
        "fuente": props.get("fuente") or fuente_de(r.type),
    }


def _caminos(registros: list, texto: str, params: dict, raiz: str,
             t0: float) -> Resultado:
    nodos: dict[str, dict] = {}
    aristas: dict[tuple, dict] = {}
    for reg in registros:
        camino = reg["p"]
        for n in camino.nodes:
            r = _resumen(n)
            if r["clave"]:
                nodos.setdefault(r["clave"], r)
        for rel in camino.relationships:
            a = _arista(rel)
            if a["desde"] and a["hasta"]:
                aristas[(a["desde"], a["relacion"], a["hasta"])] = a

    saltos = []
    for a in aristas.values():
        o, d = nodos.get(a["desde"], {}), nodos.get(a["hasta"], {})
        saltos.append({
            "origen": a["desde"], "origen_label": o.get("label", ""),
            "origen_nombre": o.get("nombre", ""),
            "relacion": a["relacion"], "dimension": a["dimension"],
            "destino": a["hasta"], "destino_label": d.get("label", ""),
            "destino_nombre": d.get("nombre", ""),
            "fuente": a["fuente"],
        })

    return Resultado(
        cypher=texto.strip(), params=params, filas=[], raiz=raiz,
        nodos=list(nodos.values()), aristas=list(aristas.values()), saltos=saltos,
        total=len(nodos), ms=round((time.perf_counter() - t0) * 1000, 2),
        motor="neo4j",
    )


def expandir(clave: str, profundidad: int = 1,
             relaciones: list[str] | None = None, limite: int = 220) -> Resultado:
    validar_clave(clave)
    profundidad = max(1, min(int(profundidad), 4))
    limite = max(1, min(int(limite), 1500))
    filtro = validar_relaciones(relaciones)
    tipos = (":" + "|".join(filtro)) if filtro else ""
    texto = (f"MATCH p = (a {{clave: $clave}})-[{tipos}*1..{profundidad}]-(b) "
             "RETURN p LIMIT $limite")
    params = {"clave": clave, "limite": limite}
    t0 = time.perf_counter()
    return _caminos(correr_crudo(texto, params), texto, params, clave, t0)


def camino(desde: str, hasta: str, max_saltos: int = 5) -> Resultado:
    validar_clave(desde)
    validar_clave(hasta)
    max_saltos = max(1, min(int(max_saltos), 8))
    texto = (f"MATCH p = shortestPath((a {{clave: $desde}})-[*1..{max_saltos}]-"
             "(b {clave: $hasta})) RETURN p LIMIT 1")
    params = {"desde": desde, "hasta": hasta}
    t0 = time.perf_counter()
    return _caminos(correr_crudo(texto, params), texto, params, desde, t0)


def subgrafo(limite: int = 900) -> Resultado:
    limite = max(10, min(int(limite), 6000))
    texto = "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT $limite"
    t0 = time.perf_counter()
    registros = correr_crudo(texto, {"limite": limite})
    nodos: dict[str, dict] = {}
    aristas: list[dict] = []
    _acumular(registros, nodos, aristas)
    return Resultado(
        cypher=texto, params={"limite": limite}, filas=[],
        nodos=list(nodos.values()), aristas=aristas, total=len(nodos),
        ms=round((time.perf_counter() - t0) * 1000, 2), motor="neo4j",
    )


def _acumular(registros: list, nodos: dict[str, dict], aristas: list[dict]) -> None:
    for reg in registros:
        for extremo in ("a", "b"):
            r = _resumen(reg[extremo])
            if r["clave"]:
                nodos.setdefault(r["clave"], r)
        a = _arista(reg["r"])
        if a["desde"] and a["hasta"]:
            aristas.append(a)


@lru_cache(maxsize=4)
def _muestra(por_relacion: int) -> tuple:
    """Muestra con TODAS las relaciones representadas.

    Un `LIMIT n` sobre el conjunto de aristas devuelve una sola relacion —la
    primera que encuentra el planificador— y da la impresion de un grafo plano
    de tres etiquetas. Muestreando por tipo se ve el modelo: las catorce
    etiquetas y las seis dimensiones aparecen aunque una relacion tenga cuatro
    aristas en todo el grafo.

    Va como un solo UNION ALL y no como veinticinco consultas: cada viaje a la
    region cuesta mas que la propia lectura.
    """
    t0 = time.perf_counter()
    texto = " UNION ALL ".join(
        f"MATCH (a)-[r:{relacion}]->(b) RETURN a, r, b LIMIT {por_relacion}"
        for relacion in RELACIONES
    )
    registros = correr_crudo(texto)
    nodos: dict[str, dict] = {}
    aristas: list[dict] = []
    _acumular(registros, nodos, aristas)
    presentes = len({a["relacion"] for a in aristas})
    return (list(nodos.values()), aristas, presentes,
            round((time.perf_counter() - t0) * 1000, 2))


def muestra(por_relacion: int = 10) -> Resultado:
    por_relacion = max(1, min(int(por_relacion), 60))
    nodos, aristas, presentes, ms = _muestra(por_relacion)
    return Resultado(
        cypher=("MATCH (a)-[r:<cada relación>]->(b)\n"
                "RETURN a, r, b LIMIT $limite"),
        params={"por_relacion": por_relacion}, filas=[],
        nodos=list(nodos), aristas=list(aristas),
        relaciones_representadas=presentes, total=len(nodos),
        ms=ms, motor="neo4j",
    )
