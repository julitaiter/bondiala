"use client";
import { useRef, useState, Suspense, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Check, Search, MapPin, Trophy } from "lucide-react";
import { useResource } from "@/lib/use-resource";
import { mutate } from "@/lib/api";
import type { Line, Page, Route, Trip } from "@/lib/types";
import { useApp } from "./providers";
import {
  Gate,
  Heading,
  Loading,
  ErrorState,
  LineBadge,
  ProgressBar,
  PrivateNote,
  Empty,
  Pagination,
} from "./ui";
import { CatalogNotice } from "./home-screen";

export function TripScreen() {
  return (
    <Gate>
      <Suspense fallback={<Loading />}>
        <TripForm />
      </Suspense>
    </Gate>
  );
}
function TripForm() {
  const query = useSearchParams();
  const { refresh } = useApp();
  const [search, setSearch] = useState("");
  const [selectedLineId, setLineId] = useState<string | null>(null);
  const lineId = selectedLineId ?? query.get("linea") ?? "";
  const [branchId, setBranchId] = useState("");
  const [selectedRouteId, setRouteId] = useState<string | null>(null);
  const routeId = selectedRouteId ?? query.get("recorrido") ?? "";
  const [startId, setStartId] = useState("");
  const [endId, setEndId] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Trip | null>(null);
  const key = useRef("");
  const lines = useResource<Page<Line>>(
    `lineas/?search=${encodeURIComponent(search)}`,
  );
  const chosenLine = useResource<Line>(lineId ? `lineas/${lineId}/` : null);
  const routes = useResource<Route[]>(
    lineId ? `lineas/${lineId}/recorridos/` : null,
  );
  const available = (routes.data || []).filter(
    (r) => String(r.linea) === lineId,
  );
  const initialRoute = available.find((r) => String(r.id) === routeId);
  const branch =
    branchId || String(initialRoute?.ramal || available[0]?.ramal || "");
  const branchRoutes = available.filter((r) => String(r.ramal) === branch);
  const route =
    branchRoutes.find((r) => String(r.id) === routeId) || branchRoutes[0];
  const branches = Array.from(
    new Map(available.map((r) => [r.ramal, r.ramal_nombre])).entries(),
  );
  const lineOptions = [...(lines.data?.results || [])];
  if (
    chosenLine.data &&
    String(chosenLine.data.id) === lineId &&
    !lineOptions.some((l) => String(l.id) === lineId)
  )
    lineOptions.unshift(chosenLine.data);
  const start = route?.paradas.find((p) => String(p.id) === startId);
  const end = route?.paradas.find((p) => String(p.id) === endId);
  const valid = Boolean(route && start && end && start.orden < end.orden);
  function resetSegment() {
    setStartId("");
    setEndId("");
    setConfirm(false);
    setError("");
    key.current = "";
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid || !route || busy) return;
    if (!confirm) {
      setConfirm(true);
      return;
    }
    setBusy(true);
    setError("");
    if (!key.current) key.current = crypto.randomUUID();
    try {
      const trip = await mutate<Trip>("viajes/", {
        recorrido: route.id,
        inicio: Number(startId),
        fin: Number(endId),
        idempotency_key: key.current,
      });
      setResult(trip);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pudimos guardar tu viaje.");
    } finally {
      setBusy(false);
    }
  }
  if (result)
    return (
      <section className="trip-success">
        <div className="success-symbol">
          <Check size={33} />
        </div>
        <span className="eyebrow">UN VIAJE MÁS EN TU HISTORIA</span>
        <h1>
          {result.resultado.progreso.completo
            ? "¡Línea completada!"
            : "Ya es parte de tu colección."}
        </h1>
        <p>
          Línea {result.linea_numero} · Ramal {result.ramal_nombre} ·{" "}
          {result.sentido.toLowerCase()}
        </p>
        <div className="reward-grid">
          <div>
            <MapPin className="mx-auto mb-3" size={21} />
            <strong>{result.resultado.nuevas_paradas}</strong>
            <span>paradas nuevas</span>
          </div>
          <div>
            <Trophy className="mx-auto mb-3" size={21} />
            <strong>+{result.resultado.puntos}</strong>
            <span>puntos ganados</span>
          </div>
        </div>
        {result.resultado.nuevas_paradas === 0 && (
          <p className="caption">
            Ya habías transitado estas paradas. Tu viaje quedó guardado en el
            historial.
          </p>
        )}
        <div className="panel max-w-lg mx-auto">
          <ProgressBar
            value={result.resultado.progreso.porcentaje}
            label={`Tu progreso en la línea ${result.linea_numero}`}
          />
          {result.resultado.logros.map((logro) => (
            <p className="notice success" key={logro.slug}>
              <Trophy size={18} />
              {logro.nombre} · Nuevo logro
            </p>
          ))}
        </div>
        <div className="actions">
          <Link href="/dashboard" className="button">
            Ver mi colección <ArrowRight size={17} />
          </Link>
          <button
            className="button secondary"
            onClick={() => {
              setResult(null);
              resetSegment();
            }}
          >
            Registrar otro viaje
          </button>
        </div>
      </section>
    );
  return (
    <>
      <Heading
        eyebrow="CADA VIAJE CUENTA"
        title="Sumá un nuevo recorrido"
        text="Contanos dónde subiste y bajaste. Las paradas del medio se suman a tu colección."
      />
      <CatalogNotice />
      <div className="split-grid">
        <section className="panel">
          <div className="trip-steps">
            <b>1</b>
            <span>Elegí el recorrido</span>
            <ArrowRight size={15} />
            <b>2</b>
            <span>Subida y bajada</span>
            <ArrowRight size={15} />
            <b>3</b>
            <span>Guardá</span>
          </div>
          <form className="form-stack" onSubmit={submit}>
            <label className="search-bar">
              <Search size={16} />
              <span className="sr-only">Buscar línea</span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscá tu línea por número"
                disabled={busy || confirm}
              />
            </label>
            {lines.error && (
              <ErrorState message={lines.error} retry={lines.reload} />
            )}
            <label className="field">
              Línea
              <select
                required
                value={lineId}
                disabled={busy || confirm}
                onChange={(e) => {
                  setLineId(e.target.value);
                  setBranchId("");
                  setRouteId("");
                  resetSegment();
                }}
              >
                <option value="">Seleccioná una línea</option>
                {lineOptions.map((line) => (
                  <option value={line.id} key={line.id}>
                    Línea {line.numero}
                  </option>
                ))}
              </select>
            </label>
            <div className="field-row">
              <label className="field">
                Ramal
                <select
                  required
                  value={branch}
                  disabled={!available.length || busy || confirm}
                  onChange={(e) => {
                    setBranchId(e.target.value);
                    setRouteId("");
                    resetSegment();
                  }}
                >
                  {!branches.length && (
                    <option value="">Elegí una línea primero</option>
                  )}
                  {branches.map(([id, name]) => (
                    <option value={id} key={id}>
                      Ramal {name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Sentido
                <select
                  required
                  value={route?.id || ""}
                  disabled={!branchRoutes.length || busy || confirm}
                  onChange={(e) => {
                    setRouteId(e.target.value);
                    resetSegment();
                  }}
                >
                  {!branchRoutes.length && (
                    <option value="">Elegí un ramal primero</option>
                  )}
                  {branchRoutes.map((r) => (
                    <option value={r.id} key={r.id}>
                      {r.sentido === "IDA" ? "Ida" : "Vuelta"}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {routes.error && (
              <ErrorState message={routes.error} retry={routes.reload} />
            )}
            <label className="field">
              ¿Dónde subiste?
              <select
                required
                value={startId}
                disabled={!route?.paradas.length || busy || confirm}
                onChange={(e) => {
                  setStartId(e.target.value);
                  setEndId("");
                  setConfirm(false);
                  key.current = "";
                }}
              >
                <option value="">Seleccioná la parada de subida</option>
                {route?.paradas.slice(0, -1).map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.orden}. {p.parada.nombre || p.parada.direccion}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              ¿Dónde bajaste?
              <select
                required
                value={endId}
                disabled={!start || busy || confirm}
                onChange={(e) => {
                  setEndId(e.target.value);
                  setConfirm(false);
                  key.current = "";
                }}
              >
                <option value="">Seleccioná la parada de bajada</option>
                {route?.paradas
                  .filter((p) => start && p.orden > start.orden)
                  .map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.orden}. {p.parada.nombre || p.parada.direccion}
                    </option>
                  ))}
              </select>
            </label>
            {route && !route.paradas.length && (
              <p className="notice">
                Este recorrido todavía no tiene una secuencia de paradas
                disponible.
              </p>
            )}
            {confirm && valid && (
              <div className="notice">
                <Check size={20} />
                <span>
                  Vas a registrar el tramo de <b>{start?.parada.nombre}</b> a{" "}
                  <b>{end?.parada.nombre}</b>, incluyendo las paradas
                  intermedias.
                </span>
              </div>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button full" disabled={!valid || busy}>
              {busy
                ? "Guardando tu viaje…"
                : confirm
                  ? "Confirmar y guardar"
                  : "Revisar viaje"}
              <ArrowRight size={17} />
            </button>
            {confirm && (
              <button
                className="button secondary"
                type="button"
                disabled={busy}
                onClick={() => setConfirm(false)}
              >
                Editar selección
              </button>
            )}
          </form>
          <PrivateNote />
        </section>
        <aside>
          <section className="panel">
            <span className="eyebrow">ASÍ CRECE TU COLECCIÓN</span>
            <h2>Todo lo que hay en el medio.</h2>
            <p className="mt-4 text-sm leading-7">
              No hace falta marcar cada parada ni completar el ramal de una sola
              vez. Registramos el tramo que recorriste y reconocemos tus avances
              anteriores.
            </p>
            {route && (
              <div className="trip-summary">
                <LineBadge
                  numero={route.linea_numero}
                  colores={route.colores}
                  small
                />
                <div>
                  <strong>
                    Ramal {route.ramal_nombre} · {route.sentido.toLowerCase()}
                  </strong>
                  <p>{route.paradas.length} paradas en este recorrido</p>
                </div>
              </div>
            )}
            <div className="mt-6">
              <p className="caption">
                +1 por parada nueva · +5 por sentido completo
                <br />
                +15 por ramal · +50 por línea completa
              </p>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}

export function HistoryScreen() {
  return (
    <Gate>
      <History />
    </Gate>
  );
}
function History() {
  const [page, setPage] = useState(1);
  const trips = useResource<Page<Trip>>(`viajes/?page=${page}`);
  return (
    <>
      <Heading
        eyebrow="TU HISTORIA SOBRE RUEDAS"
        title="Tus viajes"
        text="Cada tramo que sumaste a tu colección, en un solo lugar."
        action={
          <Link href="/viajes/nuevo" className="button">
            Registrar viaje <ArrowRight size={16} />
          </Link>
        }
      />
      <PrivateNote />
      {trips.loading ? (
        <Loading />
      ) : trips.error ? (
        <ErrorState message={trips.error} retry={trips.reload} />
      ) : trips.data?.results.length ? (
        <>
          <section className="panel mt-5">
            {trips.data.results.map((trip) => (
              <Link
                href={`/recorridos/${trip.recorrido}`}
                key={trip.id}
                className="history-row"
              >
                <LineBadge small numero={trip.linea_numero} />
                <div>
                  <b>
                    Línea {trip.linea_numero} · Ramal {trip.ramal_nombre} ·{" "}
                    {trip.sentido.toLowerCase()}
                  </b>
                  <p>
                    {trip.inicio_nombre} → {trip.fin_nombre}
                  </p>
                  <p>
                    {new Date(trip.fecha).toLocaleDateString("es-AR")} ·{" "}
                    {trip.resultado.nuevas_paradas} paradas nuevas
                  </p>
                </div>
                <span>+{trip.resultado.puntos} pts</span>
              </Link>
            ))}
          </section>
          <Pagination page={page} count={trips.data.count} onChange={setPage} />
        </>
      ) : (
        <Empty
          title="Tu historial empieza en el próximo viaje"
          text="Registrá dónde subiste y bajaste para sumar tu primer recorrido."
          href="/viajes/nuevo"
          cta="Registrar viaje"
        />
      )}
    </>
  );
}
