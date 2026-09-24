"""El recuperador KAG: grafo primero, vector despues, fusion al final.

El orden importa. Un RAG clasico recupera por parecido y espera que el parecido
implique pertinencia. Aqui primero se demuestra la conexion estructural —con
saltos citables y su sistema de origen— y solo entonces se busca texto, dentro
de lo que el grafo ya acoto.

Puntaje de fusion:

    score = 0.55 · similitud_vectorial
          + 0.30 · proximidad_en_grafo      (1 / (1 + saltos_al_ancla))
          + 0.15 · densidad_de_evidencia    (entidades del subgrafo que menciona)

La fusion se hace sobre un grupo de candidatos varias veces mayor que k. Si se
reordenara solo el top-k por similitud, la proximidad nunca podria rescatar al
fragmento que esta a cero saltos del ancla y ocupa el puesto 40 por parecido.
"""

from __future__ import annotations

import re
import time
from collections import deque
from typing import Any

from kag import grafo, vector
from kag.ontologia import DIMENSIONES, ETIQUETAS

PESO_SIMILITUD = 0.55
PESO_PROXIMIDAD = 0.30
PESO_EVIDENCIA = 0.15
FACTOR_CANDIDATOS = 8

# Grado dentro del subgrafo a partir del cual un nodo se considera concentrador.
UMBRAL_CONCENTRADOR = 12

# Tokens con tilde: la base guarda "Mejía", asi que quitar acentos aqui romperia
# el CONTAINS. Longitud minima 4 para descartar articulos y preposiciones.
_TOKEN = re.compile(r"[0-9a-záéíóúüñ]{4,}")

# Palabras que aparecen en casi cualquier pregunta del dominio y no sirven para
# anclar: si se usan, el ancla acaba siendo el primer documento que las nombra.
_GENERICAS = {
    "cual", "cuál", "cuanto", "cuánto", "cuanta", "cuánta", "como", "cómo",
    "donde", "dónde", "quien", "quién", "cuando", "cuándo", "dice", "tiene",
    "hay", "esta", "está", "estan", "están", "puede", "debe", "sobre", "todo",
    "toda", "todos", "todas", "para", "por", "con", "sin", "del", "las", "los",
    "una", "unos", "unas", "que", "qué",
    "exposicion", "exposición", "grupo", "total", "real", "politica", "política",
    "norma", "riesgo", "cliente", "persona", "empresa", "filial", "producto",
    "credito", "crédito", "saldo", "cuota", "deuda", "documento", "fragmento",
}

# Etiquetas que sirven de ancla util: anclar en un Documento o un Fragmento
# devuelve el propio corpus y el recorrido no aporta nada.
_ANCLAS_UTILES = {"Persona", "Empresa", "Filial", "Producto", "Obligacion",
                  "Ciudad", "Region", "Concepto", "Norma"}
_PREFERIDAS = {"Persona", "Empresa", "Filial"}


# ------------------------------------------------------------------- anclaje

def _terminos(pregunta: str) -> list[str]:
    """Candidatos de anclaje: primero los bigramas, que son mucho mas selectivos.

    "mejía vargas" identifica a una persona; "vargas" a veinte y "andrés" a
    cincuenta. Buscar el nombre completo antes que sus partes evita anclar en
    un homonimo cualquiera.
    """
    vistos: set[str] = set()
    palabras: list[str] = []
    for t in _TOKEN.findall((pregunta or "").lower()):
        if t not in _GENERICAS and t not in vistos:
            vistos.add(t)
            palabras.append(t)
    palabras = palabras[:4]
    bigramas = [f"{a} {b}" for a, b in zip(palabras, palabras[1:])]
    return bigramas + palabras


def _puntuar(filas: list[dict]) -> tuple[int, int]:
    """Menor es mejor: primero los terminos que tocan una entidad, y entre esos
    los mas selectivos. Un termino que coincide con medio grafo no ancla nada."""
    toca_entidad = any(f["label"] in _PREFERIDAS for f in filas)
    return (0 if toca_entidad else 1, len(filas))


