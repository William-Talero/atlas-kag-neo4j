"""Consultas de negocio, una por dimension.

Son las mismas preguntas que en la version AGE y, donde el Cypher es estandar,
el texto es literalmente el mismo. Las diferencias estan marcadas: Neo4j resuelve
alias en `ORDER BY` sin `WITH` intermedio y admite `LIMIT $param`, asi que aqui
no se compone nada en el texto.
"""

from __future__ import annotations

from typing import Any

from kag import grafo
from kag.ontologia import TOPE_ENDEUDAMIENTO


# ------------------------------------------------------ dimension · operacion

def exposicion_persona(clave: str) -> dict[str, Any]:
    """La cifra que ninguna filial calcula: cuota agregada de todo el grupo."""
    grafo.validar_clave(clave)
    res = grafo.ejecutar(
        "MATCH (p:Persona {clave: $clave})-[:TITULAR_DE]->(pr:Producto)"
        "-[:EMITIDO_POR]->(f:Filial) "
        "OPTIONAL MATCH (pr)-[:GENERA]->(o:Obligacion) "
        "RETURN f.nombre AS filial, pr.tipo AS producto, pr.apertura AS apertura, "
        "       pr.nuevo AS nuevo, o.referencia AS obligacion, "
        "       coalesce(o.cuotaMensual, 0) AS cuota, coalesce(o.saldo, 0) AS saldo, "
        "       coalesce(o.diasMora, 0) AS mora",
        {"clave": clave},
        ["filial", "producto", "apertura", "nuevo", "obligacion", "cuota", "saldo", "mora"],
    )
    persona = grafo.nodo(clave) or {}
    ingreso = int((persona.get("props") or {}).get("ingresoMensual") or 0) or 1

    filas = res["filas"]
    cuota = sum(int(f["cuota"] or 0) for f in filas)
    previa = sum(int(f["cuota"] or 0) for f in filas if not f["nuevo"])
    res["resumen"] = {
        "persona": clave,
        "nombre": persona.get("nombre", ""),
        "ingreso_cop": ingreso,
        "productos": len(filas),
        "filiales": len({f["filial"] for f in filas if f["filial"]}),
        "cuota_cop": cuota,
        "saldo_cop": sum(int(f["saldo"] or 0) for f in filas),
        "endeudamiento": round(cuota / ingreso * 100, 1),
        "endeudamiento_previo": round(previa / ingreso * 100, 1),
        "tope": TOPE_ENDEUDAMIENTO,
        "excede": (cuota / ingreso * 100) > TOPE_ENDEUDAMIENTO,
        "mora_maxima": max((int(f["mora"] or 0) for f in filas), default=0),
    }
    return res


def exposicion_indirecta(clave: str) -> dict[str, Any]:
    """Deuda que no cuelga de la persona: cuelga de otros y apunta hacia atras."""
    grafo.validar_clave(clave)
    res = grafo.ejecutar(
        "MATCH (p:Persona {clave: $clave})-[:CODEUDOR_DE]->(o:Obligacion) "
        "MATCH (pr:Producto)-[:GENERA]->(o)-[:VIGENTE_EN]->() "
        "MATCH (pr)-[:EMITIDO_POR]->(f:Filial) "
        "MATCH (deudor:Persona)-[:TITULAR_DE]->(pr) "
        "RETURN DISTINCT deudor.nombre AS deudor, f.nombre AS filial, "
        "       o.referencia AS obligacion, o.saldo AS saldo, o.diasMora AS mora",
        {"clave": clave},
        ["deudor", "filial", "obligacion", "saldo", "mora"],
    )
    res["saldo_cop"] = sum(int(f["saldo"] or 0) for f in res["filas"])
    res["en_mora"] = sum(1 for f in res["filas"] if int(f["mora"] or 0) > 0)
    return res


# -------------------------------------------------------- dimension · entidad

def grupo_economico(clave: str, max_saltos: int = 4) -> dict[str, Any]:
    """Arbol de control de profundidad desconocida: hay que agotarlo."""
    grafo.validar_clave(clave)
    saltos = max(1, min(int(max_saltos), 6))
    res = grafo.ejecutar(
        f"MATCH (raiz:Empresa {{clave: $clave}})-[:MATRIZ_DE*0..{saltos}]->(e:Empresa) "
        "MATCH (e)-[:TITULAR_DE]->(pr:Producto)-[:GENERA]->(o:Obligacion) "
        "MATCH (pr)-[:EMITIDO_POR]->(f:Filial) "
        "RETURN e.nombre AS empresa, e.nit AS nit, f.nombre AS filial, "
        "       o.saldo AS saldo, o.diasMora AS mora",
        {"clave": clave},
        ["empresa", "nit", "filial", "saldo", "mora"],
    )
    res["saldo_cop"] = sum(int(f["saldo"] or 0) for f in res["filas"])
    res["empresas"] = len({f["empresa"] for f in res["filas"]})
    res["filiales"] = len({f["filial"] for f in res["filas"]})
    return res


