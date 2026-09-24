const COP = new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "COP", maximumFractionDigits: 0,
});
const NUM = new Intl.NumberFormat("es-CO");

export const pesos = (v: unknown) =>
  typeof v === "number" ? COP.format(v) : String(v ?? "");

export const numero = (v: unknown) =>
  typeof v === "number" ? NUM.format(v) : String(v ?? "");

export const porcentaje = (v: unknown, dec = 1) =>
  typeof v === "number" ? `${v.toFixed(dec)} %` : String(v ?? "");

export const ms = (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(2)} s` : `${Math.round(v)} ms`);

export const celda = (clave: string, valor: unknown) => {
  if (valor === null || valor === undefined) return "—";
  if (/saldo|cuota|avaluo|ingreso/i.test(clave) && typeof valor === "number") return pesos(valor);
  if (typeof valor === "number") return numero(valor);
  if (typeof valor === "boolean") return valor ? "sí" : "no";
  return String(valor);
};
