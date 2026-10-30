"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowLeft, ArrowRight, Search, Check, MapPin } from "lucide-react";
import { useResource } from "@/lib/use-resource";
import { useApp } from "./providers";
import type { Line, Page, Route } from "@/lib/types";
import { canRegisterTrip, officialStops, routeDataMessage } from "@/lib/route-data";
import {
  Heading,
  LineCard,
  LineBadge,
  ProgressBar,
  Loading,
  Empty,
  ErrorState,
  TripCTA,
  Pagination,
} from "./ui";
import { CatalogNotice } from "./home-screen";
const MapView = dynamic(() => import("./map-view").then((m) => m.MapView), {
  ssr: false,
  loading: () => <Loading label="Preparando el mapa…" />,
});

export function LinesScreen() {
  const { user } = useApp();
  const [search, setSearch] = useState("");
  const [travelled, setTravelled] = useState(false);
  const [page, setPage] = useState(1);
  const lines = useResource<Page<Line>>(
    `lineas/?search=${encodeURIComponent(search)}&page=${page}${travelled ? "&estado=recorridas" : ""}`,
  );
  return (
    <>
      <Heading
        eyebrow="EL AMBA TIENE MUCHO PARA CONTAR"
        title="Explorá tu próxima línea"
        text="Las de siempre y las que todavía te faltan. Cada una tiene su propia historia."
        action={user && <TripCTA />}
      />
      <CatalogNotice />
      <div className="toolbar">
        <label className="search-bar">
          <Search size={18} />
          <span className="sr-only">Buscar línea</span>
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Buscá por número o nombre de línea"
          />
        </label>
        {user && (
          <button
            className="filter-button"
            aria-pressed={travelled}
            onClick={() => {
              setTravelled(!travelled);
              setPage(1);
            }}
          >
            Mis líneas recorridas
          </button>
        )}
      </div>
      {lines.loading ? (
        <Loading />
      ) : lines.error ? (
        <ErrorState message={lines.error} retry={lines.reload} />
      ) : lines.data?.results.length ? (
        <>
          <p className="results-label">
            {lines.data.count} líneas para{" "}
            {travelled ? "seguir bondiando" : "descubrir"}
          </p>
          <div className="line-grid">
            {lines.data.results.map((line) => (
              <LineCard key={line.id} line={line} />
            ))}
          </div>
          <Pagination page={page} count={lines.data.count} onChange={setPage} />
        </>
      ) : (
        <Empty
          title="No encontramos esa línea"
          text="Probá con otro número o quitá el filtro para explorar el catálogo."
        />
      )}
    </>
  );
}

