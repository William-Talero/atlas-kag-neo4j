/** Cliente REST. El front no sabe de AGE ni de pgvector: solo JSON. */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Dimension =
  | "entidad" | "operacion" | "geografica" | "temporal" | "semantica" | "documental";

export interface Motor {
  motor: string;
  host: string;
  base: string;
  grafo: string;
  autenticacion: string;
  modelo: { dimensiones: number; etiquetas: number; relaciones: number };
  componentes: { etiqueta: string; valor: string }[];
  conectado: boolean;
  error: string;
}

export interface ResumenDimension {
  dimension: Dimension;
  titulo: string;
  pregunta: string;
  descripcion: string;
  nodos: number;
  aristas: number;
  etiquetas: string[];
}

export interface Esquema {
  nodos: { etiqueta: string; dimension: Dimension; conteo: number }[];
  aristas: { relacion: string; dimension: Dimension; fuente: string; conteo: number }[];
  dimensiones: ResumenDimension[];
  totales: {
    vertices: number; aristas: number; etiquetas: number;
    relaciones: number; dimensiones: number;
  };
  ms: number;
}

export interface NodoGrafo {
  clave: string;
  label: string;
  nombre: string;
  dimension: Dimension;
  props: Record<string, unknown>;
}

export interface AristaGrafo {
  desde: string;
  hasta: string;
  relacion: string;
  dimension: Dimension;
  fuente: string;
}

export interface Salto {
  origen: string; origen_label: string; origen_nombre: string;
  relacion: string; dimension: Dimension;
  destino: string; destino_label: string; destino_nombre: string;
  fuente: string;
}

export interface Subgrafo {
  raiz?: string;
  nodos: NodoGrafo[];
  aristas: AristaGrafo[];
  saltos?: Salto[];
  cypher: string;
  ms: number;
  por_dimension?: { dimension: Dimension; titulo: string; nodos: number; aristas: number }[];
  enfocado?: boolean;
  omitidos?: number;
  recorridos?: number;
  concentradores?: { clave: string; nombre: string; label: string }[];
}

export interface Fragmento {
  clave: string;
  documento: string;
  titulo: string;
  extracto: string;
  dimension: Dimension;
  entidades: string[];
  similitud: number;
  score?: number;
  saltos_al_ancla?: number | null;
  entidades_del_subgrafo?: string[];
}

export interface Respuesta {
  pregunta: string;
  anclaje: { claves: string[]; candidatos: NodoGrafo[]; estrategia: string };
  subgrafo: Subgrafo;
  evidencia: Fragmento[];
  kag: { ms: number; sql: string; anclas: number; candidatos: number };
  rag: { resultados: Fragmento[]; ms: number; sql: string };
  cobertura: { corpus: number; alcanzados: number; reduccion: number };
  suficiente: boolean;
  aporte_del_grafo: {
    fragmentos_solo_kag: string[];
    reduccion_del_corpus: number;
    saltos_citados: number;
    fuentes: string[];
  };
  veredicto: string;
  ms: number;
}

export interface Pregunta {
  id: string;
  dimension: Dimension;
  titulo: string;
  pregunta: string;
  ancla: string | null;
  profundidad: number;
  situacion: string;
  hay_que_averiguar: string;
  porque_grafo: string;
  consulta_dimensional: string | null;
  contraejemplo?: boolean;
}

export interface ConsultaDimensional {
  id: string;
  dimension: Dimension;
  requiere: string | null;
  titulo: string;
  porque_grafo: string;
}

export interface ResultadoDimensional {
  consulta: string;
  dimension: Dimension;
  titulo: string;
  porque_grafo: string;
  cypher: string;
  filas: Record<string, unknown>[];
  total: number;
  ms: number;
  resumen?: Record<string, number | string | boolean>;
  saldo_cop?: number;
  empresas?: number;
  filiales?: number;
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${ruta}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) {
    const cuerpo = await r.text();
    throw new Error(`${ruta} respondió ${r.status}: ${cuerpo.slice(0, 180)}`);
  }
  return (await r.json()) as T;
}

export const obtenerMotor = () => pedir<Motor>("/motor");
export const obtenerEsquema = () => pedir<Esquema>("/grafo/esquema");
export const obtenerSubgrafo = (limite = 700) =>
  pedir<Subgrafo>(`/grafo/subgrafo?limite=${limite}`);
export const obtenerMuestra = (porRelacion = 10) =>
  pedir<Subgrafo & { relaciones_representadas: number }>(
    `/grafo/muestra?por_relacion=${porRelacion}`);
export const expandir = (clave: string, profundidad = 1) =>
  pedir<Subgrafo>(`/grafo/expandir?clave=${encodeURIComponent(clave)}&profundidad=${profundidad}`);
export const buscarNodos = (q: string) =>
  pedir<{ filas: NodoGrafo[]; total: number; ms: number; cypher: string }>(
    `/grafo/buscar?q=${encodeURIComponent(q)}`);
export const obtenerNodo = (clave: string) =>
  pedir<NodoGrafo>(`/grafo/nodo/${encodeURIComponent(clave)}`);

export const obtenerPreguntas = () => pedir<Pregunta[]>("/kag/preguntas");
export const responderPregunta = (id: string, enfocado = true) =>
  pedir<Respuesta & { ficha: Pregunta }>(
    `/kag/pregunta/${encodeURIComponent(id)}?enfocado=${enfocado}`);
export const responder = (cuerpo: {
  pregunta: string; ancla?: string | null; profundidad?: number; k?: number;
  enfocado?: boolean;
}) => pedir<Respuesta>("/kag/responder", { method: "POST", body: JSON.stringify(cuerpo) });
export const buscarVectorial = (q: string, k = 8) =>
  pedir<{ resultados: Fragmento[]; ms: number; sql: string }>(
    `/kag/vectorial?q=${encodeURIComponent(q)}&k=${k}`);

export const obtenerConsultas = () => pedir<ConsultaDimensional[]>("/dimensiones");
export const correrConsulta = (id: string, clave?: string | null) =>
  pedir<ResultadoDimensional>(
    `/dimensiones/${encodeURIComponent(id)}${clave ? `?clave=${encodeURIComponent(clave)}` : ""}`);
