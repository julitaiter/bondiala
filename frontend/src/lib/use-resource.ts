"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "./api";

export function useResource<T>(path: string | null) {
  const [state, setState] = useState<{
    data: T | null;
    error: string;
    path: string | null;
    version: number;
  }>({ data: null, error: "", path: null, version: -1 });
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ data, error: "", path, version });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ data: null, error: error.message, path, version });
      });
    return () => controller.abort();
  }, [path, version]);
  const current = state.path === path && state.version === version;
  return {
    data: current ? state.data : null,
    error: current ? state.error : "",
    loading: Boolean(path) && !current,
    reload,
  };
}
