"""Genera el grafo de conocimiento multidimensional de ATLAS.

Semilla fija -> salida determinista. Produce tres artefactos en `data/`:

    grafo.json        nodos y aristas de las seis dimensiones
    documentos.json   corpus con sus fragmentos y las entidades que mencionan
    embeddings.npz    el embebedor entrenado sobre ese corpus

Los casos plantados no son adorno: cada uno existe para que una consulta
concreta tenga una respuesta que solo el recorrido produce.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "apps" / "api"))
DATA = RAIZ / "data"

from kag.embeddings import Embebedor  # noqa: E402
from kag.ontologia import RELACIONES  # noqa: E402

SEMILLA = 20260921
HOY = date(2026, 9, 21)
rng = random.Random(SEMILLA)

nodos: list[dict] = []
aristas: list[dict] = []
_vistos: set[str] = set()


def nodo(clave: str, label: str, **props) -> str:
    if clave not in _vistos:
        _vistos.add(clave)
        nodos.append({"clave": clave, "label": label,
                      "props": {k: v for k, v in props.items() if v is not None}})
    return clave


def arista(desde: str, relacion: str, hasta: str, **props) -> None:
    meta = RELACIONES[relacion]
    aristas.append({"desde": desde, "relacion": relacion, "hasta": hasta,
                    "props": {"fuente": meta["fuente"],
                              "dimension": meta["dimension"], **props}})


# --------------------------------------------------------------- vocabulario

NOMBRES = """Andrés Camila Santiago Valentina Julián Daniela Mateo Laura Sebastián Manuela
Nicolás Sofía Felipe Isabella Alejandro Mariana Diego Paula Catalina Esteban Gabriela
Ricardo Natalia Óscar Adriana Fernando Carolina Álvaro Ximena Gustavo Lorena Hernán
Beatriz Iván Marcela Rodrigo Liliana Camilo Verónica Jorge Patricia Mauricio Claudia
Diana Germán Ángela Wilson Yolanda Édgar Sandra Fabián Tatiana Leonardo Mónica Raúl""".split()

APELLIDOS = """Restrepo Gutiérrez Osorio Cárdenas Valderrama Zapata Montoya Quintero
Arango Betancur Peláez Salazar Ocampo Jaramillo Hoyos Mejía Vélez Ramírez Cadavid
Escobar Guerrero Barrios Mosquera Palacios Rentería Córdoba Ariza Bermúdez Chaparro
Buitrago Sarmiento Malagón Cuéllar Solano Villamizar Pardo Contreras Lozano Trujillo
Rincón Camargo Acevedo Ballesteros Rueda Serrano Amaya Nieto Cifuentes Parra""".split()

REGIONES = {
    "Andina": ["Bogotá", "Medellín", "Bucaramanga", "Manizales", "Ibagué", "Tunja"],
    "Caribe": ["Barranquilla", "Cartagena", "Santa Marta", "Valledupar"],
    "Pacífica": ["Cali", "Buenaventura", "Pasto", "Quibdó"],
    "Orinoquía": ["Villavicencio", "Yopal"],
    "Eje Cafetero": ["Pereira", "Armenia"],
}

FILIALES = [
    ("Banco Meridiano", "Banco comercial", "Core Altair"),
    ("Banco del Litoral", "Banco comercial", "Core Bancs"),
    ("Banco Andino", "Banco comercial", "Core Topaz"),
    ("Financiera Cumbre", "Compañía de financiamiento", "Core Sirius"),
    ("Leasing Cordillera", "Leasing", "Core Vega"),
    ("Fiduciaria Meridiano", "Fiduciaria", "Core Fidu"),
    ("Pensiones Horizonte", "Fondo de pensiones", "Core Afore"),
    ("Seguros Meridiano", "Aseguradora", "Core Póliza"),
    ("Meridiano Valores", "Comisionista de bolsa", "Core Bursa"),
]

# (tipo, genera obligacion, cuota min, cuota max, concepto)
PRODUCTOS = [
    ("Cuenta de ahorros", False, 0, 0, "cpt:deposito-vista"),
    ("Cuenta corriente", False, 0, 0, "cpt:deposito-vista"),
    ("Tarjeta de crédito", True, 180_000, 2_400_000, "cpt:rotativo"),
    ("Crédito de libre inversión", True, 350_000, 3_100_000, "cpt:consumo"),
    ("Crédito de vehículo", True, 700_000, 2_600_000, "cpt:consumo-garantizado"),
    ("Crédito hipotecario", True, 1_200_000, 4_800_000, "cpt:vivienda"),
    ("Crédito de libranza", True, 300_000, 1_900_000, "cpt:consumo"),
    ("Leasing habitacional", True, 900_000, 3_400_000, "cpt:vivienda"),
    ("Cupo rotativo", True, 120_000, 1_400_000, "cpt:rotativo"),
    ("CDT", False, 0, 0, "cpt:deposito-plazo"),
    ("Póliza de vida", True, 90_000, 420_000, "cpt:seguro"),
    ("Portafolio de inversión", False, 0, 0, "cpt:inversion"),
]

SECTORES = ["Comercio al por mayor", "Construcción", "Agroindustria", "Transporte",
            "Salud", "Educación", "Tecnología", "Manufactura", "Turismo", "Alimentos"]

EMPRESA_1 = ("Inversiones Comercializadora Distribuidora Constructora Agropecuaria "
             "Transportes Servicios Industrias Soluciones Grupo Corporación").split()
EMPRESA_2 = ["del Caribe", "Andina", "del Pacífico", "de los Andes", "Altamar",
             "Santa Bárbara", "del Llano", "La Esperanza", "Monteverde",
             "San Rafael", "del Norte", "Cordillera", "Buenavista"]

GARANTIAS = ["Hipoteca sobre inmueble", "Prenda sobre vehículo", "Codeudor solidario",
             "Fondo Nacional de Garantías", "Pignoración de CDT", "Aval bancario"]


# ------------------------------------------------- dimension semantica: ontologia

CONCEPTOS = [
    ("cpt:credito", "Crédito", None),
    ("cpt:consumo", "Crédito de consumo", "cpt:credito"),
    ("cpt:consumo-garantizado", "Consumo con garantía", "cpt:consumo"),
    ("cpt:rotativo", "Crédito rotativo", "cpt:consumo"),
    ("cpt:vivienda", "Crédito de vivienda", "cpt:credito"),
    ("cpt:deposito", "Captación", None),
    ("cpt:deposito-vista", "Depósito a la vista", "cpt:deposito"),
    ("cpt:deposito-plazo", "Depósito a término", "cpt:deposito"),
    ("cpt:inversion", "Inversión", None),
    ("cpt:seguro", "Seguro de personas", None),
    ("cpt:riesgo", "Riesgo", None),
    ("cpt:riesgo-credito", "Riesgo de crédito", "cpt:riesgo"),
    ("cpt:sobreendeudamiento", "Sobreendeudamiento", "cpt:riesgo-credito"),
    ("cpt:concentracion", "Concentración", "cpt:riesgo-credito"),
    ("cpt:riesgo-operativo", "Riesgo operativo", "cpt:riesgo"),
    ("cpt:identidad", "Calidad de identidad", "cpt:riesgo-operativo"),
    ("cpt:vinculado", "Parte relacionada", "cpt:riesgo-credito"),
    ("cpt:mora", "Deterioro por mora", "cpt:riesgo-credito"),
]

NORMAS = [
    ("nrm:pol-endeudamiento", "Política de endeudamiento agregado",
     "Vicepresidencia de Riesgo", "2026-01-15", "cpt:sobreendeudamiento"),
    ("nrm:cir-limites", "Circular de límites individuales de exposición",
     "Junta Directiva", "2025-11-03", "cpt:concentracion"),
    ("nrm:man-credito", "Manual de originación de crédito",
     "Gerencia de Crédito", "2025-08-20", "cpt:credito"),
    ("nrm:pol-consumo", "Política de crédito de consumo",
     "Gerencia de Crédito", "2026-02-10", "cpt:consumo"),
    ("nrm:pol-vivienda", "Política de financiación de vivienda",
     "Gerencia de Crédito", "2025-06-30", "cpt:vivienda"),
    ("nrm:cir-identidad", "Circular de calidad de datos de identidad",
     "Comité de Datos", "2026-03-05", "cpt:identidad"),
    ("nrm:pol-vinculados", "Política de operaciones con partes relacionadas",
     "Junta Directiva", "2025-09-12", "cpt:vinculado"),
    ("nrm:man-cobranza", "Manual de cobranza y deterioro",
     "Gerencia de Cartera", "2026-01-28", "cpt:mora"),
    ("nrm:pol-captacion", "Política de captación",
     "Tesorería", "2025-07-14", "cpt:deposito"),
    ("nrm:cir-garantias", "Circular de admisibilidad de garantías",
     "Vicepresidencia de Riesgo", "2025-12-01", "cpt:consumo-garantizado"),
]


def construir_semantica() -> None:
    for clave, nombre, padre in CONCEPTOS:
        nodo(clave, "Concepto", nombre=nombre, raiz=padre is None)
    for clave, _n, padre in CONCEPTOS:
        if padre:
            arista(clave, "SUBTIPO_DE", padre)
    for clave, titulo, emisor, vigencia, concepto in NORMAS:
        nodo(clave, "Norma", titulo=titulo, emisor=emisor, vigencia=vigencia)
        arista(clave, "REGULA", concepto)


# ------------------------------------------- dimensiones geografica y temporal

ciudades: list[str] = []


def construir_geografia() -> None:
    for region, lista in REGIONES.items():
        rclave = nodo(f"reg:{_slug(region)}", "Region", nombre=region)
        for c in lista:
            cclave = nodo(f"ciu:{_slug(c)}", "Ciudad", nombre=c, region=region)
            arista(cclave, "PERTENECE_A", rclave)
            ciudades.append(cclave)


periodos: list[str] = []


def construir_tiempo(meses: int = 24) -> None:
    anterior = None
    y, m = 2024, 10
    for orden in range(meses):
        clave = f"per:{y}-{m:02d}"
        etiqueta = f"{y}-{m:02d}"
        nodo(clave, "Periodo", etiqueta=etiqueta, anio=y, mes=m, orden=orden)
        if anterior:
            arista(clave, "SIGUE_A", anterior)
        anterior = clave
        periodos.append(clave)
        m += 1
        if m > 12:
            m, y = 1, y + 1


# ---------------------------------------------------- dimension entidad y operacion

filiales: list[str] = []
personas: list[str] = []
empresas: list[str] = []
productos: list[dict] = []
obligaciones: list[dict] = []


def _slug(texto: str) -> str:
    import unicodedata
    base = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() else "-" for c in base).strip("-")


def construir_filiales() -> None:
    for i, (nombre, tipo, core) in enumerate(FILIALES):
        clave = nodo(f"fil:{_slug(nombre)}", "Filial", nombre=nombre, tipo=tipo,
                     core=core, codigo=f"F{i+1:02d}")
        filiales.append(clave)
        for c in rng.sample(ciudades, rng.randint(4, 9)):
            arista(clave, "OPERA_EN", c)


def _documento() -> str:
    return str(rng.randint(10_000_000, 1_299_999_999))


def crear_persona(idx: int, *, clave: str | None = None, nombre: str | None = None,
                  ciudad: str | None = None, documento: str | None = None,
                  ingreso: int | None = None, telefono: str | None = None) -> str:
    nom = nombre or f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}"
    ciu = ciudad or rng.choice(ciudades)
    ing = ingreso or rng.randrange(1_600_000, 22_000_000, 50_000)
    tel = telefono or f"3{rng.randint(10, 24)}{rng.randint(1000000, 9999999)}"
    k = nodo(clave or f"psn:{idx:05d}", "Persona",
             nombre=nom, documento=documento or _documento(),
             ingresoMensual=ing, telefono=tel,
             segmento=("Preferencial" if ing > 12_000_000
                       else "Personal" if ing > 4_000_000 else "Masivo"),
             correo=f"{_slug(nom.split()[0])}.{_slug(nom.split()[-1])}@correo.co")
    arista(k, "RESIDE_EN", ciu)
    personas.append(k)
    return k


def crear_empresa(idx: int, *, clave: str | None = None, nombre: str | None = None,
                  ciudad: str | None = None) -> str:
    nom = nombre or f"{rng.choice(EMPRESA_1)} {rng.choice(EMPRESA_2)} S.A.S."
    k = nodo(clave or f"emp:{idx:04d}", "Empresa", nombre=nom,
             nit=f"9{rng.randint(10_000_000, 99_999_999)}",
             sector=rng.choice(SECTORES),
             constitucion=f"{rng.randint(1995, 2024)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}")
    arista(k, "DOMICILIADA_EN", ciudad or rng.choice(ciudades))
    empresas.append(k)
    return k


_seq = {"pro": 0, "obl": 0, "gar": 0, "evt": 0}


def _sig(pref: str) -> str:
    _seq[pref] += 1
    return f"{pref}:{_seq[pref]:05d}"


def crear_producto(titular: str, filial: str, spec: tuple, *,
                   apertura: str | None = None, nuevo: bool = False,
                   cuota: int | None = None, mora: int | None = None) -> dict:
    tipo, genera, cmin, cmax, concepto = spec
    pclave = nodo(_sig("pro"), "Producto", tipo=tipo,
                  numero=f"{rng.randint(1000,9999)}-{rng.randint(100000,999999)}",
                  apertura=apertura or _fecha_aleatoria(), nuevo=nuevo)
    arista(titular, "TITULAR_DE", pclave)
    arista(pclave, "EMITIDO_POR", filial)
    arista(pclave, "CLASIFICA_COMO", concepto)
    registro = {"clave": pclave, "tipo": tipo, "filial": filial, "titular": titular,
                "obligacion": None}
    productos.append(registro)

    if genera:
        c = cuota if cuota is not None else rng.randrange(cmin, cmax, 10_000)
        saldo = c * rng.randint(8, 72)
        dias = mora if mora is not None else (rng.choice([0, 0, 0, 0, 15, 30, 60, 90])
                                              if rng.random() < 0.18 else 0)
        oclave = nodo(_sig("obl"), "Obligacion",
                      referencia=f"OBL-{_seq['obl']:06d}",
                      cuotaMensual=c, saldo=saldo, diasMora=dias,
                      calificacion=_calificacion(dias))
        arista(pclave, "GENERA", oclave)
        for p in periodos[-rng.randint(3, 18):]:
            arista(oclave, "VIGENTE_EN", p)
        registro["obligacion"] = oclave
        obligaciones.append({"clave": oclave, "producto": pclave, "filial": filial,
                             "titular": titular, "saldo": saldo, "mora": dias})
    return registro


def _calificacion(dias: int) -> str:
    return ("A" if dias == 0 else "B" if dias <= 30 else
            "C" if dias <= 60 else "D" if dias <= 90 else "E")


def _fecha_aleatoria() -> str:
    y = rng.randint(2019, 2026)
    m = rng.randint(1, 12 if y < 2026 else 9)
    return f"{y}-{m:02d}-{rng.randint(1, 28):02d}"


# ------------------------------------------------- dimension documental en grafo

def incorporar_documentos(documentos: list[dict]) -> None:
    """Los documentos tambien son nodos: asi la evidencia es recorrible."""
    for d in documentos:
        dclave = nodo(d["clave"], "Documento", titulo=d["titulo"], tipo=d["tipo"],
                      fuente=d["fuente"], fecha=d["fecha"])
        arista(dclave, "DERIVA_DE", d["norma"])
        for f in d["fragmentos"]:
            fclave = nodo(f["clave"], "Fragmento", titulo=f["titulo"],
                          dimension=f["dimension"], longitud=len(f["texto"]))
            arista(dclave, "CONTIENE", fclave)
            for ent in f["entidades"]:
                if ent in _vistos:
                    arista(fclave, "MENCIONA", ent)


# ------------------------------------------------------------------------ main

def main() -> int:
    import seed_casos
    import seed_documentos

    construir_semantica()
    construir_geografia()
    construir_tiempo()
    construir_filiales()
    print(f"· estructura base: {len(nodos)} nodos")

    seed_casos.poblar()
    print(f"· población: {len(nodos)} nodos · {len(aristas)} aristas")

    casos = [
        seed_casos.caso_persona_fragmentada(),
        seed_casos.caso_identidad_duplicada(),
        seed_casos.caso_grupo_economico(),
        seed_casos.caso_codeudor_oculto(),
        seed_casos.caso_concentracion(),
    ]
    seed_casos.eventos(casos)
    print(f"· casos y eventos: {len(nodos)} nodos · {len(aristas)} aristas")

    documentos = seed_documentos.construir()
    incorporar_documentos(documentos)
    print(f"· corpus: {len(documentos)} documentos · "
          f"{sum(len(d['fragmentos']) for d in documentos)} fragmentos")

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "grafo.json").write_text(json.dumps(
        {"nodos": nodos, "aristas": aristas, "casos": casos},
        ensure_ascii=False), "utf-8")
    (DATA / "documentos.json").write_text(json.dumps(documentos, ensure_ascii=False),
                                          "utf-8")

    textos = [f"{f['titulo']} {f['texto']}"
              for d in documentos for f in d["fragmentos"]]
    claves = [f["clave"] for d in documentos for f in d["fragmentos"]]
    embebedor = Embebedor.entrenar(textos, dimensiones=256)
    embebedor.guardar(DATA / "embeddings.npz")
    matriz = embebedor.lote(textos)
    (DATA / "vectores.json").write_text(json.dumps(
        {c: [round(float(x), 6) for x in v] for c, v in zip(claves, matriz)}),
        "utf-8")
    print(f"· embebedor: {embebedor.dimensiones} dimensiones · "
          f"{len(embebedor.vocabulario)} términos")

    verificar(casos)
    print(f"\nGrafo: {len(nodos)} nodos · {len(aristas)} aristas · "
          f"{len({n['label'] for n in nodos})} etiquetas")
    return 0


def verificar(casos: list[dict]) -> None:
    fragmentado = next(c for c in casos if c["id"] == "persona-fragmentada")
    assert fragmentado["endeudamiento_previo"] < 40.0 <= fragmentado["endeudamiento"], (
        "El caso de tarima debe cruzar el tope exactamente con el último producto: "
        f"{fragmentado['endeudamiento_previo']}% → {fragmentado['endeudamiento']}%")
    claves = {n["clave"] for n in nodos}
    faltan = {a["desde"] for a in aristas} | {a["hasta"] for a in aristas}
    assert faltan <= claves, f"Aristas apuntando a nodos inexistentes: {faltan - claves}"
    print(f"· verificación: endeudamiento {fragmentado['endeudamiento_previo']}% → "
          f"{fragmentado['endeudamiento']}% (tope 40%)")
