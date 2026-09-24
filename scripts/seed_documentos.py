"""Corpus documental y su vectorizacion.

El corpus es honesto: son normas, actas, informes y memorandos reales en forma y
tono. La busqueda semantica funciona bien contra ellos cuando la pregunta es
sobre *la norma*.

Lo que ningun documento contiene es la cifra agregada de una persona a traves de
varias filiales, porque esa cifra nunca fue redactada: existe solo como aristas.
Se verifica explicitamente al final de `construir()`.
"""

from __future__ import annotations

from typing import Any

import seed_kag as S

# La filial que aprobo el ultimo producto del caso de tarima. Ningun fragmento
# puede mencionarla junto con la persona: es lo que hace fallar al RAG puro.
FILIAL_PROHIBIDA = "fil:banco-andino"
PERSONA_PROHIBIDA = "psn:carlos"

PLANTILLAS_NORMA = [
    ("Objeto y alcance",
     "Este documento fija los lineamientos aplicables a {concepto} en todas las "
     "filiales del grupo. Comprende los criterios de admisión, los límites de "
     "{lexico2} y las atribuciones de aprobación. Su cumplimiento es obligatorio para "
     "originación, seguimiento y cobranza, y su interpretación corresponde a {emisor}."),
    ("Criterios de admisión",
     "La evaluación considera {lexico3}. No se admiten operaciones que superen el "
     "{tope}% de relación cuota ingreso ni aquellas cuya {riesgo} estimada exceda la "
     "{riesgo2} definida por la Junta. Las excepciones requieren concepto favorable "
     "del comité y quedan sujetas a revisión trimestral."),
    ("Medición y control",
     "El área de riesgo calcula mensualmente los indicadores asociados a {concepto} y "
     "los contrasta contra el apetito aprobado. Cualquier desviación superior al "
     "{pct}% se escala al comité en la sesión inmediatamente siguiente."),
    ("Responsabilidades",
     "{emisor} mantiene actualizado este documento y reporta sus indicadores al comité "
     "de riesgo. Cada filial designa un responsable de su aplicación y de la calidad "
     "de los datos que alimentan el cálculo de {concepto}."),
    ("Vigencia y revisión",
     "Rige a partir del {vigencia} y se revisa al menos una vez al año, o antes si "
     "cambian las condiciones de mercado o la regulación aplicable a {concepto}."),
]

PLANTILLAS_ACTA = [
    ("Instalación y quórum",
     "Siendo las {hora} se instala el comité con asistencia de los representantes de "
     "{filial} y de la Vicepresidencia de Riesgo. Verificado el quórum, se aprueba el "
     "orden del día y se da lectura al acta anterior."),
    ("Seguimiento de cartera",
     "Se presenta el comportamiento de la cartera de {filial} en {ciudad}. La cosecha "
     "de {mes} muestra una variación del {pct}% en {lexico2}. Al respecto, {hallazgo}."),
    ("Discusión",
     "Los miembros debaten el efecto de {lexico3} sobre la {riesgo} del portafolio. Se "
     "solicita profundizar el análisis de {concepto} para el próximo corte y "
     "contrastarlo con lo dispuesto en {norma}."),
    ("Decisiones",
     "El comité aprueba mantener los límites vigentes para {concepto} y encarga a "
     "{filial} {accion}. Se reitera la aplicación de {norma} y se fija seguimiento "
     "para la próxima sesión."),
]

PLANTILLAS_INFORME = [
    ("Resumen ejecutivo",
     "El saldo administrado por {filial} en {ciudad} varió {pct}% frente al periodo "
     "anterior. Los indicadores de {lexico2} se mantienen dentro de los rangos "
     "definidos para {concepto}."),
    ("Composición del portafolio",
     "La cartera se concentra en productos clasificados como {concepto}. La "
     "participación de operaciones con garantía admisible permanece estable y se "
     "ajusta a lo previsto en {norma}. La {riesgo} calculada no presenta variaciones "
     "materiales."),
    ("Comportamiento regional",
     "En la región {region}, y particularmente en {ciudad}, se observa un "
     "comportamiento diferenciado en {lexico2}. {hallazgo}."),
    ("Recomendaciones",
     "Se recomienda {accion} y revisar la exposición asociada a {concepto} durante el "
     "siguiente trimestre, con reporte al comité de {filial}."),
]

