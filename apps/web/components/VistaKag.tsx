"use client";

import { useEffect, useState } from "react";
import {
  obtenerEsquema, obtenerMuestra, responder, responderPregunta,
  type Respuesta, type Subgrafo,
} from "@/lib/api";
import { ms, numero } from "@/lib/format";
import Chat, { type Consulta } from "./Chat";
import Lienzo from "./Lienzo";
import { Cifra, Cypher, Insignia, Panel, Vacio } from "./ui";

export default function VistaKag() {
  const [res, setRes] = useState<Respuesta | null>(null);
  const [consulta, setConsulta] = useState<Consulta | null>(null);
  const [recargando, setRecargando] = useState(false);
  const [muestra, setMuestra] = useState<
    (Subgrafo & { relaciones_representadas: number }) | null>(null);
  const [totales, setTotales] = useState<{ vertices: number; aristas: number } | null>(null);

  // Sin pregunta se ve el grafo entero; al preguntar, el recorrido que la explica.
  useEffect(() => {
    obtenerMuestra().then(setMuestra).catch(() => setMuestra(null));
    obtenerEsquema().then((e) => setTotales(e.totales)).catch(() => setTotales(null));
  }, []);

  const enfocado = res?.subgrafo.enfocado ?? true;
  const omitidos = res?.subgrafo.omitidos ?? 0;
  const lienzo = res?.subgrafo.nodos.length ? res.subgrafo : muestra;

  async function cambiarEnfoque() {
    if (!consulta || recargando) return;
    setRecargando(true);
    try {
      const r = consulta.fichaId
        ? await responderPregunta(consulta.fichaId, !enfocado)
        : await responder({ pregunta: consulta.pregunta, profundidad: 2, k: 6,
                            enfocado: !enfocado });
      setRes(r);
    } finally {
      setRecargando(false);
    }
  }

  return (
    // Alturas explicitas en vez de flex-1: en una ventana estrecha el lienzo se
    // quedaba en cero pixeles y el grafo simplemente no aparecia.
    <div className="grid h-full min-h-0 gap-3 overflow-auto
                    grid-cols-1
                    xl:grid-cols-[minmax(300px,360px)_minmax(0,1fr)]
                    xl:overflow-hidden">
      <Panel titulo="Agente" className="h-[440px] shrink-0 xl:h-auto xl:min-h-0 xl:shrink" scroll={false}>
        <Chat onRespuesta={(r, c) => { setRes(r); setConsulta(c ?? null); }} activo={res} />
      </Panel>

      {/* En pantalla ancha esta columna se desplaza: si no, los paneles de
          abajo con altura fija dejaban al lienzo sin espacio. */}
      <div className="flex min-h-0 flex-col gap-3 xl:overflow-auto xl:pr-1">
        {res && (
          <div className="grid shrink-0 grid-cols-2 gap-3 xl:grid-cols-4">
            <Cifra etiqueta="Nodos recorridos"
                   valor={String(res.subgrafo.nodos.length)}
                   detalle={`${res.aporte_del_grafo.saltos_citados} relaciones`} />
            <Cifra etiqueta="Corpus acotado"
                   valor={`${res.cobertura.reduccion} %`}
                   detalle={`${res.cobertura.alcanzados} de ${res.cobertura.corpus}`} />
            <Cifra etiqueta="Evidencia a 0 saltos"
                   valor={String(res.evidencia.filter((e) => e.saltos_al_ancla === 0).length)}
                   detalle="menciona el ancla" />
            <Cifra etiqueta="Solo con grafo"
                   valor={String(res.aporte_del_grafo.fragmentos_solo_kag.length)}
                   detalle="la similitud no los trajo"
                   acento={res.aporte_del_grafo.fragmentos_solo_kag.length ? "#fbbf24" : undefined} />
          </div>
        )}

        <Panel
          titulo={res ? "Subgrafo recuperado" : "El grafo completo"}
          className="h-[420px] shrink-0 xl:h-auto xl:min-h-[380px] xl:flex-1 xl:shrink"
          scroll={false}
          derecha={
            <div className="flex flex-wrap items-center justify-end gap-1.5">
              {res?.subgrafo.por_dimension?.map((d) => (
                <Insignia key={d.dimension} dimension={d.dimension}>
                  {d.titulo} {d.nodos}
                </Insignia>
              ))}
              {res && consulta && (
                <button
                  onClick={cambiarEnfoque}
                  disabled={recargando}
                  title={enfocado
                    ? "Mostrar también el vecindario de los concentradores"
                    : "Dejar solo lo que explica la respuesta"}
                  className="rounded-md border border-[var(--borde)] px-2 py-0.5 text-[11px]
                             transition hover:bg-[#1b2338] disabled:opacity-40"
                >
                  {recargando ? "…" : enfocado ? `ver todo (+${omitidos})` : "enfocar"}
                </button>
              )}
            </div>
          }
        >
          {lienzo?.nodos.length ? (
            <>
              <Lienzo
                nodos={lienzo.nodos}
                aristas={lienzo.aristas}
                raiz={res?.subgrafo.raiz}
              />
              <p className="pointer-events-none absolute bottom-2 left-3 text-[11px] tenue">
                {res
                  ? (enfocado && omitidos > 0
                      ? `${res.subgrafo.nodos.length} de ${res.subgrafo.recorridos} nodos`
                        + (res.subgrafo.concentradores?.length
                            ? ` · no se atraviesa ${res.subgrafo.concentradores
                                .map((c) => c.nombre).join(", ")}`
                            : "")
                      : `${res.subgrafo.nodos.length} nodos del recorrido`)
                  : `muestra de ${muestra?.relaciones_representadas ?? 0} relaciones`
                    + (totales
                        ? ` · el grafo tiene ${numero(totales.vertices)} nodos `
                          + `y ${numero(totales.aristas)} aristas`
                        : "")}
              </p>
            </>
          ) : (
            <Vacio>
              {res
                ? "Esta pregunta no ancló en ninguna entidad del grafo."
                : "Cargando el grafo…"}
            </Vacio>
          )}
        </Panel>

        <div className="grid shrink-0 grid-cols-1 gap-3 lg:grid-cols-2">
          <Panel titulo="Evidencia · KAG" className="h-[260px] shrink-0">
            {res?.evidencia.length ? (
              <ul className="divide-y divide-[var(--borde)]">
                {res.evidencia.map((f) => (
                  <li key={f.clave} className="px-4 py-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold">{f.titulo}</span>
                      <span className="mono shrink-0 tenue">{f.score?.toFixed(3)}</span>
                    </div>
                    <p className="mt-1 text-[11px] tenue">{f.extracto}</p>
                    <p className="mt-1 text-[11px] tenue">
                      sim {f.similitud.toFixed(3)} ·{" "}
                      {f.saltos_al_ancla === 0
                        ? "menciona el ancla"
                        : `${f.saltos_al_ancla} saltos`}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <Vacio>{res ? res.veredicto : "…"}</Vacio>
            )}
          </Panel>

          <Panel
            titulo="Línea base · solo vector"
            className="h-[260px] shrink-0"
            derecha={res && <span className="text-xs tenue">{ms(res.rag.ms)}</span>}
          >
            {res?.rag.resultados.length ? (
              <ul className="divide-y divide-[var(--borde)]">
                {res.rag.resultados.slice(0, 8).map((f) => (
                  <li key={f.clave} className="flex items-start justify-between gap-2 px-4 py-2">
                    <span className="text-xs">{f.titulo}</span>
                    <span className="mono shrink-0 tenue">{f.similitud.toFixed(3)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <Vacio>…</Vacio>
            )}
          </Panel>
        </div>

        {res?.subgrafo.cypher && (
          <Panel titulo="Lo que se ejecutó" className="max-h-[200px] shrink-0">
            <div className="space-y-2 p-3">
              <Cypher texto={res.subgrafo.cypher} />
              <Cypher texto={res.kag.sql} />
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}
