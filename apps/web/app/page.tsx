"use client";

import { useEffect, useState } from "react";
import { obtenerMotor, type Motor } from "@/lib/api";
import VistaDimensiones from "@/components/VistaDimensiones";
import VistaEsquema from "@/components/VistaEsquema";
import VistaGrafo from "@/components/VistaGrafo";
import VistaKag from "@/components/VistaKag";

const VISTAS = [
  { id: "kag", titulo: "KAG", componente: VistaKag },
  { id: "dimensiones", titulo: "Dimensiones", componente: VistaDimensiones },
  { id: "grafo", titulo: "Grafo", componente: VistaGrafo },
  { id: "esquema", titulo: "Esquema", componente: VistaEsquema },
] as const;

export default function Pagina() {
  const [vista, setVista] = useState<(typeof VISTAS)[number]["id"]>("kag");
  const [motor, setMotor] = useState<Motor | null>(null);

  useEffect(() => { obtenerMotor().then(setMotor).catch(() => setMotor(null)); }, []);

  const Activa = VISTAS.find((v) => v.id === vista)!.componente;

  return (
    <div className="flex h-screen flex-col gap-3 p-3">
      <header className="panel flex shrink-0 items-center justify-between gap-4 px-4 py-2.5">
        <div className="flex shrink-0 items-center gap-5">
          <span className="whitespace-nowrap text-sm font-semibold tracking-tight">
            ATLAS <span className="tenue font-normal">· KAG · Neo4j</span>
          </span>
          <nav className="flex gap-1">
            {VISTAS.map((v) => (
              <button
                key={v.id}
                onClick={() => setVista(v.id)}
                className={`rounded-md px-3 py-1.5 text-sm transition ${
                  v.id === vista ? "bg-[#1b2338] font-medium" : "tenue hover:bg-[#161d30]"
                }`}
              >
                {v.titulo}
              </button>
            ))}
          </nav>
        </div>

        {motor && (
          <div className="flex min-w-0 items-center gap-3 overflow-hidden text-xs whitespace-nowrap">
            <span className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${
                motor.conectado ? "bg-emerald-400" : "bg-red-400"}`} />
              {motor.motor}
            </span>
            {(motor.componentes ?? []).map((c) => (
              <span key={c.etiqueta} className="tenue">{c.etiqueta} {c.valor}</span>
            ))}
            <span className="tenue truncate">{motor.autenticacion}</span>
          </div>
        )}
      </header>

      <main className="min-h-0 flex-1">
        <Activa />
      </main>
    </div>
  );
}