def anclar(pregunta: str, ancla: str | None = None) -> dict[str, Any]:
    """Resuelve la pregunta a nodos concretos del grafo.

    Tres intentos, de mas a menos preciso: clave explicita, termino distintivo
    de la pregunta, y —si nada coincide por texto— las entidades que mencionan
    los fragmentos mas parecidos. El ultimo salto es el que permite responder
    preguntas normativas, que no nombran a ninguna entidad.
    """
    if ancla:
        return {"claves": [grafo.validar_clave(ancla)], "candidatos": [],
                "estrategia": "clave explícita"}

    mejor: tuple[tuple[int, int], str, list[dict]] | None = None
    for termino in _terminos(pregunta):
        filas = [f for f in grafo.buscar(termino, 25)["filas"]
                 if f["label"] in _ANCLAS_UTILES]
        if not filas:
            continue
        puntaje = _puntuar(filas)
        if mejor is None or puntaje < mejor[0]:
            mejor = (puntaje, termino, filas)
        # Un termino que identifica a pocas entidades ya es suficiente: seguir
        # probando solo anade viajes a la base.
        if puntaje[0] == 0 and puntaje[1] <= 3:
            break

    if mejor is not None:
        _, termino, filas = mejor
        filas.sort(key=lambda f: (f["label"] not in _PREFERIDAS, len(f["nombre"])))
        return {"claves": [f["clave"] for f in filas[:3]],
                "candidatos": filas[:6],
                "estrategia": f"término distintivo · {termino}"}

    # Nada coincide por texto. Se recupera por similitud y se ancla en las
    # entidades que esos fragmentos mencionan: el vector encuentra el documento,
    # el grafo aporta de que habla.
    recuperado = vector.buscar(pregunta, 5)
    if recuperado.get("degenerado"):
        return {"claves": [], "candidatos": [], "estrategia": "fuera de vocabulario"}
    claves: list[str] = []
    for f in recuperado["resultados"]:
        for e in f["entidades"]:
            if e not in claves:
                claves.append(e)
    if claves:
        candidatos = [n for n in (grafo.nodo(c) for c in claves[:3]) if n]
        return {"claves": claves[:3], "candidatos": candidatos,
                "estrategia": "entidades de los fragmentos más parecidos"}
    return {"claves": [], "candidatos": [], "estrategia": "sin ancla"}


# -------------------------------------------------------------------- saltos

def _adyacencia(aristas: list[dict]) -> dict[str, set[str]]:
    ady: dict[str, set[str]] = {}
    for a in aristas:
        ady.setdefault(a["desde"], set()).add(a["hasta"])
        ady.setdefault(a["hasta"], set()).add(a["desde"])
    return ady


def _podar(sub: dict, raices: list[str]) -> dict:
    """Deja el ancla, sus conexiones y los caminos que sostienen la respuesta.

    La regla es no *atravesar* concentradores. Una ciudad con setenta y nueve
    vecinos dentro del subgrafo aporta un hecho sobre el ancla —donde reside—
    pero sus otros residentes no explican nada de la pregunta, y son la mitad
    de los nodos recuperados. El concentrador se muestra; lo que cuelga de él,
    no.
    """
    ady = _adyacencia(sub["aristas"])
    raiz = set(raices)

    visible = set(raices)
    cola = deque(raices)
    while cola:
        actual = cola.popleft()
        if actual not in raiz and len(ady.get(actual, ())) > UMBRAL_CONCENTRADOR:
            continue
        for vecino in ady.get(actual, ()):
            if vecino not in visible:
                visible.add(vecino)
                cola.append(vecino)

    nodos = [n for n in sub["nodos"] if n["clave"] in visible]
    aristas = [a for a in sub["aristas"]
               if a["desde"] in visible and a["hasta"] in visible]
    concentradores = sorted(
        {n["clave"] for n in nodos
         if n["clave"] not in raiz and len(ady.get(n["clave"], ())) > UMBRAL_CONCENTRADOR})

    return {
        **sub,
        "nodos": nodos,
        "aristas": aristas,
        "saltos": _saltos(aristas, {n["clave"]: n for n in nodos}),
        "omitidos": len(sub["nodos"]) - len(nodos),
        "concentradores": concentradores,
        "enfocado": True,
    }


