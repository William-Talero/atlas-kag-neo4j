# ATLAS · KAG multidimensional · Neo4j

La misma solución que `../atlas-kag-postgres`, con el mismo modelo, los mismos
datos y la misma batería de verificación, pero sobre **Neo4j** con su **índice
vectorial nativo** en lugar de Apache AGE y pgvector.

Existe para poder comparar las dos con algo más que una tabla de características:
mismo grafo, mismas preguntas, misma prueba.

```
apps/web     Next.js 15 · React 19 · Tailwind v4 · Cytoscape + fcose
apps/api     FastAPI · driver oficial de Neo4j · Cypher nativo · índice vectorial
infra/       provision.sh (Azure Container Instances) y schema.cypher
scripts/     generación del grafo, carga y verificación
```

La interfaz es la misma: un agente al que se le escribe en lenguaje natural, el
subgrafo recorrido en el lienzo, la evidencia fusionada y la línea base de solo
vector al lado. El detalle de cómo ancla y cómo fusiona está en el README de la
versión PostgreSQL: es exactamente el mismo código.

## Arranque

```bash
az login
make provision   # grupo de recursos + Neo4j en Azure Container Instances
make install     # venv de la API + npm de la web
make reload      # carga el grafo y el corpus (~45 s)
make verify      # corre la secuencia completa y falla si algo no se alcanza
make dev         # API en :8001 y web en :3001
```

Los puertos son **8001 y 3001** a propósito: así esta versión y la de PostgreSQL
pueden estar levantadas a la vez y se comparan lado a lado.

`make provision` genera la contraseña, la escribe en `.env` con permisos 600 y la
envía al contenedor como variable segura, de modo que no aparece en
`az container show`. Sin Azure, `make local` levanta el mismo Neo4j en docker.

Los datos (`data/*.json`) son los que genera `make seed`, con la misma semilla
que la versión PostgreSQL: los dos grafos son idénticos nodo a nodo.

## La diferencia real, en una consulta

La restricción del subgrafo sobre la búsqueda vectorial es donde se ve el cambio
de motor:

```cypher
-- Neo4j: la pertenencia al subgrafo es el propio patrón
MATCH (f:Fragmento)-[:MENCIONA]->(n) WHERE n.clave IN $claves
WITH DISTINCT f
WITH f, vector.similarity.cosine(f.embedding, $consulta) AS score
RETURN f, score ORDER BY score DESC LIMIT $k
```

```sql
-- pgvector: hay que materializar la pertenencia en una columna de arreglo
WITH candidatos AS MATERIALIZED (
  SELECT … FROM kag_fragmento WHERE entidades && $claves_del_subgrafo::text[]
)
SELECT …, embedding <=> $consulta AS distancia FROM candidatos ORDER BY distancia LIMIT $k
```

En Neo4j la relación `MENCIONA` **es** el grafo, así que no puede quedar
desfasada. En PostgreSQL la columna `entidades` es una desnormalización que hay
que mantener sincronizada con las aristas: el cargador la escribe, pero cualquier
escritura posterior al grafo tendría que actualizarla también.

En lo demás las dos implementaciones son sorprendentemente parecidas: el
recuperador KAG, los routers y toda la interfaz son **el mismo código**, porque
el contrato entre la capa de grafo y el resto no cambia.

## Medido, no supuesto

Contra el mismo grafo (9.368 nodos, 44.218 aristas, 1.063 fragmentos), desde la
misma máquina, contra la misma región de Azure:

| | PostgreSQL 16 + AGE 1.6 | Neo4j 5.26 community |
|---|---|---|
| Carga completa del grafo | 178 s | 43 s |
| `verify` de extremo a extremo | 10,1 s | 4,9 s |
| Esquema con conteos (en caliente) | 397 ms | 497 ms |
| `exposicion-persona` | 296 ms | 227 ms |
| Recorrido de 2 saltos, 123 nodos | ~550 ms | ~330 ms |

Los resultados son **idénticos**, no parecidos: 9 productos en 6 filiales,
39,8 % → 48,6 %, y la misma evidencia con las mismas similitudes hasta el cuarto
decimal.

```
Estudio de crédito · Banco Meridiano    score=0.748  sim=0.541  0 saltos
Estudio de crédito · Banco del Litoral  score=0.743  sim=0.533  0 saltos
Estudio de crédito · Financiera Cumbre  score=0.741  sim=0.529  0 saltos
```

Para que esas cifras fueran comparables hubo que igualar una escala: Neo4j
devuelve el coseno normalizado a [0,1] con `(1 + cos) / 2` y pgvector devuelve el
coseno crudo. `kag/vector.py` deshace la normalización.

La carga es cuatro veces más rápida en Neo4j porque AGE resuelve cada arista con
un `MATCH` etiquetado por lote y porque el aprovisionamiento exige abrir una
conexión nueva por fase. El resto de las diferencias son de décimas y, a este
tamaño, no deberían decidir nada.

## Cuándo elegir cuál

**Neo4j** si el grafo es el producto: recorridos profundos, consultas de camino,
algoritmos de grafo, y un equipo que ya escribe Cypher. El modelo de datos es más
directo y no hay que pelear con `agtype`.

**PostgreSQL con AGE** si el grafo es *una* de las cosas que hace el sistema. La
ventaja no es el grafo: es que el recorrido, la similitud vectorial y la
agregación relacional caben en la misma transacción, con un solo motor que
operar, respaldar y auditar, y con Entra ID en lugar de una contraseña.

El coste de AGE es real y conviene decirlo: menos planificador, `agtype` en cada
lectura, y tres trampas de sesión documentadas en el README de la otra versión.

## Nota de operación

El contenedor no tiene volumen persistente. Esta suscripción tiene una política
que impide la autenticación por clave compartida en Storage, y Azure Container
Instances solo monta Azure Files con clave. Si el contenedor se recrea, el grafo
se reconstruye con `make reload` en unos 45 segundos.

El puerto bolt está abierto a internet porque es un entorno de demostración. Para
algo real: Neo4j AuraDB, o el contenedor detrás de una red virtual.
