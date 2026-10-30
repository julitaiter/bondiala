"use client";
import Link from "next/link";
import {
  ArrowRight,
  MapPin,
  Route,
  Ticket,
  Check,
  Layers,
  Compass,
  Info,
} from "lucide-react";
import { useResource } from "@/lib/use-resource";
import type { Line, Page } from "@/lib/types";
import { LineBadge, LineCard, Loading, ErrorState } from "./ui";

export function CatalogNotice() {
  const status = useResource<{ muestra: boolean }>("estado/");
  return status.data?.muestra ? (
    <div className="demo-banner">
      <Info size={14} className="shrink-0" />
      <span>
        Estamos incorporando paradas oficiales de BA Data. El registro se
        habilita en recorridos con una secuencia disponible; los datos
        ilustrativos se conservan únicamente en el historial.
      </span>
    </div>
  ) : null;
}
export default function HomeScreen() {
  const lines = useResource<Page<Line>>("lineas/");
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">TU PRÓXIMA PARADA: DESCUBRIR</span>
          <h1>
            El AMBA es
            <br />
            una gran
            <br />
            <span>colección.</span>
          </h1>
          <p>
            Ese bondi que tomás todos los días también puede llevarte a algo
            nuevo. Registrá tus viajes y descubrí cuánto de la ciudad ya
            recorriste.
          </p>
          <div className="hero-actions">
            <Link href="/registro" className="button">
              Empezá a bondiar <ArrowRight size={17} />
            </Link>
            <Link href="/lineas" className="text-link">
              Explorar líneas <ArrowRight size={15} />
            </Link>
          </div>
          <span className="hero-note">
            <Check size={13} /> Tu recorrido, a tu ritmo. Cada viaje cuenta.
          </span>
        </div>
        <div className="hero-art" aria-hidden="true">
          <svg viewBox="0 0 430 420" preserveAspectRatio="xMidYMid slice">
            <defs>
              <pattern
                id="streets"
                width="46"
                height="46"
                patternTransform="rotate(-24)"
                patternUnits="userSpaceOnUse"
              >
                <path d="M 46 0 L 0 0 0 46" className="gridline" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#streets)" />
            <path
              d="M-20 332 96 332 96 228 236 228 236 90 460 90"
              className="route-yellow"
            />
            <path
              d="M-10 120 150 120 150 290 340 290 340 450"
              className="route-blue"
            />
            <path
              d="M50 440 50 360 292 360 292 160 450 160"
              className="route-navy"
            />
            {[
              [96, 332],
              [96, 228],
              [236, 228],
              [236, 90],
              [150, 120],
              [150, 290],
              [340, 290],
              [50, 360],
              [292, 360],
              [292, 160],
            ].map(([x, y]) => (
              <circle
                key={`${x}-${y}`}
                cx={x}
                cy={y}
                r="6"
                fill="var(--surface)"
                stroke="var(--text-primary)"
                strokeWidth="2"
              />
            ))}
          </svg>
          <div className="hero-floating one">
            <LineBadge
              numero="2"
              small
              colores={{
                color_principal: "#BE1F1C",
                color_secundario_1: "#CCC7B1",
                color_secundario_2: "#1D3B78",
                color_texto: "#FFFFFF",
              }}
            />
            <div>
              <b>Un recorrido más.</b>
              <small>Una historia para coleccionar.</small>
            </div>
          </div>
          <div className="hero-floating two">
            <span
              className="achievement-icon"
              style={{
                background: "var(--brand-accent)",
                color: "var(--on-accent)",
                width: 40,
                height: 43,
              }}
            >
              <MapPin size={20} />
            </span>
            <div>
              <b>Cada parada cuenta</b>
              <small>Descubrí lo que te falta.</small>
            </div>
          </div>
          <span className="hero-art-caption">
            RECORRÉ. COMPLETÁ. COLECCIONÁ.
          </span>
        </div>
      </section>
      <section className="intro-strip" aria-label="Cómo funciona">
        {(
          [
            [
              Ticket,
              "Subite a una línea",
              "Elegí el ramal y registrá dónde subiste y bajaste.",
            ],
            [
              Route,
              "Sumá nuevos recorridos",
              "Cada parada nueva hace crecer tu colección.",
            ],
            [
              Layers,
              "Completá tu colección",
              "Ganás puntos, desbloqueás logros y seguís explorando.",
            ],
          ] as const
        ).map(([Icon, title, text]) => (
          <article key={title}>
            <span>
              <Icon size={18} />
            </span>
            <div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          </article>
        ))}
      </section>
      <div className="section-head">
        <div>
          <span className="eyebrow">HAY MUCHO POR DESCUBRIR</span>
          <h2>¿Cuál vas a bondiar primero?</h2>
        </div>
        <Link className="text-link" href="/lineas">
          Ver todas <ArrowRight size={15} />
        </Link>
      </div>
      <CatalogNotice />
      {lines.loading ? (
        <Loading label="Buscando líneas para tu colección…" />
      ) : lines.error ? (
        <ErrorState message={lines.error} retry={lines.reload} />
      ) : lines.data?.results.length ? (
        <div className="line-grid">
          {lines.data.results.slice(0, 6).map((line) => (
            <LineCard key={line.id} line={line} />
          ))}
        </div>
      ) : (
        <p className="panel">
          Todavía no hay líneas en el catálogo. Volvé pronto para descubrir los
          primeros recorridos.
        </p>
      )}
      <section className="collection-callout">
        <Compass size={35} />
        <div>
          <h2>La ciudad se conoce desde la ventanilla.</h2>
          <p>
            Una parada nueva. Un ramal completo. Una línea que ya es parte de tu
            historia.
          </p>
        </div>
        <Link href="/registro" className="button secondary">
          Creá tu colección <ArrowRight size={16} />
        </Link>
      </section>
    </>
  );
}
