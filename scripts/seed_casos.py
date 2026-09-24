"""Segunda parte del generador: poblacion, casos plantados y corpus documental.

Se importa desde seed_kag.py para que el archivo principal no supere lo legible.
"""

from __future__ import annotations

import random
from typing import Any

import seed_kag as S


def poblar(n_personas: int = 1250, n_empresas: int = 170) -> None:
    rng = S.rng
    for i in range(1, n_personas + 1):
        S.crear_persona(i)
    for i in range(1, n_empresas + 1):
        S.crear_empresa(i)

    # Vinculos societarios: representante legal y socios.
    for emp in S.empresas:
        rep = rng.choice(S.personas)
        S.arista(rep, "REPRESENTA_A", emp)
        for socio in rng.sample(S.personas, rng.randint(1, 3)):
            S.arista(socio, "SOCIO_DE", emp)

    # Partes relacionadas declaradas entre personas.
    for _ in range(int(len(S.personas) * 0.22)):
        a, b = rng.sample(S.personas, 2)
        S.arista(a, "VINCULADO_A", b, tipo=rng.choice(
            ["Cónyuge", "Familiar en primer grado", "Socio comercial", "Codeudor habitual"]))

    # Productos de personas: la mayoria en una sola filial, algunos repartidos.
    for p in S.personas:
        cuantos = rng.choices([1, 2, 3, 4, 5], weights=[34, 30, 20, 11, 5])[0]
        for fil in rng.sample(S.filiales, min(cuantos, len(S.filiales))):
            S.crear_producto(p, fil, rng.choice(S.PRODUCTOS))

    # Productos de empresas.
    for e in S.empresas:
        for fil in rng.sample(S.filiales, rng.randint(1, 3)):
            S.crear_producto(e, fil, rng.choice(S.PRODUCTOS[2:9]))

    # Garantias sobre una parte de las obligaciones.
    for o in S.obligaciones:
        if rng.random() < 0.28:
            tipo = rng.choice(S.GARANTIAS)
            g = S.nodo(S._sig("gar"), "Garantia", tipo=tipo,
                       avaluo=o["saldo"] * rng.randint(1, 3),
                       admisible=tipo != "Codeudor solidario")
            S.arista(g, "RESPALDA", o["clave"])
            S.arista(g, "CLASIFICA_COMO", "cpt:consumo-garantizado")

    # Codeudores dispersos.
    for o in rng.sample(S.obligaciones, int(len(S.obligaciones) * 0.16)):
        S.arista(rng.choice(S.personas), "CODEUDOR_DE", o["clave"])


# ------------------------------------------------------------ casos plantados

def caso_persona_fragmentada() -> dict[str, Any]:
    """Nueve productos en seis filiales. Cada filial aprobo dentro de politica.

    El ultimo producto es el que cruza el tope: 39,8% -> 48,6%. Esa cifra no
    existe en ningun core porque exige sumar seis fuentes distintas.
    """
    rng = S.rng
    ingreso = 9_400_000
    clave = S.crear_persona(0, clave="psn:carlos",
                            nombre="Carlos Andrés Mejía Vargas",
                            ciudad="ciu:medellin", documento="71284593",
                            ingreso=ingreso, telefono="3104457812")

    seis = S.filiales[:6]
    # Calibrado para que la suma previa quede en 39,8% y el ultimo producto la
    # lleve a 48,6%: el salto ocurre exactamente con la novena apertura.
    plan = [
        (seis[0], S.PRODUCTOS[0], None, "2019-03-12", False),
        (seis[0], S.PRODUCTOS[3], 780_000, "2021-06-04", False),
        (seis[1], S.PRODUCTOS[2], 410_000, "2022-02-18", False),
        (seis[2], S.PRODUCTOS[5], 1_340_000, "2022-09-30", False),
        (seis[3], S.PRODUCTOS[4], 560_000, "2023-11-21", False),
        (seis[4], S.PRODUCTOS[8], 195_000, "2024-05-09", False),
        (seis[5], S.PRODUCTOS[10], 118_000, "2025-01-16", False),
        (seis[1], S.PRODUCTOS[6], 338_200, "2025-08-03", False),
        (seis[2], S.PRODUCTOS[2], 828_000, "2026-09-11", True),
    ]
    for filial, spec, cuota, apertura, nuevo in plan:
        S.crear_producto(clave, filial, spec, apertura=apertura,
                         nuevo=nuevo, cuota=cuota, mora=0)

    total = sum(c for _f, _s, c, _a, _n in plan if c)
    previa = sum(c for _f, _s, c, _a, n in plan if c and not n)
    return {
        "id": "persona-fragmentada", "clave": clave, "dimension": "operacion",
        "titulo": "Persona fragmentada en seis filiales",
        "endeudamiento": round(total / ingreso * 100, 1),
        "endeudamiento_previo": round(previa / ingreso * 100, 1),
        "productos": len(plan), "filiales": 6,
    }


def caso_identidad_duplicada() -> dict[str, Any]:
    """Tres registros, un digito de diferencia en el documento, mismo telefono."""
    base = "52871934"
    tel = "3157729014"
    claves = []
    for i, (suf, nombre) in enumerate([
        (base, "Marcela Liliana Quintero Rúa"),
        (base[:-1] + "5", "Marcela L. Quintero Rua"),
        ("0" + base[1:], "M. Liliana Quintero R."),
    ]):
        k = S.crear_persona(0, clave=f"psn:duplicada-{i+1}", nombre=nombre,
                            ciudad="ciu:cali", documento=suf,
                            ingreso=6_200_000 + i * 40_000, telefono=tel)
        claves.append(k)
        S.crear_producto(k, S.filiales[i % 3], S.PRODUCTOS[3 + i % 3])
    return {"id": "identidad-duplicada", "clave": claves[0], "dimension": "entidad",
            "titulo": "Tres registros que son la misma persona",
            "registros": claves, "telefono_comun": tel}