PLANTILLAS_MEMO = [
    ("Antecedentes",
     "Se recibe solicitud de análisis sobre la exposición de {empresa}, del sector "
     "{sector}, domiciliada en {ciudad}, en el marco de {norma}."),
    ("Análisis",
     "La operación se clasifica como {concepto}. Se evaluaron {lexico3} y se verificó "
     "la coherencia de la información financiera aportada. La {riesgo} estimada "
     "resulta compatible con el perfil declarado por {empresa}."),
    ("Observaciones",
     "{hallazgo}. Se deja constancia de que el expediente de {empresa} deberá "
     "actualizarse conforme al calendario definido por {emisor}."),
    ("Concepto",
     "Se emite concepto favorable condicionado al cumplimiento de los límites "
     "definidos para {concepto} y a {accion}."),
]

PLANTILLAS_VISITA = [
    ("Objetivo de la visita",
     "Se realiza visita comercial a {persona} en {ciudad} para actualizar la "
     "información del expediente y evaluar necesidades de producto."),
    ("Hallazgos",
     "Se verificó la información de contacto registrada en el {core}. {persona} "
     "manifiesta interés en productos asociados a {concepto} y aporta soportes de "
     "ingreso. {hallazgo}."),
    ("Siguiente paso",
     "Se remite el expediente a {filial} para el estudio correspondiente conforme a "
     "{norma}, previa validación de {lexico2}."),
]

PLANTILLAS_JURIDICO = [
    ("Consulta",
     "Se consulta sobre la aplicación de {norma} a operaciones de {concepto} "
     "celebradas por {filial}."),
    ("Marco aplicable",
     "El análisis parte de {norma}, expedida por {emisor} con vigencia desde el "
     "{vigencia}, y de las disposiciones internas sobre {lexico2}."),
    ("Consideraciones",
     "La obligación de revelar {lexico2} subsiste con independencia de la cuantía. La "
     "ausencia de registro no sanea la operación ni traslada la {riesgo} a un tercero."),
    ("Conclusión",
     "Se concluye que la operación es viable siempre que se documente el cumplimiento "
     "de {concepto} y se proceda a {accion}."),
]

# Vocabulario por concepto. Es lo que hace que dos documentos sobre temas
# distintos no se parezcan entre si: sin esto el corpus seria una plantilla
# repetida y el comparativo entre RAG y KAG no probaria nada.
LEXICO = {
    "cpt:sobreendeudamiento": [
        "capacidad de pago", "relación cuota ingreso", "carga financiera",
        "ingreso disponible", "holgura presupuestal", "nivel de apalancamiento"],
    "cpt:concentracion": [
        "límite individual", "cupo máximo", "exposición agregada",
        "diversificación del portafolio", "grupo de riesgo único", "tope sectorial"],
    "cpt:credito": [
        "originación", "estudio de crédito", "análisis del deudor",
        "perfil de riesgo", "aprobación escalonada", "atribuciones de aprobación"],
    "cpt:consumo": [
        "libre inversión", "destinación no específica", "plazo máximo",
        "tasa de interés corriente", "seguro de vida deudores"],
    "cpt:vivienda": [
        "valor del inmueble", "relación préstamo garantía", "avalúo comercial",
        "leasing habitacional", "subsidio de vivienda", "unidad de valor real"],
    "cpt:identidad": [
        "unicidad del registro", "depuración de duplicados", "documento de identidad",
        "dato de contacto verificado", "conciliación entre cores", "llave maestra"],
    "cpt:vinculado": [
        "parte relacionada", "beneficiario real", "control efectivo",
        "conflicto de interés", "operación entre vinculadas", "revelación obligatoria"],
    "cpt:mora": [
        "altura de mora", "cosecha", "provisión individual", "castigo de cartera",
        "gestión de cobranza prejurídica", "acuerdo de pago"],
    "cpt:deposito": [
        "captación del público", "encaje", "tasa de remuneración",
        "liquidez estructural", "renovación automática"],
    "cpt:consumo-garantizado": [
        "garantía admisible", "cobertura de la garantía", "prenda sin tenencia",
        "hipoteca de primer grado", "actualización de avalúos"],
}