export function LineDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const { user } = useApp();
  const line = useResource<Line>(`lineas/${id}/`);
  const routes = useResource<Route[]>(`lineas/${id}/recorridos/`);
  if (line.loading) return <Loading />;
  if (line.error || !line.data)
    return (
      <ErrorState
        message={line.error || "No encontramos esta línea."}
        retry={line.reload}
      />
    );
  const data = line.data;
  return (
    <>
      <Link className="back-link" href="/lineas">
        <ArrowLeft size={15} /> Todas las líneas
      </Link>
      <div className="page-heading">
        <div className="line-detail-heading">
          <LineBadge numero={data.numero} colores={data.colores} />
          <div>
            <h1>Línea {data.numero}</h1>
            <p>
              {data.nombre ||
                `${data.ramales_count} ramales · Una nueva parte de tu colección`}
            </p>
          </div>
        </div>
        {routes.data?.some(canRegisterTrip) && (
          <Link className="button" href={`/viajes/nuevo?linea=${id}`}>
            Registrar viaje <ArrowRight size={16} />
          </Link>
        )}
      </div>
      <CatalogNotice />
      {user && (
        <section className="panel mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3>Tu progreso en la {data.numero}</h3>
            {data.progreso.completo && (
              <span className="pill earned">
                <Check size={12} /> Línea completada
              </span>
            )}
          </div>
          <ProgressBar
            value={data.progreso.porcentaje}
            label={`${data.progreso.transitadas} de ${data.progreso.total} paradas transitadas`}
          />
        </section>
      )}
      <div className="split-grid">
        <section>
          <h2 className="mb-5">Elegí un ramal</h2>
          {data.progreso.ramales.length ? (
            data.progreso.ramales.map((branch) => (
              <article className="route-card" key={branch.id}>
                <div className="route-card-top">
                  <div>
                    <h3>Ramal {branch.nombre}</h3>
                    <p>
                      {branch.recorridos.length} sentidos disponibles ·{" "}
                      {branch.total} paradas únicas
                    </p>
                  </div>
                  {branch.completo && (
                    <span className="pill earned">
                      <Check size={12} /> Completo
                    </span>
                  )}
                </div>
                {user && (
                  <div className="mb-4">
                    <ProgressBar
                      value={branch.porcentaje}
                      label="Tu recorrido"
                    />
                  </div>
                )}
                <div className="route-choices">
                  {branch.recorridos.map((route) => (
                    <Link href={`/recorridos/${route.id}`} key={route.id}>
                      {route.sentido === "IDA" ? "Ida" : "Vuelta"}
                      <span>
                        {user
                          ? `${route.transitadas}/${route.total}`
                          : `${route.total} paradas`}
                      </span>
                      <ArrowRight size={13} />
                    </Link>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <Empty
              title="Los ramales están por llegar"
              text="Esta línea todavía no tiene recorridos disponibles."
            />
          )}
        </section>
        <section>
          <h2 className="mb-5">La línea en el mapa</h2>
          {routes.loading ? (
            <Loading />
          ) : routes.error ? (
            <ErrorState message={routes.error} retry={routes.reload} />
          ) : (
            <MapView routes={routes.data || []} />
          )}
          <p className="caption mt-3">
            Los sentidos comparten progreso cuando usan la misma parada física
            dentro de esta línea.
          </p>
        </section>
      </div>
    </>
  );
}

export function RouteDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const route = useResource<Route>(`recorridos/${id}/`);
  if (route.loading) return <Loading />;
  if (route.error || !route.data)
    return (
      <ErrorState
        message={route.error || "No encontramos este recorrido."}
        retry={route.reload}
      />
    );
  const data = route.data;
  const stops = officialStops(data);
  const done = stops.filter((p) => p.transitada).length;
  const usable = canRegisterTrip(data);
  return (
    <>
      <Link className="back-link" href={`/lineas/${data.linea}`}>
        <ArrowLeft size={15} /> Línea {data.linea_numero}
      </Link>
      <Heading
        eyebrow={`LÍNEA ${data.linea_numero} · ${data.sentido}`}
        title={`Ramal ${data.ramal_nombre}`}
        text={`${data.desde} → ${data.hasta}`}
        action={
          usable && <Link
            className="button"
            href={`/viajes/nuevo?linea=${data.linea}&recorrido=${data.id}`}
          >
            Registrar viaje <ArrowRight size={16} />
          </Link>
        }
      />
      <CatalogNotice />
      {!usable && <p className="notice">{routeDataMessage(data)}</p>}
      <div className="split-grid">
        <section>
          <MapView routes={[data]} />
          {stops.length > 0 && (
            <div className="panel mt-5">
              <ProgressBar
                value={(100 * done) / stops.length}
                label={`${done} de ${stops.length} paradas oficiales transitadas`}
              />
            </div>
          )}
        </section>
        <section className="panel">
          <h2>Parada a parada</h2>
          <p className="caption mt-2">
            Paradas oficiales · En orden de recorrido · {data.sentido.toLowerCase()}
          </p>
          {stops.length ? (
            <ol className="stop-list stop-scroll">
              {stops.map((stop) => (
                <li key={stop.id}>
                  <span
                    className={`stop-dot ${stop.transitada ? "visited" : ""}`}
                  />
                  <b>
                    {stop.parada.nombre ||
                      stop.parada.direccion ||
                      `Parada ${stop.orden}`}
                  </b>
                  <small>
                    {stop.transitada ? "Transitada" : "Pendiente"}
                    {stop.parada.barrio ? ` · ${stop.parada.barrio}` : ""}
                  </small>
                  {stop.transitada && (
                    <Check className="stop-check" size={14} />
                  )}
                </li>
              ))}
            </ol>
          ) : (
            <Empty
              title="Paradas aún no disponibles"
              text="Estamos incorporando los datos oficiales. El registro se habilita cuando haya una secuencia disponible."
            />
          )}
        </section>
      </div>
    </>
  );
}

export function MapScreen() {
  const [search, setSearch] = useState("");
  const [lineId, setLineId] = useState("");
  const lines = useResource<Page<Line>>(
    `lineas/?search=${encodeURIComponent(search)}`,
  );
  const selected = lineId || String(lines.data?.results[0]?.id || "");
  const routes = useResource<Route[]>(
    selected ? `lineas/${selected}/recorridos/` : null,
  );
  return (
    <>
      <Heading
        eyebrow="MIRÁ TODO LO QUE TE ESPERA"
        title="El mapa de tu colección"
        text="Elegí una línea, acercate y descubrí los recorridos, parada a parada."
      />
      <CatalogNotice />
      <div className="toolbar">
        <label className="search-bar">
          <Search size={17} />
          <span className="sr-only">Buscar línea para el mapa</span>
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setLineId("");
            }}
            placeholder="Buscá una línea para explorar"
          />
        </label>
        <label className="field">
          <span className="sr-only">Línea en el mapa</span>
          <select value={selected} onChange={(e) => setLineId(e.target.value)}>
            {lines.data?.results.map((line) => (
              <option key={line.id} value={line.id}>
                Línea {line.numero}
              </option>
            ))}
            {!lines.data?.results.length && (
              <option value="">Sin líneas</option>
            )}
          </select>
        </label>
        {selected && (
          <Link className="button secondary" href={`/lineas/${selected}`}>
            Ver línea <ArrowRight size={15} />
          </Link>
        )}
      </div>
      {lines.error ? (
        <ErrorState message={lines.error} retry={lines.reload} />
      ) : !lines.loading && !lines.data?.results.length ? (
        <Empty
          title="No hay líneas para mostrar"
          text="Buscá otro número o volvé a explorar el catálogo."
        />
      ) : routes.loading ? (
        <Loading label="Trazando los recorridos…" />
      ) : routes.error ? (
        <ErrorState message={routes.error} retry={routes.reload} />
      ) : (
        <MapView routes={routes.data || []} full />
      )}
      <p className="caption mt-4 inline-note">
        <MapPin size={14} /> Seleccioná una parada para ver su nombre y estado.
        También podés consultar la lista accesible en el detalle del recorrido.
      </p>
    </>
  );
}
