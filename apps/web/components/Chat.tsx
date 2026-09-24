"use client";

import { useEffect, useRef, useState } from "react";
import {
  obtenerPreguntas, responder, responderPregunta,
  type Pregunta, type Respuesta,
} from "@/lib/api";
import { color } from "@/lib/colores";
import { ms } from "@/lib/format";

export interface Consulta {
  pregunta: string;
  fichaId?: string;
}

export interface Turno {
  id: number;
  pregunta: string;
  ficha?: Pregunta;
  respuesta?: Respuesta;
  error?: string;
}

interface Props {
  onRespuesta: (r: Respuesta | null, consulta?: Consulta) => void;
  activo?: Respuesta | null;
}

/** El agente no inventa: cada frase sale de una cifra del recorrido. */
function redactar(r: Respuesta): string[] {
  if (!r.anclaje.claves.length) {
    return [r.veredicto];
  }
  const cero = r.evidencia.filter((e) => e.saltos_al_ancla === 0).length;
  const dims = r.subgrafo.por_dimension ?? [];
  const lineas = [
    `Ancló en ${r.anclaje.claves.join(", ")} por ${r.anclaje.estrategia}.`,
    `El recorrido tocó ${r.subgrafo.nodos.length} nodos y ${r.aporte_del_grafo.saltos_citados}` +
      ` relaciones sobre ${dims.length} dimensiones, citando ${r.aporte_del_grafo.fuentes.length}` +
      ` sistemas de origen distintos.`,
    `Eso redujo el corpus un ${r.cobertura.reduccion}%: de ${r.cobertura.corpus}` +
      ` fragmentos quedaron ${r.cobertura.alcanzados} conectados al subgrafo.`,
  ];
  if (cero) {
    lineas.push(`${cero} de los fragmentos recuperados mencionan el ancla directamente.`);
  }
  if (r.aporte_del_grafo.fragmentos_solo_kag.length) {
    lineas.push(
      `${r.aporte_del_grafo.fragmentos_solo_kag.length} fragmentos no aparecían` +
      ` en la búsqueda por similitud pura: los trajo el grafo.`);
  } else if (cero) {
    lineas.push("La similitud pura también los encontraba: aquí el grafo ordena, no rescata.");
  }
  return lineas;
}

