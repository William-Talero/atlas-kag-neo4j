"""Las preguntas de la demostracion.

El criterio de admision es el ultimo campo: si una consulta SQL o una busqueda
semantica responden bien, la pregunta no entra. La excepcion es deliberada y
esta marcada como contraejemplo: sirve para mostrar cuando el grafo sobra.
"""

from __future__ import annotations

from typing import Any

PREGUNTAS: list[dict[str, Any]] = [
    {
        "id": "exposicion-real",
        "dimension": "operacion",
        "titulo": "Exposición real de una persona en todo el grupo",
        "pregunta": ("¿Cuál es la exposición real de Carlos Andrés Mejía Vargas "
                     "sumando todas las filiales del grupo?"),
        "ancla": "psn:carlos",
        "profundidad": 2,
        "situacion": ("Una filial le aprobó una tarjeta hace tres días. Con la "
                      "información que ella tenía, quedaba en 12% de endeudamiento."),
        "hay_que_averiguar": ("La cuota mensual agregada contra el ingreso declarado, "
                              "sumando los productos de las seis filiales."),
        "porque_grafo": ("Antes de sumar hay que resolver que seis fichas de seis cores "
                         "son la misma persona. Ningún sistema del grupo tiene esa suma: "
                         "no es una columna, es un recorrido."),
        "consulta_dimensional": "exposicion-persona",
    },
    {
        "id": "misma-persona",
        "dimension": "entidad",
        "titulo": "¿Son la misma persona?",
        "pregunta": ("¿Los registros de Marcela Quintero en tres filiales corresponden "
                     "a la misma persona?"),
        "ancla": "psn:duplicada-1",
        "profundidad": 2,
        "situacion": "Tres expedientes con documentos que difieren en un dígito.",
        "hay_que_averiguar": "Si comparten datos de contacto verificados.",
        "porque_grafo": ("No hay llave común. Lo único que une los registros es un "
                         "vecino compartido, y eso es una consulta de vecindad."),
        "consulta_dimensional": "identidades",
    },
    {
        "id": "grupo-economico",
        "dimension": "entidad",
        "titulo": "Exposición del grupo económico",
        "pregunta": ("¿Cuál es la exposición total del grupo económico encabezado por "
                     "Inversiones Altamar Holding?"),
        "ancla": "emp:matriz-altamar",
        "profundidad": 3,
        "situacion": "Una matriz, varias operativas y un representante legal común.",
        "hay_que_averiguar": "El saldo consolidado del árbol de control completo.",
        "porque_grafo": ("La profundidad del árbol de matrices es desconocida de "
                         "antemano: hay que agotarla, no se puede escribir el JOIN."),
        "consulta_dimensional": "grupo-economico",
    },
    {
        "id": "exposicion-indirecta",
        "dimension": "operacion",
        "titulo": "Exposición indirecta por aval",
        "pregunta": ("¿Cuánta deuda ajena está avalando Wilson Fabián Cadavid, que solo "
                     "tiene una cuenta de ahorros?"),
        "ancla": "psn:avalista",
        "profundidad": 2,
        "situacion": "Su ficha muestra un único producto sin riesgo aparente.",
        "hay_que_averiguar": "Las obligaciones de terceros que respalda como codeudor.",
        "porque_grafo": ("La deuda avalada no cuelga de él: cuelga de otros y apunta "
                         "hacia atrás. Es un recorrido en sentido inverso."),
        "consulta_dimensional": "exposicion-indirecta",
    },
    {
        "id": "concentracion",
        "dimension": "geografica",
        "titulo": "Concentración territorial",
        "pregunta": "¿Dónde está concentrada la cartera de libranza y en qué filial?",
        "ancla": "ciu:valledupar",
        "profundidad": 2,
        "situacion": "Una plaza intermedia con crecimiento acelerado en un solo producto.",
        "hay_que_averiguar": "El saldo por ciudad y región cruzado con la filial.",
        "porque_grafo": ("El saldo vive en la obligación y el territorio en la persona: "
                         "están a tres saltos y en sistemas distintos."),
        "consulta_dimensional": "concentracion-geografica",
    },
    {
        "id": "linea-de-tiempo",
        "dimension": "temporal",
        "titulo": "Qué pasó antes de la aprobación",
        "pregunta": ("¿Qué eventos precedieron la última aprobación de Carlos Andrés "
                     "Mejía Vargas?"),
        "ancla": "psn:carlos",
        "profundidad": 2,
        "situacion": "La aprobación no fue un hecho aislado.",
        "hay_que_averiguar": "La secuencia de eventos tipificados y su periodo.",
        "porque_grafo": ("Los eventos apuntan al sujeto desde otra dimensión y se "
                         "ordenan por una cadena de periodos, no por una fecha suelta."),
        "consulta_dimensional": "eventos",
    },
    {
        "id": "norma-aplicable",
        "dimension": "semantica",
        "titulo": "Qué norma regula este producto",
        "pregunta": "¿Qué norma interna regula un crédito de libre inversión?",
        "ancla": None,
        "profundidad": 3,
        "situacion": "El producto no cita su norma: cita su concepto.",
        "hay_que_averiguar": "La norma que regula el concepto padre, subiendo la jerarquía.",
        "porque_grafo": ("La norma no regula el producto sino un concepto a varios "
                         "niveles de distancia en la ontología."),
        "consulta_dimensional": "norma-aplicable",
    },
    {
        "id": "contraejemplo",
        "dimension": "documental",
        "titulo": "El contraejemplo: aquí el grafo sobra",
        "pregunta": ("¿Qué dice la política sobre el límite de relación cuota ingreso y "
                     "quién autoriza las excepciones?"),
        "ancla": "nrm:pol-endeudamiento",
        "profundidad": 1,
        "situacion": "La respuesta está redactada, literal, en un documento.",
        "hay_que_averiguar": "El límite y la instancia que aprueba excepciones.",
        "porque_grafo": ("No hace falta. La búsqueda vectorial la responde sola y el "
                         "recorrido no agrega nada: se incluye para marcar el límite."),
        "consulta_dimensional": None,
        "contraejemplo": True,
    },
]


def catalogo() -> list[dict[str, Any]]:
    return PREGUNTAS


def buscar(pregunta_id: str) -> dict[str, Any] | None:
    return next((p for p in PREGUNTAS if p["id"] == pregunta_id), None)
