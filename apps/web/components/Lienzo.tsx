"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import type { AristaGrafo, NodoGrafo } from "@/lib/api";
import { color, colorTenue } from "@/lib/colores";
import { celda } from "@/lib/format";

let registrado = false;

// Propiedades que no aportan nada en el tooltip: la clave ya va en la cabecera,
// `raiz` es interno de la ontología y el vector es ruido.
const OCULTAS = new Set(["clave", "embedding", "longitud", "raiz", "dimension"]);

type Tip =
  | { tipo: "nodo"; x: number; y: number; nodo: NodoGrafo }
  | { tipo: "arista"; x: number; y: number; arista: AristaGrafo;
      origen: string; destino: string };

interface Props {
  nodos: NodoGrafo[];
  aristas: AristaGrafo[];
  raiz?: string;
  seleccion?: string;
  onSeleccion?: (clave: string) => void;
}

export default function Lienzo({ nodos, aristas, raiz, seleccion, onSeleccion }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  useEffect(() => {
    let vivo = true;
    let limpiar: (() => void) | undefined;
    (async () => {
      if (!registrado) {
        const fcose = (await import("cytoscape-fcose")).default;
        cytoscape.use(fcose);
        registrado = true;
      }
      if (!vivo || !contenedor.current) return;

      const elementos: ElementDefinition[] = [
        ...nodos.map((n) => ({
          data: {
            id: n.clave, etiqueta: n.nombre?.slice(0, 26) ?? n.clave,
            dimension: n.dimension, label: n.label,
            raiz: n.clave === raiz ? 1 : 0,
            nodo: n,
          },
        })),
        ...aristas
          .filter((a) => a.desde && a.hasta)
          .map((a, i) => ({
            data: {
              id: `e${i}`, source: a.desde, target: a.hasta,
              relacion: a.relacion, dimension: a.dimension,
              arista: a,
            },
          })),
      ];

      cy.current?.destroy();
      const instancia = cytoscape({
        container: contenedor.current,
        elements: elementos,
        wheelSensitivity: 0.2,
        style: [
          {
            selector: "node",
            style: {
              "background-color": (e) => color(e.data("dimension")),
              width: (e: cytoscape.NodeSingular) => (e.data("raiz") ? 26 : 13),
              height: (e: cytoscape.NodeSingular) => (e.data("raiz") ? 26 : 13),
              "border-width": (e) => (e.data("raiz") ? 3 : 0),
              "border-color": "#ffffff",
              label: (e: cytoscape.NodeSingular) =>
                e.data("raiz") ? e.data("etiqueta") : "",
              color: "#e5e7eb",
              "font-size": 11,
              "text-valign": "bottom",
              "text-margin-y": 6,
              "text-background-color": "#0b0f19",
              "text-background-opacity": 0.85,
              "text-background-padding": "3px",
            },
          },
          {
            selector: "node:selected",
            style: { "border-width": 3, "border-color": "#fde047", label: "data(etiqueta)" },
          },
          {
            selector: "edge",
            style: {
              width: 1,
              "line-color": (e) => color(e.data("dimension")),
              "line-opacity": 0.38,
              "curve-style": "haystack",
            },
          },
          {
            selector: ".resaltado",
            style: { "line-opacity": 1, width: 2.5 },
          },
        ],
        layout: {
          name: "fcose", quality: "default", animate: false,
          nodeRepulsion: 6500, idealEdgeLength: 55, numIter: 900,
          randomize: true, packComponents: true,
        } as cytoscape.LayoutOptions,
      });

      instancia.on("tap", "node", (ev) => onSeleccion?.(ev.target.id()));
      instancia.one("layoutstop", () => instancia.fit(undefined, 24));

      const nombrePorClave = new Map(nodos.map((n) => [n.clave, n.nombre]));
      const lienzo = contenedor.current;
      instancia.on("mouseover", "node", (ev) => {
        const p = ev.renderedPosition ?? ev.target.renderedPosition();
        setTip({ tipo: "nodo", x: p.x, y: p.y, nodo: ev.target.data("nodo") });
        ev.target.connectedEdges().addClass("resaltado");
        lienzo.style.cursor = "pointer";
      });
      instancia.on("mouseover", "edge", (ev) => {
        const a: AristaGrafo = ev.target.data("arista");
        const p = ev.renderedPosition ?? ev.target.midpoint();
        setTip({
          tipo: "arista", x: p.x, y: p.y, arista: a,
          origen: nombrePorClave.get(a.desde) ?? a.desde,
          destino: nombrePorClave.get(a.hasta) ?? a.hasta,
        });
        ev.target.addClass("resaltado");
        lienzo.style.cursor = "help";
      });
      instancia.on("mouseout", "node, edge", (ev) => {
        setTip(null);
        ev.target.removeClass("resaltado");
        ev.target.connectedEdges?.().removeClass("resaltado");
        lienzo.style.cursor = "";
      });
      // Sin esto el tooltip se queda colgado al arrastrar el lienzo.
      instancia.on("pan zoom drag", () => setTip(null));

      cy.current = instancia;

      // El contenedor todavia puede estar creciendo cuando se monta: sin esto
      // el layout se calcula sobre cero pixeles y los nodos quedan apilados.
      // Se compara contra el ultimo tamano porque `fit()` reajusta el lienzo y
      // volveria a disparar al observador: un bucle que nunca se estabiliza.
      let ancho = 0;
      let alto = 0;
      const observador = new ResizeObserver((entradas) => {
        const r = entradas[0]?.contentRect;
        if (!r || (Math.abs(r.width - ancho) < 1 && Math.abs(r.height - alto) < 1)) return;
        ancho = r.width;
        alto = r.height;
        instancia.resize();
        instancia.fit(undefined, 24);
      });
      observador.observe(contenedor.current);
      limpiar = () => observador.disconnect();
    })();

    return () => {
      vivo = false;
      limpiar?.();
      cy.current?.destroy();
      cy.current = null;
    };
  }, [nodos, aristas, raiz, onSeleccion]);

  useEffect(() => {
    const c = cy.current;
    if (!c || !seleccion) return;
    c.$(":selected").unselect();
    c.$id(seleccion).select();
  }, [seleccion]);

  // h-full y no `absolute inset-0`: Cytoscape fija `position: relative` en su
  // contenedor al inicializarse y anularia el posicionamiento absoluto, dejando
  // el div sin altura. El recorte lo hace el panel, que va con overflow-hidden.
  return (
    <div className="relative h-full w-full">
      <div ref={contenedor} className="h-full w-full" />
      {tip && <Tooltip tip={tip} caja={contenedor.current?.getBoundingClientRect()} />}
    </div>
  );
}

