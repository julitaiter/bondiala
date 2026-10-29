"use client";
import Link from "next/link";
import { ArrowRight, MapPin } from "lucide-react";
import { useApp } from "./providers";
import { useResource } from "@/lib/use-resource";
import type { Line, Page, RankingRow, Trip } from "@/lib/types";
import {
  Gate,
  Metrics,
  TripCTA,
  LineCard,
  ProgressBar,
  LineBadge,
  Avatar,
  Empty,
  Loading,
  ErrorState,
  number,
} from "./ui";
import { CatalogNotice } from "./home-screen";

export default function DashboardScreen() {
  return (
    <Gate>
      <Dashboard />
    </Gate>
  );
}
function Dashboard() {
  const { user } = useApp();
  const lines = useResource<Page<Line>>("lineas/?estado=recorridas");
  const trips = useResource<Page<Trip>>("viajes/");
  const board = useResource<Page<RankingRow>>("rankings/?tipo=semanal");
  if (!user) return null;
  const levelProgress = user.nivel.siguiente
    ? (100 * (user.puntos - user.nivel.puntos_minimos)) /
      (user.nivel.siguiente.puntos_minimos - user.nivel.puntos_minimos)
    : 100;
  return (
    <>
      <div className="dashboard-welcome">
        <div>
          <span className="eyebrow">TU COLECCIÓN SIGUE EN MOVIMIENTO</span>
          <h1>¿Qué vas a bondiar hoy, {user.nickname}?</h1>
          <p>Cada viaje tiene algo nuevo. Mirá todo lo que ya descubriste.</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-5 flex-wrap mt-6">
        <div className="collection-level">
          <span className="level-number">{user.nivel.numero}</span>
          <div>
            <h3>{user.nivel.nombre}</h3>
            <p>
              {number(user.puntos)} pts{" "}
              {user.nivel.siguiente
                ? `· ${number(user.nivel.siguiente.puntos_minimos - user.puntos)} para el próximo nivel`
                : "· Llegaste al nivel máximo"}
            </p>
            <ProgressBar value={levelProgress} />
          </div>
        </div>
        <TripCTA />
      </div>
      <Metrics
        stops={user.paradas}
        lines={user.lineas_recorridas}
        branches={user.ramales_completos}
        points={user.puntos}
      />
      <CatalogNotice />
      <div className="section-head">
        <h2>Seguir bondiando</h2>
        <Link href="/lineas" className="text-link">
          Ver mi colección <ArrowRight size={15} />
        </Link>
      </div>
      {lines.loading ? (
        <Loading />
      ) : lines.error ? (
        <ErrorState message={lines.error} retry={lines.reload} />
      ) : lines.data?.results.length ? (
        <div className="line-grid">
          {lines.data.results.slice(0, 6).map((line) => (
            <LineCard key={line.id} line={line} />
          ))}
        </div>
      ) : (
        <Empty
          title="Tu primera línea está por llegar"
          text="Registrá un viaje y empezá a llenar tu colección de paradas e historias."
          href="/viajes/nuevo"
          cta="Registrar mi primer viaje"
        />
      )}
      <div className="dashboard-bottom">
        <section className="panel">
          <div className="section-head mt-0">
            <h2>Tu próximo objetivo</h2>
            <MapPin size={20} className="muted" />
          </div>
          {lines.data?.results
            .filter((l) => !l.progreso.completo)
            .slice(0, 3)
            .map((line) => (
              <Link
                href={`/lineas/${line.id}`}
                className="goal-card"
                key={line.id}
              >
                <LineBadge small numero={line.numero} colores={line.colores} />
                <div>
                  <h3>Un poco más de la {line.numero}</h3>
                  <p>
                    Te faltan {line.progreso.total - line.progreso.transitadas}{" "}
                    paradas
                  </p>
                  <ProgressBar value={line.progreso.porcentaje} />
                </div>
                <ArrowRight size={17} />
              </Link>
            ))}
          {!lines.data?.results.some((l) => !l.progreso.completo) && (
            <p className="empty-inline">
              Bondiá una línea nueva y descubrí tu próximo objetivo.
            </p>
          )}
        </section>
        <section className="panel">
          <div className="section-head mt-0">
            <h2>Esta semana</h2>
            <Link href="/ranking" className="text-link">
              Ver ranking <ArrowRight size={14} />
            </Link>
          </div>
          {board.error ? (
            <ErrorState message={board.error} retry={board.reload} />
          ) : board.loading ? (
            <Loading />
          ) : (
            board.data?.results.slice(0, 3).map((row) => (
              <Link
                href={`/perfil/${row.username}`}
                className="ranking-row"
                key={row.id}
              >
                <span className="rank-number">{row.posicion}</span>
                <Avatar user={row} />
                <span className="rank-info">
                  <strong>{row.nickname}</strong>
                  <small>{row.nivel.nombre}</small>
                </span>
                <b>
                  {number(row.puntos)} <small>pts</small>
                </b>
              </Link>
            ))
          )}
        </section>
      </div>
      <div className="section-head">
        <h2>Últimos viajes</h2>
        <Link href="/viajes" className="text-link">
          Ver historial <ArrowRight size={15} />
        </Link>
      </div>
      <section className="panel">
        {trips.loading ? (
          <Loading />
        ) : trips.error ? (
          <ErrorState message={trips.error} retry={trips.reload} />
        ) : trips.data?.results.length ? (
          trips.data.results.slice(0, 3).map((trip) => (
            <div key={trip.id} className="history-row">
              <LineBadge numero={trip.linea_numero} small />
              <div>
                <b>
                  Línea {trip.linea_numero} · Ramal {trip.ramal_nombre}
                </b>
                <p>
                  {trip.inicio_nombre} → {trip.fin_nombre}
                </p>
              </div>
              <span>+{trip.resultado.puntos} pts</span>
            </div>
          ))
        ) : (
          <p className="empty-inline">
            Todavía no registraste viajes. El próximo puede ser el primero.
          </p>
        )}
      </section>
    </>
  );
}
