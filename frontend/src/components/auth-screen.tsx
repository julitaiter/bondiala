"use client";
import { useState, type FormEvent, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { mutate } from "@/lib/api";
import { useApp } from "./providers";
import { Loading, Success } from "./ui";

type Mode = "login" | "registro" | "recuperar" | "restablecer";
export function AuthScreen({ mode }: { mode: Mode }) {
  return (
    <Suspense fallback={<Loading />}>
      <AuthForm mode={mode} />
    </Suspense>
  );
}
function AuthForm({ mode }: { mode: Mode }) {
  const { refresh } = useApp();
  const router = useRouter();
  const query = useSearchParams();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const titles = {
    login: "Volvé a tu colección",
    registro: "Tu primer viaje empieza acá",
    recuperar: "Recuperá tu cuenta",
    restablecer: "Elegí una nueva contraseña",
  };
  const subtitles = {
    login: "La ciudad sigue ahí afuera. Tus recorridos también.",
    registro: "Creá tu cuenta y empezá a coleccionar el AMBA.",
    recuperar: "Te vamos a enviar un enlace para volver a bondiar.",
    restablecer: "Usá una contraseña de al menos 10 caracteres.",
  };
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const payload =
        mode === "restablecer"
          ? { ...data, uid: query.get("uid"), token: query.get("token") }
          : data;
      const result = await mutate<{ detail?: string }>(
        `auth/${mode}/`,
        payload,
      );
      if (mode === "recuperar" || mode === "restablecer")
        setSuccess(result.detail || "Listo. Revisá tu email.");
      else {
        await refresh();
        const next = query.get("next");
        router.push(
          next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard",
        );
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-container">
      <span className="eyebrow">EL AMBA, LÍNEA POR LÍNEA</span>
      <h1>{titles[mode]}</h1>
      <p>{subtitles[mode]}</p>
      <section className="panel">
        {success ? (
          <>
            <Success>{success}</Success>
            <Link className="button full mt-5" href="/login">
              Ir a iniciar sesión <ArrowRight size={16} />
            </Link>
          </>
        ) : (
          <form onSubmit={submit} className="form-stack">
            {mode === "registro" && (
              <>
                <label className="field">
                  Nombre de usuario
                  <input
                    required
                    name="username"
                    aria-label="Nombre de usuario"
                    autoComplete="username"
                    minLength={3}
                    maxLength={30}
                    pattern="[A-Za-z0-9_]+"
                    placeholder="como_te_conocen"
                  />
                  <small>
                    Letras, números y guion bajo. Lo vas a usar en tu perfil.
                  </small>
                </label>
                <label className="field">
                  ¿Cómo te llamamos?
                  <input
                    required
                    name="nickname"
                    autoComplete="nickname"
                    maxLength={60}
                    placeholder="Tu nombre o apodo"
                  />
                </label>
              </>
            )}
            {mode === "login" ? (
              <label className="field">
                Email o usuario
                <input
                  name="identifier"
                  required
                  autoComplete="username"
                  maxLength={254}
                  placeholder="Tu email o nombre de usuario"
                />
              </label>
            ) : (
              mode !== "restablecer" && (
                <label className="field">
                  Email
                  <input
                    name="email"
                    required
                    type="email"
                    autoComplete="email"
                    maxLength={254}
                    placeholder="vos@ejemplo.com"
                  />
                </label>
              )
            )}
            {mode !== "recuperar" && (
              <label className="field">
                Contraseña
                <input
                  name="password"
                  aria-label="Contraseña"
                  required
                  type="password"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  minLength={mode === "login" ? 1 : 10}
                  maxLength={128}
                  placeholder={
                    mode === "login"
                      ? "Tu contraseña"
                      : "Al menos 10 caracteres"
                  }
                />
                {mode !== "login" && (
                  <small>
                    Combiná palabras, números y símbolos. Evitá datos
                    personales.
                  </small>
                )}
              </label>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button full" disabled={busy}>
              {busy
                ? "Un momento…"
                : mode === "login"
                  ? "Iniciar sesión"
                  : mode === "registro"
                    ? "Crear mi colección"
                    : mode === "recuperar"
                      ? "Enviar enlace"
                      : "Guardar contraseña"}
              <ArrowRight size={16} />
            </button>
            {mode === "registro" && (
              <p className="caption">
                Tu historial de viajes es privado. Podés elegir la visibilidad
                de tu perfil en Configuración.{" "}
                <Link className="text-link" href="/privacidad">
                  Conocé cómo cuidamos tus datos.
                </Link>
              </p>
            )}
          </form>
        )}
        <div className="auth-meta">
          {mode === "login" ? (
            <>
              <Link href="/recuperar">Olvidé mi contraseña</Link>
              <Link href="/registro">Crear cuenta</Link>
            </>
          ) : (
            <Link href="/login">Ya tengo una cuenta</Link>
          )}
        </div>
      </section>
    </div>
  );
}
