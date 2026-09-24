"use client";

import { useEffect, useMemo, useState } from "react";
import {
  correrConsulta, obtenerConsultas,
  type ConsultaDimensional, type ResultadoDimensional,
} from "@/lib/api";
import { color } from "@/lib/colores";
import { celda, ms, pesos, porcentaje } from "@/lib/format";
import { Cifra, Cypher, Insignia, Panel, Vacio } from "./ui";

// Claves de ejemplo para las consultas que exigen un nodo concreto.
const SUGERIDAS: Record<string, string> = {
  "exposicion-persona": "psn:carlos",
  "exposicion-indirecta": "psn:avalista",
  "grupo-economico": "emp:matriz-altamar",
  identidades: "psn:duplicada-1",
  eventos: "psn:carlos",
  evidencia: "psn:carlos",
  "norma-aplicable": "pro:00001",
};

export default function VistaDimensiones() {
  const [consultas, setConsultas] = useState<ConsultaDimensional[]>([]);
  const [activa, setActiva] = useState("exposicion-persona");
  const [clave, setClave] = useState(SUGERIDAS["exposicion-persona"] ?? "");
  const [res, setRes] = useState<ResultadoDimensional | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  useEffect(() => { obtenerConsultas().then(setConsultas).catch((e) => setError(String(e))); }, []);

  useEffect(() => {
    setCargando(true);
    setError("");
    correrConsulta(activa, clave || null)
      .then(setRes)
      .catch((e) => { setError(String(e)); setRes(null); })
      .finally(() => setCargando(false));
  }, [activa, clave]);

  const columnas = useMemo(
    () => (res?.filas.length ? Object.keys(res.filas[0]) : []),
    [res],
  );

  const porDimension = useMemo(() => {
    const m = new Map<string, ConsultaDimensional[]>();
    consultas.forEach((c) => m.set(c.dimension, [...(m.get(c.dimension) ?? []), c]));
    return [...m.entries()];
  }, [consultas]);

  const resumen = res?.resumen;

  return (
    <div className="grid h-full min-h-0 gap-3 overflow-auto
                    grid-cols-1 xl:grid-cols-[minmax(220px,270px)_minmax(0,1fr)] xl:overflow-hidden">
      <Panel titulo="Una consulta por dimensión" className="h-[340px] shrink-0 xl:h-auto xl:min-h-0 xl:shrink">
        {porDimension.map(([dim, lista]) => (
          <div key={dim} className="border-b border-[var(--borde)] px-3 py-2.5 last:border-0">
            <div className="mb-1.5 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ background: color(dim) }} />
              <span className="text-[11px] uppercase tracking-wide tenue">{dim}</span>
            </div>
            <ul className="space-y-0.5">
              {lista.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => { setActiva(c.id); setClave(SUGERIDAS[c.id] ?? ""); }}
                    className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition ${
                      c.id === activa ? "bg-[#1b2338]" : "hover:bg-[#161d30]"
                    }`}
                  >
                    {c.titulo}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Panel>

      <div className="flex min-h-0 flex-col gap-3">
        <div className="panel px-4 py-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Insignia dimension={res?.dimension}>{res?.dimension ?? "—"}</Insignia>
              <h1 className="mt-1.5 text-lg font-semibold">{res?.titulo ?? "…"}</h1>
              <p className="mt-1 text-sm tenue">{res?.porque_grafo}</p>
            </div>
            <div className="shrink-0">
              <label className="block text-[11px] uppercase tracking-wide tenue">
                Clave del nodo
              </label>
              <input
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                placeholder="opcional"
                className="mono mt-1 w-56 rounded-md border border-[var(--borde)] bg-[#0b0f19] px-2 py-1.5"
              />
            </div>
          </div>
        </div>

        {resumen && (
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            <Cifra etiqueta="Productos" valor={String(resumen.productos)}
                   detalle={`en ${resumen.filiales} filiales`} />
            <Cifra etiqueta="Cuota mensual" valor={pesos(resumen.cuota_cop)} />
            <Cifra etiqueta="Ingreso declarado" valor={pesos(resumen.ingreso_cop)} />
            <Cifra etiqueta="Antes del último"
                   valor={porcentaje(resumen.endeudamiento_previo)}
                   detalle={`tope ${resumen.tope} %`} />
            <Cifra etiqueta="Endeudamiento real"
                   valor={porcentaje(resumen.endeudamiento)}
                   detalle={resumen.excede ? "supera la política" : "dentro de política"}
                   acento={resumen.excede ? "#f87171" : "#34d399"} />
          </div>
        )}

        {res?.saldo_cop !== undefined && (
          <div className="grid grid-cols-3 gap-3">
            <Cifra etiqueta="Saldo alcanzado" valor={pesos(res.saldo_cop)} />
            {res.empresas !== undefined && (
              <Cifra etiqueta="Empresas" valor={String(res.empresas)} />
            )}
            {res.filiales !== undefined && (
              <Cifra etiqueta="Filiales" valor={String(res.filiales)} />
            )}
          </div>
        )}

        <Panel
          titulo="Resultado"
          className="h-[380px] shrink-0 xl:h-auto xl:min-h-0 xl:flex-1 xl:shrink"
          derecha={res && (
            <span className="text-xs tenue">{res.total} filas · {ms(res.ms)}</span>
          )}
        >
          {cargando && <Vacio>Ejecutando…</Vacio>}
          {error && <Vacio>{error}</Vacio>}
          {!cargando && res?.filas.length ? (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-[var(--panel)]">
                <tr className="border-b border-[var(--borde)]">
                  {columnas.map((c) => (
                    <th key={c} className="px-4 py-2 text-left text-[11px] uppercase tracking-wide tenue">
                      {c.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {res.filas.map((f, i) => (
                  <tr key={i} className="border-b border-[var(--borde)]/60">
                    {columnas.map((c) => (
                      <td key={c} className="px-4 py-1.5">{celda(c, f[c])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (!cargando && !error && <Vacio>Sin filas.</Vacio>)}
        </Panel>

        {res?.cypher && (
          <Panel titulo="Cypher ejecutado">
            <div className="p-3"><Cypher texto={res.cypher} /></div>
          </Panel>
        )}
      </div>
    </div>
  );
}