def identidades_probables(clave: str, minimo: int = 2) -> dict[str, Any]:
    """Misma persona con documentos distintos: se delata por vecinos comunes."""
    grafo.validar_clave(clave)
    return grafo.ejecutar(
        "MATCH (a:Persona {clave: $clave})-[:RESIDE_EN]->(c:Ciudad)<-[:RESIDE_EN]-(b:Persona) "
        "WHERE a.clave <> b.clave AND b.telefono = a.telefono "
        "RETURN b.clave AS candidato, b.nombre AS nombre, b.documento AS documento, "
        "       c.nombre AS ciudad, b.telefono AS telefono",
        {"clave": clave},
        ["candidato", "nombre", "documento", "ciudad", "telefono"],
    )


# ----------------------------------------------------- dimension · geografica

def concentracion_geografica(limite: int = 20) -> dict[str, Any]:
    limite = max(1, min(int(limite), 100))
    return grafo.ejecutar(
        "MATCH (p:Persona)-[:RESIDE_EN]->(c:Ciudad)-[:PERTENECE_A]->(r:Region) "
        "MATCH (p)-[:TITULAR_DE]->(:Producto)-[:GENERA]->(o:Obligacion) "
        "RETURN r.nombre AS region, c.nombre AS ciudad, "
        "       count(o) AS obligaciones, sum(o.saldo) AS saldo "
        "ORDER BY saldo DESC LIMIT $limite",
        {"limite": limite}, ["region", "ciudad", "obligaciones", "saldo"],
    )


# ------------------------------------------------------- dimension · temporal

def serie_temporal(limite: int = 24) -> dict[str, Any]:
    limite = max(1, min(int(limite), 60))
    return grafo.ejecutar(
        "MATCH (o:Obligacion)-[:VIGENTE_EN]->(t:Periodo) "
        "RETURN t.etiqueta AS periodo, t.orden AS orden, "
        "       count(o) AS obligaciones, sum(o.saldo) AS saldo "
        "ORDER BY orden DESC LIMIT $limite",
        {"limite": limite}, ["periodo", "orden", "obligaciones", "saldo"],
    )


def eventos_de(clave: str, limite: int = 30) -> dict[str, Any]:
    grafo.validar_clave(clave)
    limite = max(1, min(int(limite), 200))
    return grafo.ejecutar(
        "MATCH (ev:Evento)-[:AFECTA_A]->({clave: $clave}) "
        "MATCH (ev)-[:OCURRE_EN]->(t:Periodo) "
        "OPTIONAL MATCH (ev)-[:TIPIFICA]->(c:Concepto) "
        "RETURN ev.titulo AS evento, ev.severidad AS severidad, "
        "       t.etiqueta AS periodo, t.orden AS orden, c.nombre AS concepto "
        "ORDER BY orden DESC LIMIT $limite",
        {"clave": clave, "limite": limite},
        ["evento", "severidad", "periodo", "orden", "concepto"],
    )


# ------------------------------------------------------ dimension · semantica

def exposicion_por_concepto(limite: int = 20) -> dict[str, Any]:
    limite = max(1, min(int(limite), 100))
    return grafo.ejecutar(
        "MATCH (pr:Producto)-[:CLASIFICA_COMO]->(c:Concepto) "
        "MATCH (pr)-[:GENERA]->(o:Obligacion) "
        "OPTIONAL MATCH (n:Norma)-[:REGULA]->(c) "
        "RETURN c.nombre AS concepto, n.titulo AS norma, "
        "       count(o) AS obligaciones, sum(o.saldo) AS saldo "
        "ORDER BY saldo DESC LIMIT $limite",
        {"limite": limite}, ["concepto", "norma", "obligaciones", "saldo"],
    )


def norma_aplicable(clave: str) -> dict[str, Any]:
    """De un producto concreto a la norma que lo regula, subiendo la jerarquia."""
    grafo.validar_clave(clave)
    return grafo.ejecutar(
        "MATCH (pr:Producto {clave: $clave})-[:CLASIFICA_COMO]->(c:Concepto) "
        "MATCH (c)-[:SUBTIPO_DE*0..3]->(padre:Concepto) "
        "MATCH (n:Norma)-[:REGULA]->(padre) "
        "RETURN DISTINCT padre.nombre AS concepto, n.clave AS norma_clave, "
        "       n.titulo AS norma, n.emisor AS emisor, n.vigencia AS vigencia",
        {"clave": clave},
        ["concepto", "norma_clave", "norma", "emisor", "vigencia"],
    )


