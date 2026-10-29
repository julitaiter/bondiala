"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type { Profile, Theme } from "@/lib/types";

type Context = {
  user: Profile | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
};
const AppContext = createContext<Context | null>(null);
function readTheme(): Theme {
  const value = localStorage.getItem("bondiala-theme");
  return value === "dark" || value === "light" ? value : "system";
}
function themeSubscription(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("bondiala-theme", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("bondiala-theme", callback);
  };
}
function schemeSubscription(callback: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
export function Providers({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const theme = useSyncExternalStore(
    themeSubscription,
    readTheme,
    () => "system" as Theme,
  );
  const systemDark = useSyncExternalStore(
    schemeSubscription,
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
    () => false,
  );
  const resolvedTheme =
    theme === "system" ? (systemDark ? "dark" : "light") : theme;
  const setTheme = useCallback((value: Theme) => {
    localStorage.setItem("bondiala-theme", value);
    window.dispatchEvent(new Event("bondiala-theme"));
  }, []);
  const receiveSession = useCallback(
    (result: { user: Profile | null }) => {
      setUser(result.user);
      setError("");
      if (result.user?.theme) setTheme(result.user.theme);
      setLoading(false);
    },
    [setTheme],
  );
  const failSession = useCallback((e: unknown) => {
    setError(e instanceof Error ? e.message : "No se pudo conectar.");
    setLoading(false);
  }, []);
  const refresh = useCallback(async () => {
    await api<{ user: Profile | null }>("me/")
      .then(receiveSession)
      .catch(failSession);
  }, [receiveSession, failSession]);
  useEffect(() => {
    void api<{ user: Profile | null }>("me/")
      .then(receiveSession)
      .catch(failSession);
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production")
      navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, [receiveSession, failSession]);
  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);
  return (
    <AppContext.Provider
      value={{ user, loading, error, refresh, theme, resolvedTheme, setTheme }}
    >
      {children}
    </AppContext.Provider>
  );
}
export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("App provider missing");
  return context;
}
