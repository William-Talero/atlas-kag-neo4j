"use client";

import type { Dimension } from "@/lib/api";
import { color, colorTenue } from "@/lib/colores";

export function Insignia({ dimension, children }: {
  dimension?: Dimension | string; children: React.ReactNode;
}) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[11px] font-medium"
      style={{ background: colorTenue(dimension), color: color(dimension) }}
    >
      {children}
    </span>
  );
}

export function Panel({ titulo, derecha, children, className = "", scroll = true }: {
  titulo?: string; derecha?: React.ReactNode;
  children: React.ReactNode; className?: string; scroll?: boolean;
}) {
  return (
    <section className={`panel flex flex-col overflow-hidden ${className}`}>
      {titulo && (
        <header className="flex items-center justify-between gap-3 border-b border-[var(--borde)] px-4 py-2.5">
          <h2 className="shrink-0 text-sm font-semibold">{titulo}</h2>
          {derecha}
        </header>
      )}
      <div className={`relative min-h-0 flex-1 ${scroll ? "overflow-auto" : "overflow-hidden"}`}>
        {children}
      </div>
    </section>
  );
}

export function Cifra({ etiqueta, valor, detalle, acento }: {
  etiqueta: string; valor: string; detalle?: string; acento?: string;
}) {
  return (
    <div className="panel px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide tenue">{etiqueta}</div>
      <div className="mt-1 text-2xl font-semibold" style={acento ? { color: acento } : undefined}>
        {valor}
      </div>
      {detalle && <div className="mt-0.5 text-xs tenue">{detalle}</div>}
    </div>
  );
}

export function Cypher({ texto }: { texto: string }) {
  if (!texto) return null;
  return (
    <pre className="mono cypher overflow-x-auto rounded-lg bg-[#0b0f19] p-3">{texto}</pre>
  );
}

export function Vacio({ children }: { children: React.ReactNode }) {
  return <p className="p-6 text-sm tenue">{children}</p>;
}
