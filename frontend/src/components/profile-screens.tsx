"use client";
import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Award, Settings, LogOut, Check } from "lucide-react";
import { useApp } from "./providers";
import { api, mutate } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { Profile } from "@/lib/types";
import {
  Gate,
  Heading,
  Loading,
  ErrorState,
  Avatar,
  Metrics,
  ProgressBar,
  number,
  ThemeToggle,
  Success,
  LineBadge,
  Empty,
} from "./ui";

export function MyProfileScreen() {
  return (
    <Gate>
      <MyProfile />
    </Gate>
  );
}
function MyProfile() {
  const { user } = useApp();
  return user ? <ProfileContent profile={user} mine /> : null;
}
export function PublicProfileScreen() {
  const { username } = useParams<{ username: string }>();
  const { user } = useApp();
  const profile = useResource<Profile>(
    `perfiles/${encodeURIComponent(username)}/`,
  );
  if (profile.loading) return <Loading />;
  if (profile.error || !profile.data)
    return (
      <ErrorState
        message={profile.error || "Este perfil no está disponible."}
        retry={profile.reload}
      />
    );
  return (
    <ProfileContent
      profile={profile.data}
      mine={profile.data.id === user?.id}
    />
  );
}
function ProfileContent({
  profile: p,
  mine = false,
}: {
  profile: Profile;
  mine?: boolean;
}) {
  const next = p.nivel.siguiente;
  const progress = next
    ? (100 * (p.puntos - p.nivel.puntos_minimos)) /
      (next.puntos_minimos - p.nivel.puntos_minimos)
    : 100;
  return (
    <>
      <header className="profile-header">
        <Avatar user={p} large />
        <div>
          <span className="eyebrow mb-0">UNA HISTORIA SOBRE RUEDAS</span>
          <h1>{p.nickname}</h1>
          <p className="text-sm">@{p.username}</p>
        </div>
        {mine && (
          <Link className="button secondary" href="/configuracion">
            <Settings size={16} /> Editar perfil
          </Link>
        )}
      </header>
      <Metrics
        stops={p.paradas}
        lines={p.lineas_recorridas}
        branches={p.ramales_completos}
        points={p.puntos}
      />
      <div className="split-grid">
        <section>
          <div className="level-panel">
            <span
              className="eyebrow"
              style={{ color: "inherit", opacity: 0.7 }}
            >
              NIVEL {p.nivel.numero}
            </span>
            <h2>{p.nivel.nombre}</h2>
            <p>
              {next
                ? `Faltan ${number(next.puntos_minimos - p.puntos)} puntos para el nivel ${next.numero}.`
                : "Llegaste al nivel máximo. La colección sigue creciendo."}
            </p>
            <ProgressBar
              value={progress}
              label={`${number(p.puntos)}${next ? ` / ${number(next.puntos_minimos)}` : ""} puntos`}
            />
          </div>
          <div className="section-head">
            <h2>Líneas en su historia</h2>
          </div>
          {p.lineas.length ? (
            <section className="panel">
              {p.lineas.slice(0, 6).map((line) => (
                <Link
                  href={`/lineas/${line.linea}`}
                  key={line.linea}
                  className="goal-card"
                >
                  <LineBadge numero={line.numero} small />
                  <div>
                    <h3>
                      Línea {line.numero}
                      {line.completo ? " · Completada" : ""}
                    </h3>
                    <p>
                      {line.transitadas} de {line.total} paradas
                    </p>
                    <ProgressBar value={line.porcentaje} />
                  </div>
                  <ArrowRight size={16} />
                </Link>
              ))}
            </section>
          ) : (
            <Empty
              title="La colección está por empezar"
              text="Los primeros recorridos van a aparecer acá."
              href={mine ? "/viajes/nuevo" : undefined}
              cta="Registrar viaje"
            />
          )}
        </section>
        <section>
          <div className="section-head mt-5">
            <h2>Su lugar en el AMBA</h2>
          </div>
          <div className="profile-ranks">
            <div>
              <b>{p.ranking_global ? `#${p.ranking_global}` : "—"}</b>
              <span>Global</span>
            </div>
            <div>
              <b>{p.ranking_semanal ? `#${p.ranking_semanal}` : "—"}</b>
              <span>Semanal</span>
            </div>
            <div>
              <b>{number(p.lineas_completas)}</b>
              <span>Líneas completas</span>
            </div>
          </div>
          <div className="section-head">
            <h2>Insignias de viaje</h2>
            {mine && (
              <Link className="text-link" href="/logros">
                Ver todas <ArrowRight size={14} />
              </Link>
            )}
          </div>
          <section className="panel">
            {p.logros.length ? (
              p.logros.slice(0, 6).map((a) => (
                <div className="goal-card" key={a.logro__slug}>
                  <span
                    className="achievement-icon"
                    style={{
                      background: "var(--brand-accent)",
                      color: "var(--on-accent)",
                    }}
                  >
                    <Award size={24} />
                  </span>
                  <div>
                    <h3>{a.logro__nombre}</h3>
                    <p>{a.logro__descripcion}</p>
                  </div>
                  <Check size={16} />
                </div>
              ))
            ) : (
              <p className="empty-inline">
                Cada nueva parada te acerca a la primera insignia.
              </p>
            )}
          </section>
        </section>
      </div>
    </>
  );
}

