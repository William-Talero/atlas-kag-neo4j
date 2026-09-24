"use client";

import { useCallback, useEffect, useState } from "react";
import {
  buscarNodos, expandir, obtenerSubgrafo,
  type NodoGrafo, type Subgrafo,
} from "@/lib/api";
import { color } from "@/lib/colores";
import { celda, ms } from "@/lib/format";
import { Cypher, Insignia, Panel, Vacio } from "./ui";
import Lienzo from "./Lienzo";

export default function VistaGrafo() {
  const [sub, setSub] = useState<Subgrafo | null>(null);
  const [termino, setTermino] = useState("");
  const [resultados, setResultados] = useState<NodoGrafo[]>([]);
  const [seleccion, setSeleccion] = useState<string>("");
  const [profundidad, setProfundidad] = useState(2);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    obtenerSubgrafo(600).then(setSub).finally(() => setCargando(false));
  }, []);

  const abrir = useCallback((clave: string, p = profundidad) => {
    setCargando(true);
    setSeleccion(clave);
    expandir(clave, p).then(setSub).finally(() => setCargando(false));
  }, [profundidad]);

  const buscar = (e: React.FormEvent) => {
    e.preventDefault();
    if (!termino.trim()) return;
    buscarNodos(termino).then((r) => setResultados(r.filas));
  };

  const nodoSeleccionado = sub?.nodos.find((n) => n.clave === seleccion);

  return (
    <div className="grid h-full min-h-0 gap-3 overflow-auto
                    grid-cols-1
                    xl:grid-cols-[minmax(230px,260px)_minmax(0,1fr)_minmax(280px,320px)]
                    xl:overflow-hidden">
      <Panel titulo="Buscar en el grafo" className="h-[320px] shrink-0 xl:h-auto xl:min-h-0 xl:shrink">
        <form onSubmit={buscar} className="border-b border-[var(--borde)] p-3">
          <input
            value={termino}
            onChange={(e) => setTermino(e.target.value)}
            placeholder="nombre, documento, NIT, tipo…"
            className="w-full rounded-md border border-[var(--borde)] bg-[#0b0f19] px-3 py-2 text-sm"
          />
          <div className="mt-2 flex items-center gap-2">
            <label className="text-xs tenue">Profundidad</label>
            <select
              value={profundidad}
              onChange={(e) => setProfundidad(Number(e.target.value))}
              className="rounded-md border border-[var(--borde)] bg-[#0b0f19] px-2 py-1 text-xs"
            >
              {[1, 2, 3].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </form>
        <ul className="divide-y divide-[var(--borde)]">
          {resultados.map((n) => (
            <li key={n.clave}>
              <button
                onClick={() => abrir(n.clave)}
                className="w-full px-4 py-2.5 text-left hover:bg-[#161d30]"
              >
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: color(n.dimension) }} />
                  <span className="text-sm">{n.nombre}</span>
                </div>
                <div className="mono mt-0.5 tenue">{n.label} · {n.clave}</div>
              </button>
            </li>
          ))}
          {!resultados.length && (
            <li className="p-4 text-xs tenue">
              Prueba con <span className="mono">Carlos</span>,
              {" "}<span className="mono">Altamar</span> o
              {" "}<span className="mono">libranza</span>.
            </li>
          )}
        </ul>
      </Panel>

      <Panel
        titulo={sub?.raiz ? `Vecindario de ${sub.raiz}` : "Muestra del grafo"}
        className="h-[420px] shrink-0 xl:h-auto xl:min-h-0 xl:shrink"
        scroll={false}
        derecha={sub && (
          <span className="text-xs tenue">
            {sub.nodos.length} nodos · {sub.aristas.length} aristas · {ms(sub.ms)}
          </span>
        )}
      >
        {cargando && <Vacio>Consultando…</Vacio>}
        {!cargando && sub && (
          <Lienzo
            nodos={sub.nodos} aristas={sub.aristas}
            raiz={sub.raiz} seleccion={seleccion}
            onSeleccion={(c) => setSeleccion(c)}
          />
        )}
      </Panel>

      <div className="flex min-h-0 flex-col gap-3">
        <Panel titulo="Nodo seleccionado" className="h-[300px] shrink-0 xl:h-auto xl:min-h-0 xl:flex-1 xl:shrink">
          {nodoSeleccionado ? (
            <div className="p-4">
              <Insignia dimension={nodoSeleccionado.dimension}>
                {nodoSeleccionado.label}
              </Insignia>
              <h3 className="mt-2 text-base font-semibold">{nodoSeleccionado.nombre}</h3>
              <p className="mono mt-0.5 tenue">{nodoSeleccionado.clave}</p>
              <dl className="mt-3 space-y-1 text-sm">
                {Object.entries(nodoSeleccionado.props).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3">
                    <dt className="tenue">{k}</dt>
                    <dd className="text-right">{celda(k, v)}</dd>
                  </div>
                ))}
              </dl>
              <button
                onClick={() => abrir(nodoSeleccionado.clave)}
                className="mt-4 w-full rounded-md border border-[var(--borde)] px-3 py-2 text-sm hover:bg-[#1b2338]"
              >
                Expandir desde aquí
              </button>
            </div>
          ) : (
            <Vacio>Selecciona un nodo del lienzo.</Vacio>
          )}
        </Panel>

        <Panel titulo="Saltos y procedencia" className="h-[280px] shrink-0 xl:h-auto xl:min-h-0 xl:flex-1 xl:shrink">
          {sub?.saltos?.length ? (
            <ul className="divide-y divide-[var(--borde)]">
              {sub.saltos.slice(0, 40).map((s, i) => (
                <li key={i} className="px-4 py-2">
                  <div className="text-xs">
                    <span>{s.origen_nombre}</span>
                    <span className="mx-1.5" style={{ color: color(s.dimension) }}>
                      —{s.relacion}→
                    </span>
                    <span>{s.destino_nombre}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] tenue">{s.fuente}</div>
                </li>
              ))}
            </ul>
          ) : (
            <Vacio>Expande un nodo para ver la procedencia de cada salto.</Vacio>
          )}
        </Panel>

        {sub?.cypher && (
          <Panel titulo="Cypher">
            <div className="p-3"><Cypher texto={sub.cypher} /></div>
          </Panel>
        )}
      </div>
    </div>
  );
}
