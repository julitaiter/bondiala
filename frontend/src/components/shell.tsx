"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Bus,
  Map,
  Trophy,
  Award,
  Users,
  Settings,
  ArrowUpRight,
  Plus,
  Menu,
  X,
  BookOpen,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { useApp } from "./providers";
import { Avatar } from "./ui";

const navigation = [
  ["/dashboard", "Mi colección", Home],
  ["/lineas", "Explorar líneas", Bus],
  ["/mapa", "El mapa", Map],
  ["/ranking", "Rankings", Trophy],
  ["/logros", "Logros", Award],
  ["/amigos", "Amigos", Users],
] as const;
export function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { user } = useApp();
  const [menu, setMenu] = useState(false);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <aside className={`sidebar ${menu ? "is-open" : ""}`}>
        <Link
          href="/"
          className="brand"
          onClick={() => setMenu(false)}
          aria-label="Bondiala, inicio"
        >
          <img
            className="asset-light"
            src="/assets/light/wordmark_bondiala.png"
            alt="Bondiala"
          />
          <img
            className="asset-dark"
            src="/assets/dark/wordmark_bondiala_dark.png"
            alt="Bondiala"
          />
        </Link>
        <span className="sidebar-caption">EL AMBA, LÍNEA POR LÍNEA</span>
        <nav aria-label="Navegación principal">
          {navigation.map(([href, label, Icon]) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMenu(false)}
              className={`nav-item ${path.startsWith(href) ? "active" : ""}`}
              aria-current={path.startsWith(href) ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{label}</span>
              {path.startsWith(href) && <i />}
            </Link>
          ))}
        </nav>
        <Link
          className="button sidebar-cta"
          href={user ? "/viajes/nuevo" : "/registro"}
          onClick={() => setMenu(false)}
        >
          <Plus size={19} />
          {user ? "Registrar viaje" : "Empezá tu colección"}
        </Link>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <BookOpen size={20} />
            <p>
              Cada viaje cuenta.
              <br />
              <b>Hacelo parte de tu historia.</b>
            </p>
            <span className="mini-route">
              <i />
              <i />
              <i />
            </span>
          </div>
          <Link
            href="/configuracion"
            className="nav-item"
            onClick={() => setMenu(false)}
          >
            <Settings size={18} /> Configuración
          </Link>
          {user ? (
            <Link
              href="/perfil"
              className="user-card"
              onClick={() => setMenu(false)}
            >
              <Avatar user={user} />
              <span>
                <b>{user.nickname}</b>
                <small>
                  Nivel {user.nivel.numero} · {user.nivel.nombre}
                </small>
              </span>
              <ArrowUpRight size={16} />
            </Link>
          ) : (
            <Link
              className="login-link"
              href="/login"
              onClick={() => setMenu(false)}
            >
              Ya tengo una cuenta <ArrowRightSmall />
            </Link>
          )}
        </div>
      </aside>
      {menu && (
        <button
          className="menu-backdrop"
          aria-label="Cerrar navegación"
          onClick={() => setMenu(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label={menu ? "Cerrar menú" : "Abrir menú"}
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X size={22} /> : <Menu size={22} />}
          </button>
          <span className="topbar-label">
            <span className="status-dot" /> Explorando Buenos Aires
          </span>
          <div>
            {user ? (
              <>
                <Link className="topbar-profile" href="/perfil">
                  <span>{user.nickname}</span>
                  <Avatar user={user} />
                </Link>
                <Link
                  href="/viajes/nuevo"
                  className="icon-button mobile-add"
                  aria-label="Registrar viaje"
                >
                  <Plus size={21} />
                </Link>
              </>
            ) : (
              <Link href="/login" className="text-link">
                Iniciar sesión <ArrowUpRight size={15} />
              </Link>
            )}
          </div>
        </header>
        <main id="contenido">{children}</main>
        <footer className="footer">
          <span>Bondiala · Recorré. Completá. Coleccioná.</span>
          <Link href="/privacidad">Privacidad</Link>
          <span>Hecho para quienes miran por la ventanilla.</span>
        </footer>
      </div>
      <nav className="bottom-nav" aria-label="Navegación móvil">
        {navigation.slice(0, 4).map(([href, label, Icon]) => (
          <Link
            key={href}
            href={href}
            aria-current={path.startsWith(href) ? "page" : undefined}
          >
            <Icon size={21} />
            <span>
              {label === "Explorar líneas"
                ? "Líneas"
                : label === "Mi colección"
                  ? "Colección"
                  : label}
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
function ArrowRightSmall() {
  return <ArrowUpRight size={16} />;
}