def _saltos(aristas: list[dict], nodos: dict[str, dict]) -> list[dict]:
    salida = []
    for a in aristas:
        o, d = nodos.get(a["desde"], {}), nodos.get(a["hasta"], {})
        salida.append({
            "origen": a["desde"], "origen_label": o.get("label", ""),
            "origen_nombre": o.get("nombre", ""),
            "relacion": a["relacion"], "dimension": a["dimension"],
            "destino": a["hasta"], "destino_label": d.get("label", ""),
            "destino_nombre": d.get("nombre", ""),
            "fuente": a["fuente"],
        })
    return salida


def _distancias(raices: list[str], aristas: list[dict]) -> dict[str, int]:
    """BFS sobre el subgrafo recuperado. Da la proximidad de cada nodo al ancla."""
    adyacencia = _adyacencia(aristas)
    dist = {r: 0 for r in raices}
    cola = deque(raices)
    while cola:
        actual = cola.popleft()
        for vecino in adyacencia.get(actual, ()):
            if vecino not in dist:
                dist[vecino] = dist[actual] + 1
                cola.append(vecino)
    return dist


# -------------------------------------------------------------------- fusion

def _fusionar(fragmentos: list[dict], distancias: dict[str, int],
              claves: set[str]) -> list[dict]:
    salida = []
    for f in fragmentos:
        tocadas = [e for e in f["entidades"] if e in claves]
        saltos = min((distancias.get(e, 99) for e in tocadas), default=99)
        proximidad = 1.0 / (1.0 + saltos) if saltos < 99 else 0.0
        densidad = min(len(tocadas) / 4.0, 1.0)
        salida.append({
            **f,
            "saltos_al_ancla": None if saltos == 99 else saltos,
            "entidades_del_subgrafo": tocadas,
            "score": round(PESO_SIMILITUD * f["similitud"]
                           + PESO_PROXIMIDAD * proximidad
                           + PESO_EVIDENCIA * densidad, 4),
        })
    salida.sort(key=lambda x: -x["score"])
    return salida


# ------------------------------------------------------------------ respuesta