# ----------------------------------------------------- dimension · documental

def evidencia_de(clave: str, limite: int = 20) -> dict[str, Any]:
    grafo.validar_clave(clave)
    limite = max(1, min(int(limite), 100))
    return grafo.ejecutar(
        "MATCH (fr:Fragmento)-[:MENCIONA]->({clave: $clave}) "
        "MATCH (d:Documento)-[:CONTIENE]->(fr) "
        "RETURN d.titulo AS documento, d.fuente AS fuente, d.fecha AS fecha, "
        "       fr.clave AS fragmento, fr.titulo AS titulo "
        "LIMIT $limite",
        {"clave": clave, "limite": limite},
        ["documento", "fuente", "fecha", "fragmento", "titulo"],
    )


CATALOGO: dict[str, dict[str, Any]] = {
    "exposicion-persona": {
        "dimension": "operacion", "requiere": "Persona",
        "titulo": "Exposición real de una persona",
        "porque_grafo": "Antes de sumar hay que resolver que varias fichas de varios cores son la misma persona.",
        "fn": exposicion_persona,
    },
    "exposicion-indirecta": {
        "dimension": "operacion", "requiere": "Persona",
        "titulo": "Exposición indirecta por aval",
        "porque_grafo": "La deuda avalada no cuelga de la persona: cuelga de otros y apunta hacia atrás.",
        "fn": exposicion_indirecta,
    },
    "grupo-economico": {
        "dimension": "entidad", "requiere": "Empresa",
        "titulo": "Exposición del grupo económico",
        "porque_grafo": "La profundidad del árbol de matrices es desconocida: hay que agotarla.",
        "fn": grupo_economico,
    },
    "identidades": {
        "dimension": "entidad", "requiere": "Persona",
        "titulo": "¿Son la misma persona?",
        "porque_grafo": "El documento difiere en un dígito; lo único que une los registros es un vecino común.",
        "fn": identidades_probables,
    },
    "concentracion-geografica": {
        "dimension": "geografica", "requiere": None,
        "titulo": "Concentración por territorio",
        "porque_grafo": "El saldo vive en la obligación y el territorio en la persona: hay que cruzarlos.",
        "fn": concentracion_geografica,
    },
    "serie-temporal": {
        "dimension": "temporal", "requiere": None,
        "titulo": "Evolución de la cartera",
        "porque_grafo": "La vigencia es una arista por mes, no una columna.",
        "fn": serie_temporal,
    },
    "eventos": {
        "dimension": "temporal", "requiere": None,
        "titulo": "Línea de tiempo de un nodo",
        "porque_grafo": "Los eventos apuntan al sujeto desde otra dimensión.",
        "fn": eventos_de,
    },
    "exposicion-concepto": {
        "dimension": "semantica", "requiere": None,
        "titulo": "Exposición por concepto de riesgo",
        "porque_grafo": "El concepto es una jerarquía, no una etiqueta plana.",
        "fn": exposicion_por_concepto,
    },
    "norma-aplicable": {
        "dimension": "semantica", "requiere": "Producto",
        "titulo": "Qué norma regula este producto",
        "porque_grafo": "La norma regula un concepto padre, a varios niveles de distancia.",
        "fn": norma_aplicable,
    },
    "evidencia": {
        "dimension": "documental", "requiere": None,
        "titulo": "Dónde consta este nodo",
        "porque_grafo": "El vínculo fragmento–entidad es una arista extraída, no una búsqueda de texto.",
        "fn": evidencia_de,
    },
}


def catalogo() -> list[dict[str, Any]]:
    return [
        {"id": k, **{c: v for c, v in meta.items() if c != "fn"}}
        for k, meta in CATALOGO.items()
    ]


def correr(consulta_id: str, clave: str | None = None) -> dict[str, Any]:
    meta = CATALOGO.get(consulta_id)
    if not meta:
        raise grafo.ConsultaInvalida(f"Consulta desconocida: {consulta_id!r}")
    fn = meta["fn"]
    if meta["requiere"]:
        if not clave:
            raise grafo.ConsultaInvalida(
                f"'{consulta_id}' requiere una clave de tipo {meta['requiere']}")
        res = fn(clave)
    else:
        res = fn(clave) if consulta_id in ("eventos", "evidencia") and clave else fn()
    return {"consulta": consulta_id, "dimension": meta["dimension"],
            "titulo": meta["titulo"], "porque_grafo": meta["porque_grafo"], **res}
