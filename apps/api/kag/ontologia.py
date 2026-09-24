"""Ontologia del grafo de conocimiento ATLAS.

El grafo no es una sola red: son seis dimensiones que comparten los mismos nodos.
Una persona es a la vez un titular (dimension operacion), un residente (dimension
geografica), el sujeto de un evento (dimension temporal), una instancia de un
concepto (dimension semantica) y algo mencionado en un documento (dimension
documental). Cada consulta KAG elige por cuales dimensiones se mueve.
"""

from __future__ import annotations

from typing import Literal, TypedDict

GRAFO = "atlas"

Dimension = Literal["entidad", "operacion", "geografica", "temporal",
                    "semantica", "documental"]

DIMENSIONES: dict[str, dict[str, str]] = {
    "entidad": {
        "titulo": "Entidad",
        "pregunta": "¿Quién?",
        "descripcion": "Personas, empresas y filiales del grupo. El sujeto de todo lo demás.",
    },
    "operacion": {
        "titulo": "Operación",
        "pregunta": "¿Qué se contrató?",
        "descripcion": "Productos, obligaciones y garantías. Lo que cada core registra.",
    },
    "geografica": {
        "titulo": "Geográfica",
        "pregunta": "¿Dónde?",
        "descripcion": "Ciudades y regiones. Permite concentración territorial.",
    },
    "temporal": {
        "titulo": "Temporal",
        "pregunta": "¿Cuándo?",
        "descripcion": "Periodos mensuales y eventos fechados. Da la secuencia causal.",
    },
    "semantica": {
        "titulo": "Semántica",
        "pregunta": "¿Qué significa?",
        "descripcion": "Conceptos y normas. La capa que conecta el dato con la política.",
    },
    "documental": {
        "titulo": "Documental",
        "pregunta": "¿Dónde consta?",
        "descripcion": "Documentos y fragmentos vectorizados. La evidencia citable.",
    },
}

# Etiqueta -> (dimension, campo que se muestra como nombre)
ETIQUETAS: dict[str, tuple[str, str]] = {
    "Persona": ("entidad", "nombre"),
    "Empresa": ("entidad", "nombre"),
    "Filial": ("entidad", "nombre"),
    "Producto": ("operacion", "tipo"),
    "Obligacion": ("operacion", "referencia"),
    "Garantia": ("operacion", "tipo"),
    "Ciudad": ("geografica", "nombre"),
    "Region": ("geografica", "nombre"),
    "Periodo": ("temporal", "etiqueta"),
    "Evento": ("temporal", "titulo"),
    "Concepto": ("semantica", "nombre"),
    "Norma": ("semantica", "titulo"),
    "Documento": ("documental", "titulo"),
    "Fragmento": ("documental", "titulo"),
}


class Relacion(TypedDict):
    desde: list[str]
    hasta: list[str]
    dimension: str
    fuente: str