export function SettingsScreen() {
  const { user, loading, error, refresh } = useApp();
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} retry={() => void refresh()} />;
  return (
    <>
      <Heading
        eyebrow="A TU MANERA"
        title="Configuración"
        text="Elegí cómo querés vivir tu próxima parada."
      />
      {user ? (
        <ProfileSettings profile={user} />
      ) : (
        <section className="panel max-w-2xl">
          <h2 className="mb-5">Apariencia</h2>
          <ThemeToggle />
          <p className="caption mt-5">
            La opción Sistema sigue la apariencia de tu dispositivo.
          </p>
          <Link href="/login" className="button mt-6">
            Iniciar sesión para editar mi perfil
          </Link>
        </section>
      )}
    </>
  );
}
function ProfileSettings({ profile }: { profile: Profile }) {
  const { theme, refresh } = useApp();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess(false);
    const form = new FormData(event.currentTarget);
    try {
      await mutate(
        "me/",
        {
          nickname: form.get("nickname"),
          avatar: form.get("avatar"),
          public_profile: form.get("public_profile") === "on",
          theme,
        },
        "PATCH",
      );
      await refresh();
      setSuccess(true);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No pudimos guardar los cambios.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function signOut() {
    setBusy(true);
    setError("");
    try {
      await api("auth/logout/", { method: "POST" });
      await refresh();
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cerrar la sesión.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="max-w-2xl">
      <form className="panel" onSubmit={save}>
        <section className="settings-section">
          <h2>Tu perfil</h2>
          <p>Así te ven las demás personas de la comunidad.</p>
          <div className="form-stack">
            <label className="field">
              Nombre visible
              <input
                name="nickname"
                required
                maxLength={60}
                autoComplete="nickname"
                defaultValue={profile.nickname}
              />
            </label>
            <label className="field">
              Avatar{" "}
              <span className="muted caption">
                Opcional · enlace HTTPS a una imagen
              </span>
              <input
                type="url"
                name="avatar"
                maxLength={200}
                defaultValue={profile.avatar}
                placeholder="https://…"
              />
            </label>
            <label className="field">
              Email
              <input value={profile.email || ""} readOnly type="email" />
              <small>
                Tu email es privado y se usa para recuperar tu cuenta.
              </small>
            </label>
          </div>
        </section>
        <section className="settings-section">
          <h2>Privacidad</h2>
          <p>Tu historial detallado siempre es privado.</p>
          <label className="checkbox-field">
            <input
              type="checkbox"
              name="public_profile"
              defaultChecked={profile.public_profile}
            />
            <span>
              Mostrar mi perfil en la comunidad
              <small>
                Permite que otras personas vean tus métricas, te sigan y te
                encuentren en los rankings. Si lo desactivás, salís de búsquedas
                y rankings públicos.
              </small>
            </span>
          </label>
        </section>
        <section className="settings-section">
          <h2>Apariencia</h2>
          <p>El modo Sistema se adapta a tu dispositivo.</p>
          <ThemeToggle />
        </section>
        {error && (
          <p role="alert" className="form-error mb-5">
            {error}
          </p>
        )}
        {success && (
          <Success>Cambios guardados. Tu perfil está al día.</Success>
        )}
        <button className="button" disabled={busy}>
          {busy ? "Guardando…" : "Guardar cambios"}
          <Check size={16} />
        </button>
      </form>
      <div className="flex items-center justify-between gap-4 mt-6">
        <Link className="text-link" href="/recuperar">
          Cambiar mi contraseña <ArrowRight size={15} />
        </Link>
        <button
          className="button secondary"
          disabled={busy}
          onClick={() => void signOut()}
        >
          <LogOut size={16} /> Cerrar sesión
        </button>
      </div>
    </div>
  );
}