HALLAZGOS = [
    "se identificó una desviación menor frente al procedimiento vigente",
    "la documentación soporte se encuentra completa y archivada",
    "persisten diferencias de criterio entre originación y seguimiento",
    "el indicador se mantiene dentro del apetito de riesgo aprobado",
    "se observa una tendencia creciente que amerita seguimiento cercano",
    "la muestra revisada no arrojó excepciones materiales",
    "se detectaron registros con información desactualizada en el maestro",
    "la trazabilidad de la decisión quedó debidamente sustentada",
]

ACCIONES = [
    "fortalecer los controles de primera línea",
    "actualizar el modelo de calificación interna",
    "capacitar a la fuerza comercial en los criterios de admisión",
    "automatizar la validación cruzada entre sistemas",
    "revisar la parametrización de los cupos preaprobados",
    "documentar las excepciones en el acta correspondiente",
    "ajustar la periodicidad del reporte al comité",
]

RIESGOS = [
    "pérdida esperada", "severidad", "probabilidad de incumplimiento",
    "exposición al momento del incumplimiento", "correlación sectorial",
    "riesgo residual", "apetito de riesgo", "tolerancia definida",
]

TIPOS = {
    "Política": (PLANTILLAS_NORMA, "semantica", 20),
    "Acta de comité": (PLANTILLAS_ACTA, "semantica", 18),
    "Informe de cartera": (PLANTILLAS_INFORME, "operacion", 22),
    "Memorando de riesgo": (PLANTILLAS_MEMO, "entidad", 16),
    "Reporte de visita": (PLANTILLAS_VISITA, "entidad", 12),
    "Concepto jurídico": (PLANTILLAS_JURIDICO, "semantica", 12),
}


def _lexico(concepto: str, n: int) -> str:
    base = LEXICO.get(concepto) or LEXICO["cpt:credito"]
    return ", ".join(S.rng.sample(base, min(n, len(base))))


