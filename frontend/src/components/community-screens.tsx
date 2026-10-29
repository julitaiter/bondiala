"use client";
import { useState } from "react";
import Link from "next/link";
import {
  Award,
  Check,
  Lock,
  Search,
  UserPlus,
  UserMinus,
  ArrowRight,
} from "lucide-react";
import { useResource } from "@/lib/use-resource";
import { mutate, api } from "@/lib/api";
import { useApp } from "./providers";
import type {
  Page,
  RankingRow,
  Achievement,
  Follow,
  PublicUser,
} from "@/lib/types";
import {
  Heading,
  Loading,
  ErrorState,
  Empty,
  Avatar,
  number,
  ProgressBar,
  Pagination,
  Gate,
} from "./ui";

export function RankingScreen() {
  const { user } = useApp();
  const [tab, setTab] = useState("global");
  const [page, setPage] = useState(1);
  const board = useResource<Page<RankingRow>>(
    tab === "amigos" && !user ? null : `rankings/?tipo=${tab}&page=${page}`,
  );
  return (
    <>
      <Heading
        eyebrow="EXPLORAR TAMBIÉN SE COMPARTE"
        title="Nos vemos en el ranking"
        text="Cada parada suma. Encontrá tu lugar entre quienes también salen a descubrir el AMBA."
      />
      <div className="tabs" role="tablist" aria-label="Tipo de ranking">
        {[
          ["global", "Global"],
          ["semanal", "Esta semana"],
          ["amigos", "Amigos"],
        ].map(([value, label]) => (
          <button
            key={value}
            id={`tab-${value}`}
            role="tab"
            aria-selected={tab === value}
            aria-controls="ranking-panel"
            onClick={() => {
              setTab(value);
              setPage(1);
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <div id="ranking-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === "amigos" && !user ? (
          <Empty
            title="Bondiar entre amigos"
            text="Iniciá sesión y seguí a otros exploradores para comparar sus colecciones."
            href="/login"
            cta="Iniciar sesión"
          />
        ) : board.loading ? (
          <Loading />
        ) : board.error ? (
          <ErrorState message={board.error} retry={board.reload} />
        ) : board.data?.results.length ? (
          <>
            <section className="panel">
              <div className="flex justify-between pb-3 border-b border-[var(--border)]">
                <span className="eyebrow mb-0">
                  {tab === "semanal"
                    ? "DEL LUNES A HOY · HORA ARGENTINA"
                    : tab === "amigos"
                      ? "TU CÍRCULO DE EXPLORADORES"
                      : "LA COLECCIÓN DEL AMBA"}
                </span>
                <span className="caption muted">Puntos</span>
              </div>
              {board.data.results.map((row) => (
                <Link
                  href={`/perfil/${row.username}`}
                  key={row.id}
                  className={`ranking-row ${row.posicion === 1 ? "rank-first" : ""}`}
                >
                  <span className="rank-number">
                    {row.posicion.toString().padStart(2, "0")}
                  </span>
                  <Avatar user={row} />
                  <span className="rank-info">
                    <strong>
                      {row.nickname}
                      {row.id === user?.id ? " · vos" : ""}
                    </strong>
                    <small>
                      Nivel {row.nivel.numero} · {row.nivel.nombre}
                    </small>
                  </span>
                  <b>
                    {number(row.puntos)} <small>pts</small>
                  </b>
                </Link>
              ))}
            </section>
            <Pagination
              page={page}
              count={board.data.count}
              onChange={setPage}
            />
          </>
        ) : (
          <Empty
            title="El primer puesto está esperando"
            text="Creá tu cuenta, registrá tu primer viaje y empezá a sumar puntos."
            href="/registro"
            cta="Crear cuenta"
          />
        )}
      </div>
      <p className="caption mt-5">
        El ranking semanal comienza cada lunes a las 00:00 de Argentina. Solo
        aparecen perfiles públicos.
      </p>
    </>
  );
}

export function AchievementsScreen() {
  const [earnedOnly, setEarnedOnly] = useState(false);
  const [page, setPage] = useState(1);
  const achievements = useResource<Page<Achievement>>(
    `logros/?page=${page}${earnedOnly ? "&obtenidos=true" : ""}`,
  );
  const data =
    achievements.data?.results.filter((a) => !earnedOnly || a.obtenido) || [];
  return (
    <>
      <Heading
        eyebrow="PEQUEÑOS VIAJES. GRANDES HISTORIAS."
        title="Tus próximas conquistas"
        text="Hay un logro detrás de cada nueva forma de conocer la ciudad. Descubrí tu colección de insignias."
      />
      <div className="tabs" role="tablist" aria-label="Filtrar logros">
        <button
          role="tab"
          aria-selected={!earnedOnly}
          aria-controls="achievements-panel"
          onClick={() => setEarnedOnly(false)}
        >
          Todos los logros
        </button>
        <button
          role="tab"
          aria-selected={earnedOnly}
          aria-controls="achievements-panel"
          onClick={() => setEarnedOnly(true)}
        >
          Obtenidos
        </button>
      </div>
      <div id="achievements-panel" role="tabpanel">
        {achievements.loading ? (
          <Loading />
        ) : achievements.error ? (
          <ErrorState
            message={achievements.error}
            retry={achievements.reload}
          />
        ) : data.length ? (
          <div className="achievement-grid">
            {data.map((a) => (
              <article
                key={a.id}
                className={`achievement-card ${a.obtenido ? "is-earned" : ""}`}
              >
                <div className="achievement-icon">
                  <Award size={28} />
                </div>
                <span className={`pill ${a.obtenido ? "earned" : ""}`}>
                  {a.obtenido ? <Check size={11} /> : <Lock size={11} />}{" "}
                  {a.obtenido ? "En tu colección" : "Por descubrir"}
                </span>
                <h3>{a.nombre}</h3>
                <p>{a.descripcion}</p>
                <ProgressBar
                  value={(100 * a.progreso) / a.objetivo}
                  label={`${number(a.progreso)} / ${number(a.objetivo)}`}
                />
              </article>
            ))}
          </div>
        ) : (
          <Empty
            title="Tu primera insignia está cerca"
            text="Registrá un viaje para desbloquear tu primer logro."
            href="/viajes/nuevo"
            cta="Registrar viaje"
          />
        )}
      </div>
      {achievements.data && (
        <Pagination
          page={page}
          count={achievements.data.count}
          onChange={setPage}
        />
      )}
    </>
  );
}

export function FriendsScreen() {
  return (
    <Gate>
      <Friends />
    </Gate>
  );
}
function Friends() {
  const { user } = useApp();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [searchPage, setSearchPage] = useState(1);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const follows = useResource<Page<Follow>>(`amigos/?page=${page}`);
  const people = useResource<Page<PublicUser>>(
    search
      ? `perfiles/?search=${encodeURIComponent(search)}&page=${searchPage}`
      : null,
  );
  async function toggle(person: PublicUser) {
    setBusy(person.id);
    setError("");
    try {
      const existing =
        follows.data?.results.find((f) => f.usuario.id === person.id)?.id ||
        person.follow_id;
      if (existing) await api(`amigos/${existing}/`, { method: "DELETE" });
      else await mutate("amigos/", { seguido: person.id });
      follows.reload();
      people.reload();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo actualizar la relación.",
      );
    } finally {
      setBusy(null);
    }
  }
  const rows = search
    ? people.data?.results.filter((p) => p.id !== user?.id)
    : follows.data?.results.map((f) => f.usuario);
  const resource = search ? people : follows;
  return (
    <>
      <Heading
        eyebrow="LA EXPLORACIÓN SE CONTAGIA"
        title="Tu círculo de bondieros"
        text="Seguí a otros exploradores y compará sus avances en el ranking de amigos."
        action={
          <Link href="/ranking" className="button secondary">
            Ver rankings <ArrowRight size={16} />
          </Link>
        }
      />
      <label className="search-bar mb-6">
        <Search size={18} />
        <span className="sr-only">Buscar personas</span>
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSearchPage(1);
          }}
          placeholder="Buscá por nombre o usuario"
        />
      </label>
      {error && (
        <p role="alert" className="form-error mb-5">
          {error}
        </p>
      )}
      {resource.loading ? (
        <Loading />
      ) : resource.error ? (
        <ErrorState message={resource.error} retry={resource.reload} />
      ) : rows?.length ? (
        <>
          <section className="panel">
            {rows.map((person) => {
              const following =
                Boolean(person.follow_id) ||
                follows.data?.results.some((f) => f.usuario.id === person.id);
              return (
                <div className="people-row" key={person.id}>
                  <Link href={`/perfil/${person.username}`}>
                    <Avatar user={person} />
                    <span>
                      <b>{person.nickname}</b>
                      <small>@{person.username}</small>
                    </span>
                  </Link>
                  <button
                    className={`button ${following ? "secondary" : ""}`}
                    disabled={busy !== null}
                    onClick={() => void toggle(person)}
                  >
                    {following ? (
                      <UserMinus size={15} />
                    ) : (
                      <UserPlus size={15} />
                    )}{" "}
                    {busy === person.id
                      ? "Guardando…"
                      : following
                        ? "Dejar de seguir"
                        : "Seguir"}
                  </button>
                </div>
              );
            })}
          </section>
          <Pagination
            page={search ? searchPage : page}
            count={resource.data?.count || 0}
            onChange={search ? setSearchPage : setPage}
          />
        </>
      ) : (
        <Empty
          title={
            search
              ? "No encontramos ese perfil"
              : "Tu próxima compañía de viaje"
          }
          text={
            search
              ? "Probá con otro nombre. Solo se muestran perfiles públicos."
              : "Buscá a tus amigos por su nombre de usuario y sumalos a tu círculo."
          }
        />
      )}
      <p className="caption mt-5">
        Seguir es una relación directa: tu ranking de amigos incluye a las
        personas que seguís y a vos.
      </p>
    </>
  );
}
