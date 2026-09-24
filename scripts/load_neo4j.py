"""Carga el grafo y el corpus en Neo4j.

Comparado con el cargador de AGE, aqui no hay fases ni reconexiones: el driver
mantiene la sesion, las etiquetas no se declaran por adelantado y los parametros
son nativos. Lo unico que se compone en el texto son los nombres de etiqueta y
de relacion, que Cypher no parametriza, y ambos pasan por la ontologia.

    python scripts/load_neo4j.py            carga incremental (MERGE)
    python scripts/load_neo4j.py --recrear  borra el grafo y lo reconstruye
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "apps" / "api"))

from kag.conexion import cerrar, correr  # noqa: E402
from kag.ontologia import ETIQUETAS, RELACIONES  # noqa: E402
from settings import load_settings  # noqa: E402

LOTE = 1000


def _log(msg: str) -> None:
    print(msg, flush=True)


def aplicar_esquema(recrear: bool) -> None:
    dim = int(load_settings()["EMBED_DIM"])
    if recrear:
        _log("· borrando el grafo anterior")
        # En lotes para no agotar la memoria de la transaccion.
        while correr("MATCH (n) WITH n LIMIT 20000 DETACH DELETE n "
                     "RETURN count(*) AS n")[0]["n"]:
            pass
        for indice in ("fragmento_embedding", "fragmento_texto"):
            correr(f"DROP INDEX {indice} IF EXISTS")

    for etiqueta in ETIQUETAS:
        correr(f"CREATE CONSTRAINT clave_{etiqueta.lower()} IF NOT EXISTS "
               f"FOR (n:{etiqueta}) REQUIRE n.clave IS UNIQUE")
    correr(
        "CREATE VECTOR INDEX fragmento_embedding IF NOT EXISTS "
        "FOR (f:Fragmento) ON (f.embedding) "
        "OPTIONS { indexConfig: { `vector.dimensions`: $dim, "
        "`vector.similarity_function`: 'cosine' } }", {"dim": dim})
    correr("CREATE FULLTEXT INDEX fragmento_texto IF NOT EXISTS "
           "FOR (f:Fragmento) ON EACH [f.titulo, f.texto]")
    _log(f"· {len(ETIQUETAS)} restricciones · índice vectorial de {dim} dimensiones")


def cargar_nodos(nodos: list[dict]) -> int:
    por_etiqueta: dict[str, list[dict]] = defaultdict(list)
    for n in nodos:
        if n["label"] not in ETIQUETAS:
            raise SystemExit(f"Etiqueta fuera de la ontología: {n['label']}")
        por_etiqueta[n["label"]].append(n)

    total = 0
    for etiqueta, lista in por_etiqueta.items():
        cypher = (f"UNWIND $filas AS f MERGE (n:{etiqueta} {{clave: f.clave}}) "
                  "SET n += f.props")
        for i in range(0, len(lista), LOTE):
            correr(cypher, {"filas": [
                {"clave": n["clave"], "props": n["props"]} for n in lista[i:i + LOTE]]})
        total += len(lista)
        _log(f"  · {etiqueta:<12} {len(lista):>6}")
    return total


def cargar_aristas(aristas: list[dict], etiqueta_de: dict[str, str]) -> int:
    grupos: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for a in aristas:
        eo, ed = etiqueta_de.get(a["desde"]), etiqueta_de.get(a["hasta"])
        if not eo or not ed:
            raise SystemExit(f"Arista con extremo inexistente: {a}")
        meta = RELACIONES[a["relacion"]]
        if eo not in meta["desde"] or ed not in meta["hasta"]:
            raise SystemExit(
                f"{a['relacion']} no admite {eo} -> {ed} según la ontología")
        grupos[(a["relacion"], eo, ed)].append(a)

    total = 0
    for (relacion, eo, ed), lista in sorted(grupos.items()):
        cypher = (
            "UNWIND $filas AS f "
            f"MATCH (a:{eo} {{clave: f.desde}}), (b:{ed} {{clave: f.hasta}}) "
            f"MERGE (a)-[r:{relacion}]->(b) "
            "SET r.fuente = f.fuente, r.dimension = f.dimension"
        )
        for i in range(0, len(lista), LOTE):
            correr(cypher, {"filas": [
                {"desde": a["desde"], "hasta": a["hasta"],
                 "fuente": a["props"]["fuente"], "dimension": a["props"]["dimension"]}
                for a in lista[i:i + LOTE]]})
        total += len(lista)
        _log(f"  · {relacion:<16} {eo:>10} → {ed:<12} {len(lista):>6}")
    return total


def cargar_fragmentos(documentos: list[dict], vectores: dict[str, list]) -> int:
    filas = [
        {"clave": f["clave"], "documento": d["clave"], "titulo": f["titulo"],
         "texto": f["texto"], "dimension": f["dimension"],
         "entidades": f["entidades"], "embedding": vectores[f["clave"]]}
        for d in documentos for f in d["fragmentos"]
    ]
    cypher = (
        "UNWIND $filas AS f "
        "MATCH (n:Fragmento {clave: f.clave}) "
        "SET n.documento = f.documento, n.texto = f.texto, "
        "    n.entidades = f.entidades "
        "WITH n, f CALL db.create.setNodeVectorProperty(n, 'embedding', f.embedding) "
        "RETURN count(*) AS n"
    )
    for i in range(0, len(filas), 200):
        correr(cypher, {"filas": filas[i:i + 200]})
    _log(f"  · Fragmento (texto y vector)  {len(filas):>6}")
    return len(filas)


def main() -> int:
    recrear = "--recrear" in sys.argv
    data = load_settings()["DATA"]
    grafo = json.loads((data / "grafo.json").read_text("utf-8"))
    documentos = json.loads((data / "documentos.json").read_text("utf-8"))
    vectores = json.loads((data / "vectores.json").read_text("utf-8"))

    t0 = time.perf_counter()
    try:
        aplicar_esquema(recrear)

        _log("· nodos")
        etiqueta_de = {n["clave"]: n["label"] for n in grafo["nodos"]}
        n = cargar_nodos(grafo["nodos"])

        _log("· aristas")
        a = cargar_aristas(grafo["aristas"], etiqueta_de)

        _log("· dimensión documental")
        f = cargar_fragmentos(documentos, vectores)
    finally:
        cerrar()

    _log(f"\nCargado: {n} nodos · {a} aristas · {f} fragmentos "
         f"en {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
