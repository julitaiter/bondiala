"use client";
import Link from "next/link";
import {
  ArrowRight,
  AlertCircle,
  RotateCw,
  MapPin,
  Bus,
  Trophy,
  Route as RouteIcon,
  Check,
  Sun,
  Moon,
  Monitor,
  Plus,
  LockKeyhole,
} from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import type { Line, Palette, PublicUser } from "@/lib/types";
import { useApp } from "./providers";

export const number = (value: number) =>
  new Intl.NumberFormat("es-AR").format(value);
export function LineBadge({
  numero,
  colores,
  small = false,
}: {
  numero: string;
  colores?: Palette | null;
  small?: boolean;
}) {
  const style = colores
    ? ({
        "--line-main": colores.color_principal,
        "--line-one": colores.color_secundario_1,
        "--line-two": colores.color_secundario_2,
        "--line-text": colores.color_texto,
      } as CSSProperties)
    : undefined;
  return (
    <span
      className={`line-badge ${small ? "small" : ""}`}
      data-code-length={numero.length}
      style={style}
      aria-label={`Línea ${numero}`}
    >
      <span className="badge-stripes">
        <i />
        <i />
      </span>
      <b>{numero}</b>
    </span>
  );
}
export function ProgressBar({
  value,
  label,
}: {
  value: number;
  label?: string;
}) {
  return (
    <div className="progress-wrap">
      {label && (
        <div className="progress-label">
          <span>{label}</span>
          <b>{Math.round(value)}%</b>
        </div>
      )}
      <div
        className="progress-track"
        role="progressbar"
        aria-label={label || "Progreso"}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}
export function LineCard({ line }: { line: Line }) {
  const { user } = useApp();
  return (
    <Link href={`/lineas/${line.id}`} className="line-card">
      <div className="flex items-start justify-between gap-3">
        <LineBadge numero={line.numero} colores={line.colores} />
        <ArrowRight size={19} className="muted" />
      </div>
      <h3>{line.nombre || `Línea ${line.numero}`}</h3>
      <p>
        {line.ramales_count}{" "}
        {line.ramales_count === 1
          ? "ramal para descubrir"
          : "ramales para descubrir"}
      </p>
      {user && line.progreso.total > 0 ? (
        <ProgressBar
          value={line.progreso.porcentaje}
          label={
            line.progreso.completo
              ? "Línea completada"
              : `${line.progreso.transitadas} de ${line.progreso.total} paradas`
          }
        />
      ) : (
        <span className="card-foot">
          {line.progreso.total
            ? "Conocé el recorrido"
            : "Paradas por incorporar"}{" "}
          <ArrowRight size={14} />
        </span>
      )}
    </Link>
  );
}
export function Avatar({
  user,
  large = false,
}: {
  user: Pick<PublicUser, "nickname" | "avatar">;
  large?: boolean;
}) {
  return (
    <span className={`avatar ${large ? "large" : ""}`}>
      {user.avatar ? (
        <img src={user.avatar} referrerPolicy="no-referrer" alt="" />
      ) : (
        user.nickname.slice(0, 2).toUpperCase()
      )}
    </span>
  );
}
export function Heading({
  eyebrow,
  title,
  text,
  action,
}: {
  eyebrow?: string;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {text && <p>{text}</p>}
      </div>
      {action}
    </header>
  );
}
export function Loading({
  label = "Cargando tu próxima parada…",
}: {
  label?: string;
}) {
  return (
    <div className="state" role="status">
      <span className="route-loader">
        <i />
        <i />
        <i />
      </span>
      <p>{label}</p>
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="state error-state" role="alert">
      <AlertCircle size={28} />
      <h3>No pudimos llegar a esta parada</h3>
      <p>{message}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          <RotateCw size={16} /> Intentar de nuevo
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  text,
  href,
  cta,
}: {
  title: string;
  text: string;
  href?: string;
  cta?: string;
}) {
  return (
    <div className="state">
      <MapPin size={32} className="muted" />
      <h3>{title}</h3>
      <p>{text}</p>
      {href && (
        <Link className="button" href={href}>
          {cta || "Explorar líneas"}
          <ArrowRight size={17} />
        </Link>
      )}
    </div>
  );
}
export function Gate({ children }: { children: ReactNode }) {
  const { user, loading, error, refresh } = useApp();
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} retry={() => void refresh()} />;
  if (!user)
    return (
      <Empty
        title="Tu colección te espera"
        text="Creá una cuenta o iniciá sesión para registrar tus viajes y ver tu progreso."
        href="/login"
        cta="Iniciar sesión"
      />
    );
  return <>{children}</>;
}
export function ThemeToggle() {
  const { theme, setTheme } = useApp();
  return (
    <div className="theme-switch" role="group" aria-label="Apariencia">
      {(
        [
          ["light", Sun, "Claro"],
          ["dark", Moon, "Oscuro"],
          ["system", Monitor, "Sistema"],
        ] as const
      ).map(([value, Icon, label]) => (
        <button
          type="button"
          key={value}
          aria-pressed={theme === value}
          onClick={() => setTheme(value)}
        >
          <Icon size={17} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
export function Metrics({
  stops,
  lines,
  branches,
  points,
}: {
  stops: number;
  lines: number;
  branches: number;
  points: number;
}) {
  return (
    <div className="metrics">
      {(
        [
          [MapPin, stops, "Paradas transitadas"],
          [Bus, lines, "Líneas recorridas"],
          [RouteIcon, branches, "Ramales completos"],
          [Trophy, points, "Puntos ganados"],
        ] as const
      ).map(([Icon, value, label]) => (
        <div className="metric" key={label}>
          <Icon size={20} />
          <strong>{number(value)}</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}
export function TripCTA() {
  return (
    <Link href="/viajes/nuevo" className="button">
      <Plus size={18} /> Registrar viaje
    </Link>
  );
}
export function Success({ children }: { children: ReactNode }) {
  return (
    <div className="notice success" role="status">
      <Check size={18} />
      <span>{children}</span>
    </div>
  );
}
export function PrivateNote() {
  return (
    <p className="caption inline-note">
      <LockKeyhole size={14} /> Tu historial de viajes es privado.
    </p>
  );
}
export function Pagination({
  page,
  count,
  onChange,
}: {
  page: number;
  count: number;
  onChange: (page: number) => void;
}) {
  if (count <= 24) return null;
  return (
    <nav className="pagination" aria-label="Paginación">
      <button
        className="button secondary"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        Anterior
      </button>
      <span>
        {page} / {Math.ceil(count / 24)}
      </span>
      <button
        className="button secondary"
        disabled={page * 24 >= count}
        onClick={() => onChange(page + 1)}
      >
        Siguiente
      </button>
    </nav>
  );
}