# Cada relacion declara de que sistema de registro proviene. Es lo que permite
# que una respuesta KAG cite la procedencia salto a salto y no solo el documento.
RELACIONES: dict[str, Relacion] = {
    "TITULAR_DE": {
        "desde": ["Persona", "Empresa"], "hasta": ["Producto"],
        "dimension": "operacion", "fuente": "Core bancario · maestro de clientes"},
    "EMITIDO_POR": {
        "desde": ["Producto"], "hasta": ["Filial"],
        "dimension": "operacion", "fuente": "Catálogo de productos del grupo"},
    "GENERA": {
        "desde": ["Producto"], "hasta": ["Obligacion"],
        "dimension": "operacion", "fuente": "Sistema de cartera"},
    "CODEUDOR_DE": {
        "desde": ["Persona"], "hasta": ["Obligacion"],
        "dimension": "operacion", "fuente": "Expediente de crédito"},
    "RESPALDA": {
        "desde": ["Garantia"], "hasta": ["Obligacion"],
        "dimension": "operacion", "fuente": "Sistema de garantías y avalúos"},
    "REPRESENTA_A": {
        "desde": ["Persona"], "hasta": ["Empresa"],
        "dimension": "entidad", "fuente": "Cámara de Comercio · certificado"},
    "SOCIO_DE": {
        "desde": ["Persona"], "hasta": ["Empresa"],
        "dimension": "entidad", "fuente": "Cámara de Comercio · composición accionaria"},
    "MATRIZ_DE": {
        "desde": ["Empresa"], "hasta": ["Empresa"],
        "dimension": "entidad", "fuente": "Superintendencia de Sociedades"},
    "VINCULADO_A": {
        "desde": ["Persona"], "hasta": ["Persona"],
        "dimension": "entidad", "fuente": "Declaración de partes relacionadas"},
    "RESIDE_EN": {
        "desde": ["Persona"], "hasta": ["Ciudad"],
        "dimension": "geografica", "fuente": "CRM · datos de contacto"},
    "DOMICILIADA_EN": {
        "desde": ["Empresa"], "hasta": ["Ciudad"],
        "dimension": "geografica", "fuente": "RUT · domicilio fiscal"},
    "OPERA_EN": {
        "desde": ["Filial"], "hasta": ["Ciudad"],
        "dimension": "geografica", "fuente": "Red de oficinas"},
    "PERTENECE_A": {
        "desde": ["Ciudad"], "hasta": ["Region"],
        "dimension": "geografica", "fuente": "DANE · división territorial"},
    "VIGENTE_EN": {
        "desde": ["Obligacion"], "hasta": ["Periodo"],
        "dimension": "temporal", "fuente": "Cierre mensual de cartera"},
    "OCURRE_EN": {
        "desde": ["Evento"], "hasta": ["Periodo"],
        "dimension": "temporal", "fuente": "Bitácora de eventos"},
    "SIGUE_A": {
        "desde": ["Periodo"], "hasta": ["Periodo"],
        "dimension": "temporal", "fuente": "Calendario contable"},
    "AFECTA_A": {
        "desde": ["Evento"], "hasta": ["Persona", "Empresa", "Obligacion"],
        "dimension": "temporal", "fuente": "Bitácora de eventos"},
    "SUBTIPO_DE": {
        "desde": ["Concepto"], "hasta": ["Concepto"],
        "dimension": "semantica", "fuente": "Ontología de riesgo del grupo"},
    "REGULA": {
        "desde": ["Norma"], "hasta": ["Concepto"],
        "dimension": "semantica", "fuente": "Normograma corporativo"},
    "CLASIFICA_COMO": {
        "desde": ["Producto", "Garantia"], "hasta": ["Concepto"],
        "dimension": "semantica", "fuente": "Catálogo maestro de productos"},
    "TIPIFICA": {
        "desde": ["Evento"], "hasta": ["Concepto"],
        "dimension": "semantica", "fuente": "Motor de tipificación"},
    "CONTIENE": {
        "desde": ["Documento"], "hasta": ["Fragmento"],
        "dimension": "documental", "fuente": "Indexador documental"},
    "MENCIONA": {
        "desde": ["Fragmento"],
        "hasta": ["Persona", "Empresa", "Filial", "Concepto", "Norma"],
        "dimension": "documental", "fuente": "Extractor de entidades"},
    "DERIVA_DE": {
        "desde": ["Documento"], "hasta": ["Norma"],
        "dimension": "documental", "fuente": "Normograma corporativo"},
    "EVIDENCIA": {
        "desde": ["Fragmento"], "hasta": ["Evento"],
        "dimension": "documental", "fuente": "Extractor de entidades"},
}

# Umbral de politica del grupo: cuota mensual agregada sobre ingreso declarado.
TOPE_ENDEUDAMIENTO = 40.0


def etiquetas_de(dimension: str) -> list[str]:
    return [e for e, (d, _) in ETIQUETAS.items() if d == dimension]


def relaciones_de(dimension: str) -> list[str]:
    return [r for r, meta in RELACIONES.items() if meta["dimension"] == dimension]


def fuente_de(relacion: str) -> str:
    meta = RELACIONES.get(relacion)
    return meta["fuente"] if meta else "Registro interno"


def dimension_de_relacion(relacion: str) -> str:
    meta = RELACIONES.get(relacion)
    return meta["dimension"] if meta else "entidad"


def campo_nombre(etiqueta: str) -> str:
    return ETIQUETAS.get(etiqueta, ("entidad", "nombre"))[1]


def nombre_visible(nodo: dict) -> str:
    props = nodo.get("props") or nodo.get("properties") or {}
    campo = campo_nombre(str(nodo.get("label", "")))
    return str(props.get(campo) or props.get("nombre") or nodo.get("clave", ""))
