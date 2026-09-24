"""Verificacion de extremo a extremo sobre Neo4j. Falla si algo no se alcanza.

Es la misma bateria que en la version PostgreSQL y comprueba las mismas
afirmaciones: si las dos implementaciones son equivalentes, las dos tienen que
pasarla igual.

    python scripts/verify_kag.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "apps" / "api"))

from kag import dimensiones as D  # noqa: E402
from kag import grafo, preguntas, recuperador, vector  # noqa: E402
from kag.conexion import cerrar, ping  # noqa: E402
from kag.ontologia import DIMENSIONES, ETIQUETAS, RELACIONES, TOPE_ENDEUDAMIENTO  # noqa: E402

fallos: list[str] = []
t_inicio = time.perf_counter()


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    marca = "ok  " if condicion else "FALLA"
    print(f"  {marca} · {nombre}{('  — ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


def bloque(titulo: str) -> None:
    print(f"\n{titulo}")


# --------------------------------------------------------------------- motor

bloque("Motor")
estado = ping()
check("conexión a Neo4j", estado.get("ok", False), estado.get("error", ""))
check("versión 5.x", str(estado.get("version", "")).startswith("5."),
      f"{estado.get('producto')} {estado.get('version')} {estado.get('edicion')}")
check("índice vectorial nativo creado", estado.get("indices_vectoriales", 0) >= 1,
      f"{estado.get('indices_vectoriales')} índice(s)")

# ------------------------------------------------------------------- modelo

bloque("Modelo multidimensional")
esq = grafo.esquema()
check("seis dimensiones declaradas", len(DIMENSIONES) == 6)
check("catorce etiquetas en la ontología", len(ETIQUETAS) == 14)
check("veinticinco relaciones en la ontología", len(RELACIONES) == 25)
check("el grafo tiene nodos en las seis dimensiones",
      all(d["nodos"] > 0 for d in esq["dimensiones"]),
      " · ".join(f"{d['titulo']}={d['nodos']}" for d in esq["dimensiones"]))
check("el grafo tiene aristas en las seis dimensiones",
      all(d["aristas"] > 0 for d in esq["dimensiones"]))
check("volumen cargado", esq["totales"]["vertices"] > 8000
      and esq["totales"]["aristas"] > 40000,
      f"{esq['totales']['vertices']} nodos · {esq['totales']['aristas']} aristas")

# -------------------------------------------------- el numero que no existe

bloque("El número que ningún core tiene")
exp = D.exposicion_persona("psn:carlos")["resumen"]
check("nueve productos en seis filiales",
      exp["productos"] == 9 and exp["filiales"] == 6,
      f"{exp['productos']} productos · {exp['filiales']} filiales")
check("antes del último producto estaba dentro de política",
      exp["endeudamiento_previo"] < TOPE_ENDEUDAMIENTO,
      f"{exp['endeudamiento_previo']}% < {TOPE_ENDEUDAMIENTO}%")
check("con el último producto supera el tope",
      exp["endeudamiento"] > TOPE_ENDEUDAMIENTO,
      f"{exp['endeudamiento']}% > {TOPE_ENDEUDAMIENTO}%")

# ------------------------------------------------------ las seis dimensiones

bloque("Una consulta por dimensión")
casos = [
    ("operacion", "exposicion-indirecta", "psn:avalista", lambda r: r["total"] > 0),
    ("entidad", "grupo-economico", "emp:matriz-altamar", lambda r: r["empresas"] >= 4),
    ("entidad", "identidades", "psn:duplicada-1", lambda r: r["total"] >= 2),
    ("geografica", "concentracion-geografica", None, lambda r: r["total"] > 5),
    ("temporal", "serie-temporal", None, lambda r: r["total"] > 5),
    ("temporal", "eventos", "psn:carlos", lambda r: r["total"] > 0),
    ("semantica", "exposicion-concepto", None, lambda r: r["total"] > 0),
    ("documental", "evidencia", "psn:carlos", lambda r: r["total"] > 0),
]
for dim, cid, clave, prueba in casos:
    try:
        res = D.correr(cid, clave)
        check(f"[{dim}] {cid}", prueba(res), f"{res['total']} filas · {res['ms']:.0f} ms")
    except Exception as exc:
        check(f"[{dim}] {cid}", False, str(exc).splitlines()[0][:80])

producto = grafo.buscar("libre inversión", 1)["filas"]
if producto:
    res = D.correr("norma-aplicable", producto[0]["clave"])
    check("[semantica] norma-aplicable sube la jerarquía de conceptos",
          res["total"] >= 2, f"{res['total']} normas")

# ---------------------------------------------------------------- KAG vs RAG

bloque("KAG contra la línea base RAG")
p = preguntas.buscar("exposicion-real")
r = recuperador.responder(p["pregunta"], p["ancla"], p["profundidad"], k=6)
check("el anclaje resuelve a un nodo", bool(r["anclaje"]["claves"]),
      r["anclaje"]["estrategia"])
check("el subgrafo cruza varias dimensiones",
      len(r["subgrafo"]["por_dimension"]) >= 4,
      " · ".join(f"{d['titulo']}={d['nodos']}" for d in r["subgrafo"]["por_dimension"]))
check("cada salto cita su sistema de origen",
      all(s["fuente"] for s in r["subgrafo"]["saltos"]),
      f"{len(r['aporte_del_grafo']['fuentes'])} fuentes distintas")
check("el grafo acota el corpus", r["cobertura"]["reduccion"] > 0,
      f"{r['cobertura']['alcanzados']}/{r['cobertura']['corpus']} fragmentos")
cero = [e for e in r["evidencia"] if e["saltos_al_ancla"] == 0]
check("la fusión sube la evidencia que toca al ancla", len(cero) >= 3,
      f"{len(cero)} fragmentos a 0 saltos en el top {len(r['evidencia'])}")

bloque("El contraejemplo: donde el grafo sobra")
c = preguntas.buscar("contraejemplo")
solo_vector = vector.buscar(c["pregunta"], 5)
check("la búsqueda vectorial sola responde la pregunta normativa",
      any("Política" in x["titulo"] or "Circular" in x["titulo"]
          for x in solo_vector["resultados"]),
      solo_vector["resultados"][0]["titulo"][:70] if solo_vector["resultados"] else "")

# ------------------------------------------------------------------ seguridad

bloque("Superficie de consulta")
for entrada in ("psn:carlos' RETURN n //", "../../etc", "psn:" + "x" * 80):
    try:
        grafo.validar_clave(entrada)
        check(f"rechaza clave inválida {entrada[:24]!r}", False)
    except grafo.ConsultaInvalida:
        check(f"rechaza clave inválida {entrada[:24]!r}", True)
try:
    grafo.validar_relaciones(["BORRA_TODO"])
    check("rechaza relación fuera de la ontología", False)
except grafo.ConsultaInvalida:
    check("rechaza relación fuera de la ontología", True)

# ---------------------------------------------------------------------- fin

cerrar()
print(f"\n{'─' * 62}")
if fallos:
    print(f"FALLAN {len(fallos)} comprobaciones:")
    for f in fallos:
        print(f"  · {f}")
    raise SystemExit(1)
print(f"Todo verificado en {time.perf_counter() - t_inicio:.1f}s")