export default function Chat({ onRespuesta, activo }: Props) {
  const [sugerencias, setSugerencias] = useState<Pregunta[]>([]);
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [texto, setTexto] = useState("");
  const [cargando, setCargando] = useState(false);
  const fin = useRef<HTMLDivElement>(null);
  const contador = useRef(0);

  useEffect(() => { obtenerPreguntas().then(setSugerencias).catch(() => {}); }, []);
  useEffect(() => { fin.current?.scrollIntoView({ behavior: "smooth" }); }, [turnos, cargando]);

  async function lanzar(pregunta: string, fichaId?: string) {
    if (cargando) return;
    const id = ++contador.current;
    setTurnos((t) => [...t, { id, pregunta }]);
    setCargando(true);
    setTexto("");
    try {
      const r = fichaId
        ? await responderPregunta(fichaId)
        : await responder({ pregunta, profundidad: 2, k: 6 });
      setTurnos((t) => t.map((x) => (x.id === id
        ? { ...x, respuesta: r, ficha: (r as Respuesta & { ficha?: Pregunta }).ficha }
        : x)));
      onRespuesta(r, { pregunta, fichaId });
    } catch (e) {
      setTurnos((t) => t.map((x) => (x.id === id ? { ...x, error: String(e) } : x)));
      onRespuesta(null);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-auto px-3 py-3">
        {!turnos.length && (
          <div className="space-y-2">
            <p className="px-1 text-xs tenue">
              Pregunta lo que quieras, o empieza por una de estas. Cada respuesta
              se arma recorriendo el grafo y se sustenta en evidencia citable.
            </p>
            {sugerencias.map((p) => (
              <button
                key={p.id}
                onClick={() => lanzar(p.pregunta, p.id)}
                className="w-full rounded-lg border border-[var(--borde)] px-3 py-2 text-left transition hover:bg-[#1b2338]"
              >
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: color(p.dimension) }} />
                  <span className="text-[13px] font-medium">{p.titulo}</span>
                </span>
                <span className="mt-0.5 block text-[11px] tenue">{p.situacion}</span>
              </button>
            ))}
          </div>
        )}

        <ul className="space-y-3">
          {turnos.map((t) => (
            <li key={t.id} className="space-y-2">
              <div className="ml-6 rounded-lg rounded-br-sm bg-[#1e2a44] px-3 py-2 text-[13px]">
                {t.pregunta}
              </div>

              {t.error && (
                <div className="mr-6 rounded-lg border border-red-900/60 bg-red-950/30 px-3 py-2 text-[12px] text-red-300">
                  {t.error}
                </div>
              )}

              {t.respuesta && (
                <div
                  className={`mr-6 cursor-pointer rounded-lg rounded-bl-sm border px-3 py-2 transition ${
                    activo === t.respuesta
                      ? "border-[#3b4a6b] bg-[#161d30]"
                      : "border-[var(--borde)] hover:bg-[#141b2d]"
                  }`}
                  onClick={() => onRespuesta(t.respuesta!, {
                    pregunta: t.pregunta, fichaId: t.ficha?.id })}
                >
                  {t.ficha && (
                    <p className="mb-1.5 text-[11px] tenue">
                      <span className="font-medium" style={{ color: color(t.ficha.dimension) }}>
                        Por qué un grafo:
                      </span>{" "}
                      {t.ficha.porque_grafo}
                    </p>
                  )}
                  <ul className="space-y-1 text-[12px]">
                    {redactar(t.respuesta).map((l, i) => (
                      <li key={i} className="flex gap-1.5">
                        <span className="tenue">·</span>
                        <span>{l}</span>
                      </li>
                    ))}
                  </ul>
                  {t.respuesta.evidencia.length > 0 && (
                    <div className="mt-2 border-t border-[var(--borde)] pt-2">
                      <p className="mb-1 text-[11px] tenue">Evidencia principal</p>
                      {t.respuesta.evidencia.slice(0, 2).map((e) => (
                        <p key={e.clave} className="text-[11px]">
                          <span className="tenue">{e.score?.toFixed(3)}</span>{" "}
                          {e.titulo}
                        </p>
                      ))}
                    </div>
                  )}
                  <p className="mt-2 text-[11px] tenue">
                    {ms(t.respuesta.ms)} · {t.respuesta.subgrafo.nodos.length} nodos
                    {activo === t.respuesta ? " · en el lienzo" : " · pulsa para verlo"}
                  </p>
                </div>
              )}
            </li>
          ))}
        </ul>

        {cargando && (
          <p className="mr-6 mt-3 animate-pulse text-[12px] tenue">
            Recorriendo el grafo…
          </p>
        )}
        <div ref={fin} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); if (texto.trim()) lanzar(texto.trim()); }}
        className="shrink-0 border-t border-[var(--borde)] p-3"
      >
        <div className="flex gap-2">
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="¿Cuánto debe Carlos en todo el grupo?"
            disabled={cargando}
            className="min-w-0 flex-1 rounded-md border border-[var(--borde)] bg-[#0b0f19] px-3 py-2 text-[13px] outline-none focus:border-[#3b4a6b] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={cargando || !texto.trim()}
            className="shrink-0 rounded-md bg-[#2a3a5c] px-3 py-2 text-[13px] font-medium transition hover:bg-[#33466e] disabled:opacity-40"
          >
            Preguntar
          </button>
        </div>
        {turnos.length > 0 && (
          <button
            type="button"
            onClick={() => { setTurnos([]); onRespuesta(null); }}
            className="mt-2 text-[11px] tenue hover:underline"
          >
            Empezar de nuevo
          </button>
        )}
      </form>
    </div>
  );
}
