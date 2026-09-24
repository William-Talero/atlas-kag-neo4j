"use client";

import { useEffect, useState } from "react";
import { obtenerEsquema, type Esquema } from "@/lib/api";
import { color, colorTenue } from "@/lib/colores";
import { numero } from "@/lib/format";
import { Panel, Vacio } from "./ui";

export default function VistaEsquema() {
  const [esq, setEsq] = useState<Esquema | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    obtenerEsquema().then(setEsq).catch((e) => setError(String(e)));
  }, []);

  if (error) return <Vacio>{error}</Vacio>;
  if (!esq) return <Vacio>Leyendo el catálogo de AGE…</Vacio>;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-auto lg:overflow-hidden">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
        {esq.dimensiones.map((d) => (
          <div key={d.dimension} className="panel px-4 py-3"
               style={{ borderColor: color(d.dimension) }}>
            <div className="text-[11px] uppercase tracking-wide"
                 style={{ color: color(d.dimension) }}>
              {d.titulo}
            </div>
            <div className="mt-1 text-xl font-semibold">{numero(d.nodos)}</div>
            <div className="text-xs tenue">{numero(d.aristas)} aristas</div>
            <p className="mt-2 text-xs tenue">{d.descripcion}</p>
          </div>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-2">
        <Panel
          titulo="Etiquetas"
          derecha={<span className="text-xs tenue">{numero(esq.totales.vertices)} nodos</span>}
        >
          <ul className="divide-y divide-[var(--borde)]">
            {esq.nodos.map((n) => (
              <li key={n.etiqueta} className="flex items-center justify-between px-4 py-2">
                <span className="flex items-center gap-2 text-sm">
                  <span className="rounded px-1.5 py-0.5 text-[11px]"
                        style={{ background: colorTenue(n.dimension), color: color(n.dimension) }}>
                    {n.dimension}
                  </span>
                  {n.etiqueta}
                </span>
                <span className="mono tenue">{numero(n.conteo)}</span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          titulo="Relaciones y su sistema de origen"
          derecha={<span className="text-xs tenue">{numero(esq.totales.aristas)} aristas</span>}
        >
          <ul className="divide-y divide-[var(--borde)]">
            {esq.aristas.map((a) => (
              <li key={a.relacion} className="px-4 py-2">
                <div className="flex items-center justify-between">
                  <span className="mono" style={{ color: color(a.dimension) }}>
                    {a.relacion}
                  </span>
                  <span className="mono tenue">{numero(a.conteo)}</span>
                </div>
                <div className="mt-0.5 text-[11px] tenue">{a.fuente}</div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
