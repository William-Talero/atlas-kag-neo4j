import type { Dimension } from "./api";

/** Un color fijo por dimension en toda la aplicacion: es lo que permite leer de
 *  un vistazo por que eje se esta moviendo una consulta. */
export const COLOR: Record<Dimension, string> = {
  entidad: "#7dd3fc",
  operacion: "#fbbf24",
  geografica: "#34d399",
  temporal: "#c084fc",
  semantica: "#f472b6",
  documental: "#94a3b8",
};

export const COLOR_TENUE: Record<Dimension, string> = {
  entidad: "rgba(125,211,252,0.14)",
  operacion: "rgba(251,191,36,0.14)",
  geografica: "rgba(52,211,153,0.14)",
  temporal: "rgba(192,132,252,0.14)",
  semantica: "rgba(244,114,182,0.14)",
  documental: "rgba(148,163,184,0.14)",
};

export const color = (d?: string) => COLOR[(d ?? "entidad") as Dimension] ?? COLOR.entidad;
export const colorTenue = (d?: string) =>
  COLOR_TENUE[(d ?? "entidad") as Dimension] ?? COLOR_TENUE.entidad;