function Tooltip({ tip, caja }: { tip: Tip; caja?: DOMRect }) {
  const ANCHO = 250;
  const margen = 14;
  // Se voltea contra el borde para que no se salga del panel.
  const derecha = caja ? tip.x + ANCHO + margen > caja.width : false;
  const abajo = caja ? tip.y > caja.height * 0.6 : false;

  const estilo: React.CSSProperties = {
    width: ANCHO,
    left: derecha ? undefined : tip.x + margen,
    right: derecha && caja ? caja.width - tip.x + margen : undefined,
    top: abajo ? undefined : tip.y + margen,
    bottom: abajo && caja ? caja.height - tip.y + margen : undefined,
  };

  return (
    <div
      className="pointer-events-none absolute z-10 rounded-lg border border-[var(--borde)]
                 bg-[#0b0f19]/95 px-3 py-2 shadow-xl backdrop-blur-sm"
      style={estilo}
    >
      {tip.tipo === "nodo" ? <ContenidoNodo nodo={tip.nodo} /> : <ContenidoArista tip={tip} />}
    </div>
  );
}

function ContenidoNodo({ nodo }: { nodo: NodoGrafo }) {
  const props = Object.entries(nodo.props ?? {})
    // Se descarta el campo que ya se muestra como nombre, sea cual sea su clave.
    .filter(([k, v]) => !OCULTAS.has(k) && v !== null && v !== "" && v !== nodo.nombre)
    .slice(0, 7);
  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[13px] font-semibold leading-tight">{nodo.nombre}</span>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[10px]"
          style={{ background: colorTenue(nodo.dimension), color: color(nodo.dimension) }}
        >
          {nodo.label}
        </span>
      </div>
      <p className="mono mt-0.5 tenue">{nodo.clave}</p>
      {props.length > 0 && (
        <dl className="mt-2 space-y-0.5 border-t border-[var(--borde)] pt-1.5 text-[11px]">
          {props.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="tenue">{k}</dt>
              <dd className="truncate text-right">{celda(k, v)}</dd>
            </div>
          ))}
        </dl>
      )}
    </>
  );
}

function ContenidoArista({ tip }: { tip: Extract<Tip, { tipo: "arista" }> }) {
  const { arista, origen, destino } = tip;
  return (
    <>
      <div className="text-[11px] leading-snug">
        <span>{origen}</span>
        <span className="mx-1 font-medium" style={{ color: color(arista.dimension) }}>
          —{arista.relacion}→
        </span>
        <span>{destino}</span>
      </div>
      <p className="mt-1.5 border-t border-[var(--borde)] pt-1.5 text-[11px] tenue">
        {arista.fuente}
      </p>
    </>
  );
}
