// Esquema de ATLAS KAG sobre Neo4j.
//
// Restricciones de unicidad por etiqueta: ademas de garantizar la integridad,
// crean el indice que hace que `MATCH (n:Persona {clave: ...})` sea una busqueda
// y no un recorrido.
//
// __ETIQUETAS__ y la dimension del vector los sustituye el cargador.

CREATE CONSTRAINT clave_unica IF NOT EXISTS
FOR (n:__ETIQUETA__) REQUIRE n.clave IS UNIQUE;

// Indice vectorial nativo sobre los fragmentos del corpus.
CREATE VECTOR INDEX fragmento_embedding IF NOT EXISTS
FOR (f:Fragmento) ON (f.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: __DIM__,
  `vector.similarity_function`: 'cosine'
}};

// Texto de los fragmentos, para la busqueda lexica de anclaje.
CREATE FULLTEXT INDEX fragmento_texto IF NOT EXISTS
FOR (f:Fragmento) ON EACH [f.titulo, f.texto];