def caso_grupo_economico() -> dict[str, Any]:
    """Una matriz, cuatro operativas y un representante legal que las une."""
    rng = S.rng
    matriz = S.crear_empresa(0, clave="emp:matriz-altamar",
                             nombre="Inversiones Altamar Holding S.A.S.",
                             ciudad="ciu:barranquilla")
    rep = S.crear_persona(0, clave="psn:rep-altamar",
                          nombre="Germán Eduardo Rentería Solano",
                          ciudad="ciu:barranquilla", ingreso=31_000_000)
    S.arista(rep, "REPRESENTA_A", matriz)

    hijas = []
    nivel = [matriz]
    for n, nombre in enumerate([
        "Comercializadora Altamar S.A.S.", "Transportes Altamar S.A.S.",
        "Agropecuaria Altamar S.A.S.", "Constructora Altamar S.A.S.",
    ]):
        h = S.crear_empresa(0, clave=f"emp:altamar-{n+1}", nombre=nombre,
                            ciudad=rng.choice(S.ciudades))
        padre = nivel[-1] if n == 3 else matriz  # una nieta, para dar profundidad
        S.arista(padre, "MATRIZ_DE", h)
        S.arista(rep, "REPRESENTA_A", h)
        nivel.append(h)
        hijas.append(h)
        for fil in rng.sample(S.filiales, 2):
            S.crear_producto(h, fil, S.PRODUCTOS[rng.randint(2, 8)],
                             cuota=rng.randrange(2_000_000, 7_000_000, 100_000))
    return {"id": "grupo-economico", "clave": matriz, "dimension": "entidad",
            "titulo": "Grupo económico con profundidad desconocida",
            "operativas": hijas, "representante": rep}


def caso_codeudor_oculto() -> dict[str, Any]:
    """Una cuenta de ahorros de 2 millones que avala siete obligaciones ajenas."""
    rng = S.rng
    clave = S.crear_persona(0, clave="psn:avalista",
                            nombre="Wilson Fabián Cadavid Hoyos",
                            ciudad="ciu:pereira", ingreso=4_100_000)
    S.crear_producto(clave, S.filiales[0], S.PRODUCTOS[0], apertura="2020-04-02")
    avaladas = rng.sample([o for o in S.obligaciones if o["saldo"] > 20_000_000], 7)
    for o in avaladas:
        S.arista(clave, "CODEUDOR_DE", o["clave"])
    return {"id": "codeudor-oculto", "clave": clave, "dimension": "operacion",
            "titulo": "Exposición indirecta que no está en su ficha",
            "obligaciones": len(avaladas),
            "saldo_avalado": sum(o["saldo"] for o in avaladas)}


def caso_concentracion() -> dict[str, Any]:
    """Una ciudad intermedia con exposicion desproporcionada a un solo sector."""
    rng = S.rng
    ciudad = "ciu:valledupar"
    creadas = []
    for i in range(38):
        p = S.crear_persona(0, clave=f"psn:conc-{i+1:03d}", ciudad=ciudad,
                            ingreso=rng.randrange(2_000_000, 5_000_000, 50_000))
        creadas.append(p)
        S.crear_producto(p, S.filiales[3], S.PRODUCTOS[6],
                         cuota=rng.randrange(900_000, 1_700_000, 10_000))
    return {"id": "concentracion-territorial", "clave": ciudad,
            "dimension": "geografica",
            "titulo": "Concentración de libranza en una plaza",
            "personas": len(creadas)}


def eventos(casos: list[dict]) -> None:
    """Dimension temporal: lo que paso, cuando y como se tipifica."""
    rng = S.rng
    catalogo = [
        ("Apertura de producto", "informativa", "cpt:credito"),
        ("Incremento de cupo", "media", "cpt:rotativo"),
        ("Primer pago en mora", "media", "cpt:mora"),
        ("Mora superior a 60 días", "alta", "cpt:mora"),
        ("Actualización de datos de contacto", "informativa", "cpt:identidad"),
        ("Revisión de capacidad de pago", "media", "cpt:sobreendeudamiento"),
        ("Alerta de concentración", "alta", "cpt:concentracion"),
        ("Declaración de parte relacionada", "media", "cpt:vinculado"),
    ]
    objetivos = (rng.sample(S.personas, 220) + rng.sample(S.empresas, 60)
                 + [c["clave"] for c in casos if c["clave"].startswith(("psn:", "emp:"))])
    for obj in objetivos:
        for _ in range(rng.randint(1, 3)):
            titulo, sev, cpt = rng.choice(catalogo)
            ev = S.nodo(S._sig("evt"), "Evento", titulo=titulo, severidad=sev,
                        detalle=f"{titulo} registrado por el motor de seguimiento.")
            S.arista(ev, "AFECTA_A", obj)
            S.arista(ev, "OCURRE_EN", rng.choice(S.periodos))
            S.arista(ev, "TIPIFICA", cpt)

    # El evento que dispara el caso de tarima.
    ev = S.nodo(S._sig("evt"), "Evento",
                titulo="Aprobación de tarjeta de crédito sin visión de grupo",
                severidad="alta",
                detalle=("La filial aprobó con 12% de endeudamiento calculado sobre "
                         "su propio core. El agregado del grupo era 39,8%."))
    S.arista(ev, "AFECTA_A", "psn:carlos")
    S.arista(ev, "OCURRE_EN", S.periodos[-1])
    S.arista(ev, "TIPIFICA", "cpt:sobreendeudamiento")