def responder(pregunta: str, ancla: str | None = None, profundidad: int = 2,
              k: int = 8, relaciones: list[str] | None = None,
              dimensiones: list[str] | None = None,
              enfocado: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    anclaje = anclar(pregunta, ancla)
    if not anclaje["claves"]:
        # Misma forma que una respuesta completa: el front no deberia tener que
        # distinguir el caso vacio para no romperse.
        rag = vector.buscar(pregunta, k)
        return {
            "pregunta": pregunta, "anclaje": anclaje, "suficiente": False,
            "veredicto": ("Ninguna entidad del grafo coincide con la pregunta. "
                          "Solo queda la recuperación por similitud."),
            "subgrafo": {"raiz": "", "nodos": [], "aristas": [], "saltos": [],
                         "cypher": "", "ms": 0.0, "por_dimension": [],
                         "enfocado": enfocado, "omitidos": 0,
                         "concentradores": [], "recorridos": 0},
            "evidencia": [],
            "kag": {"ms": 0.0, "sql": "", "anclas": 0, "candidatos": 0},
            "rag": rag,
            "cobertura": {"corpus": len(rag["resultados"]), "alcanzados": 0,
                          "reduccion": 0.0},
            "aporte_del_grafo": {"fragmentos_solo_kag": [], "reduccion_del_corpus": 0.0,
                                 "saltos_citados": 0, "fuentes": []},
            "ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    filtro = _relaciones_por_dimension(relaciones, dimensiones)
    raiz = anclaje["claves"][0]
    completo = grafo.expandir(raiz, profundidad, filtro)
    if not anclaje["candidatos"]:
        anclaje["candidatos"] = [n for n in completo["nodos"] if n["clave"] == raiz]

    # La recuperacion vectorial usa el subgrafo completo: podar es una decision
    # de presentacion y no debe cambiar lo que se acota ni lo que se cita.
    claves = {n["clave"] for n in completo["nodos"]}
    distancias = _distancias([raiz], completo["aristas"])

    kag = vector.buscar_en_subgrafo(pregunta, sorted(claves), k * FACTOR_CANDIDATOS)
    rag = vector.buscar(pregunta, k)
    evidencia = _fusionar(kag["resultados"], distancias, claves)[:k]
    cob = vector.cobertura(sorted(claves))

    sub = _podar(completo, [raiz]) if enfocado else {**completo, "omitidos": 0,
                                                    "concentradores": [],
                                                    "enfocado": False}

    solo_kag = {f["clave"] for f in evidencia} - {f["clave"] for f in rag["resultados"]}
    return {
        "pregunta": pregunta,
        "anclaje": anclaje,
        "subgrafo": {
            "raiz": raiz,
            "nodos": sub["nodos"], "aristas": sub["aristas"], "saltos": sub["saltos"],
            "cypher": sub["cypher"], "ms": sub["ms"],
            "por_dimension": _conteo_por_dimension(sub),
            "enfocado": sub["enfocado"],
            "omitidos": sub["omitidos"],
            "concentradores": [
                {"clave": c, "nombre": n["nombre"], "label": n["label"]}
                for c in sub["concentradores"]
                for n in sub["nodos"] if n["clave"] == c
            ],
            "recorridos": len(completo["nodos"]),
        },
        "evidencia": evidencia,
        "kag": {k2: v for k2, v in kag.items() if k2 != "resultados"} |
               {"candidatos": len(kag["resultados"])},
        "rag": rag,
        "cobertura": cob,
        "suficiente": bool(evidencia),
        "aporte_del_grafo": {
            "fragmentos_solo_kag": sorted(solo_kag),
            "reduccion_del_corpus": cob["reduccion"],
            "saltos_citados": len(sub["saltos"]),
            "fuentes": sorted({s["fuente"] for s in sub["saltos"]}),
        },
        "veredicto": _veredicto(evidencia, rag["resultados"], cob, sub),
        "ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def _relaciones_por_dimension(relaciones: list[str] | None,
                              dimensiones: list[str] | None) -> list[str]:
    if relaciones:
        return grafo.validar_relaciones(relaciones)
    if not dimensiones:
        return []
    malas = [d for d in dimensiones if d not in DIMENSIONES]
    if malas:
        raise grafo.ConsultaInvalida(f"Dimensiones desconocidas: {malas}")
    from kag.ontologia import relaciones_de
    return [r for d in dimensiones for r in relaciones_de(d)]


def _conteo_por_dimension(sub: dict) -> list[dict[str, Any]]:
    salida = []
    for clave, meta in DIMENSIONES.items():
        nodos = sum(1 for n in sub["nodos"] if n["dimension"] == clave)
        aristas = sum(1 for a in sub["aristas"] if a["dimension"] == clave)
        if nodos or aristas:
            salida.append({"dimension": clave, "titulo": meta["titulo"],
                           "nodos": nodos, "aristas": aristas})
    return salida


def _veredicto(evidencia: list[dict], rag: list[dict], cobertura: dict,
               sub: dict) -> str:
    if not evidencia:
        return ("El grafo conecta los nodos pero ningún fragmento del corpus los "
                "menciona: la relación existe como aristas, no como texto redactado.")
    cruce = len({n["dimension"] for n in sub["nodos"]})
    solo_kag = {f["clave"] for f in evidencia} - {f["clave"] for f in rag}
    partes = [
        f"{len(sub['saltos'])} saltos citables sobre {cruce} dimensiones",
        f"corpus reducido {cobertura['reduccion']}%",
    ]
    if solo_kag:
        partes.append(f"{len(solo_kag)} fragmentos que la similitud pura no trajo")
    return "El grafo aportó " + ", ".join(partes) + "."