def construir(n_documentos: int = 260) -> list[dict[str, Any]]:
    rng = S.rng
    nombres = {n["clave"]: n["props"] for n in S.nodos}
    docs: list[dict[str, Any]] = []
    frag_seq = 0

    etiquetas = list(TIPOS)
    pesos = [TIPOS[t][2] for t in etiquetas]

    for i in range(1, n_documentos + 1):
        tipo = rng.choices(etiquetas, weights=pesos)[0]
        plantillas, dim, _ = TIPOS[tipo]
        norma = rng.choice(S.NORMAS)
        concepto_clave = norma[4]
        filial = rng.choice(S.filiales)
        ciudad = rng.choice(S.ciudades)
        empresa = rng.choice(S.empresas)
        persona = rng.choice(S.personas)

        ctx = {
            "concepto": nombres[concepto_clave]["nombre"],
            "emisor": norma[2], "vigencia": norma[3], "norma": norma[1], "tope": 40,
            "filial": nombres[filial]["nombre"],
            "core": nombres[filial].get("core", ""),
            "ciudad": nombres[ciudad]["nombre"],
            "region": nombres[ciudad].get("region", ""),
            "empresa": nombres[empresa]["nombre"],
            "sector": nombres[empresa].get("sector", ""),
            "persona": nombres[persona]["nombre"],
            "hora": f"{rng.randint(8, 16)}:{rng.choice(['00', '30'])}",
            "lexico3": _lexico(concepto_clave, 3),
            "lexico2": _lexico(concepto_clave, 2),
            "hallazgo": rng.choice(HALLAZGOS),
            "accion": rng.choice(ACCIONES),
            "riesgo": rng.choice(RIESGOS),
            "riesgo2": rng.choice(RIESGOS),
            "pct": rng.randint(3, 28),
            "mes": rng.choice(["enero", "marzo", "abril", "junio", "agosto",
                               "septiembre", "noviembre"]),
        }
        mencionados = {concepto_clave, norma[0]}
        if tipo in ("Acta de comité", "Informe de cartera", "Reporte de visita",
                    "Concepto jurídico"):
            mencionados.add(filial)
        if tipo == "Memorando de riesgo":
            mencionados.add(empresa)
        if tipo == "Reporte de visita":
            mencionados.add(persona)

        titulo = {
            "Política": f"{tipo} · {norma[1]}",
            "Memorando de riesgo": f"{tipo} · {ctx['empresa']}",
            "Reporte de visita": f"{tipo} · {ctx['ciudad']}",
        }.get(tipo, f"{tipo} · {ctx['filial']}")

        fragmentos = []
        for sub, plantilla in plantillas:
            frag_seq += 1
            fragmentos.append({
                "clave": f"frg:{frag_seq:05d}",
                "titulo": f"{titulo} — {sub}",
                "texto": plantilla.format(**ctx),
                "dimension": dim,
                "entidades": sorted(mencionados),
            })
        docs.append({
            "clave": f"doc:{i:04d}", "titulo": titulo, "tipo": tipo,
            "fuente": norma[2], "fecha": S._fecha_aleatoria(),
            "norma": norma[0], "fragmentos": fragmentos,
        })

    docs.extend(_documentos_del_caso(frag_seq, nombres))
    _verificar_ausencia(docs)
    return docs


def _documentos_del_caso(seq: int, nombres: dict) -> list[dict[str, Any]]:
    """Documentos que si hablan del caso, pero cada uno desde una sola filial.

    Es el punto entero: la informacion esta repartida, ninguna pieza tiene la
    suma, y por eso la similitud semantica no puede producirla.
    """
    salida = []
    piezas = [
        ("fil:banco-meridiano", "crédito de libre inversión", "780.000"),
        ("fil:banco-del-litoral", "tarjeta de crédito", "410.000"),
        ("fil:financiera-cumbre", "crédito de vehículo", "560.000"),
    ]
    for n, (filial, producto, cuota) in enumerate(piezas):
        fil = nombres[filial]["nombre"]
        core = nombres[filial].get("core", "")
        seq += 1
        salida.append({
            "clave": f"doc:caso-{n+1:02d}",
            "titulo": f"Estudio de crédito · {fil}",
            "tipo": "Estudio de crédito",
            "fuente": fil,
            "fecha": "2026-08-14",
            "norma": "nrm:pol-endeudamiento",
            "fragmentos": [{
                "clave": f"frg:{seq:05d}",
                "titulo": f"Estudio de crédito · {fil} — Decisión",
                "texto": (
                    f"Se aprueba {producto} para Carlos Andrés Mejía Vargas por una "
                    f"cuota mensual de {cuota} pesos. La capacidad de pago se calculó "
                    f"con la información disponible en el {core} de {fil}. La relación "
                    "cuota ingreso resultante se encuentra dentro del límite de "
                    "política y no se identificaron obligaciones adicionales en los "
                    "sistemas consultados por esta filial."),
                "dimension": "operacion",
                "entidades": sorted({"psn:carlos", filial, "cpt:sobreendeudamiento",
                                     "nrm:pol-endeudamiento"}),
            }],
        })
    return salida


def _verificar_ausencia(docs: list[dict[str, Any]]) -> None:
    for d in docs:
        for f in d["fragmentos"]:
            ents = set(f["entidades"])
            if PERSONA_PROHIBIDA in ents and FILIAL_PROHIBIDA in ents:
                raise AssertionError(
                    f"{f['clave']} menciona a la vez la persona y la filial del caso; "
                    "el comparativo RAG/KAG dejaria de ser honesto.")
