import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Route } from "@/lib/types";
import { TripScreen } from "@/components/trip-screen";

const state = vi.hoisted(() => ({ route: {} as Route, mutate: vi.fn() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("linea=1&recorrido=1"),
}));
vi.mock("@/components/providers", () => ({
  useApp: () => ({ user: { id: 1 }, loading: false, refresh: vi.fn() }),
}));
vi.mock("@/lib/api", () => ({ mutate: state.mutate }));
vi.mock("@/lib/use-resource", () => ({
  useResource: (path: string | null) => ({
    data: path?.endsWith("/recorridos/")
      ? [state.route]
      : path?.startsWith("lineas/?")
        ? { results: [{ id: 1, numero: "60" }] }
        : path === "lineas/1/"
          ? { id: 1, numero: "60" }
          : { muestra: false },
    loading: false,
  }),
}));

beforeEach(() => {
  state.mutate.mockReset();
  state.route = {
    id: 1,
    linea: 1,
    linea_numero: "60",
    ramal: 1,
    ramal_nombre: "A",
    sentido: "IDA",
    geometria: {
      type: "MultiLineString",
      coordinates: [[[-58.4, -34.6], [-58.401, -34.6]]],
    },
    puede_registrar_viaje: true,
    paradas: [1, 2, 3].map((id) => ({
      id,
      orden: id,
      transitada: false,
      parada: {
        id,
        nombre: `Parada ${id}`,
        direccion: "",
        barrio: "",
        coordenadas: [-58.4, -34.6],
        is_official: true,
      },
    })),
  } as Route;
});

describe("registro con paradas oficiales", () => {
  it("impide usar paradas ilustrativas aunque llegue un flag de disponibilidad obsoleto", () => {
    state.route.paradas.forEach((item) => { item.parada.is_official = false; });
    render(<TripScreen />);
    expect(screen.getByRole("combobox", { name: "¿Dónde subiste?" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Revisar viaje" })).toBeDisabled();
    expect(screen.getByText(/Paradas aún no disponibles/)).toBeVisible();
    expect(screen.queryByRole("option", { name: /Parada 1/ })).not.toBeInTheDocument();
    expect(state.mutate).not.toHaveBeenCalled();
  });

  it("exige trazado y al menos dos paradas oficiales", () => {
    state.route.geometria = null;
    render(<TripScreen />);
    expect(screen.getByRole("combobox", { name: "¿Dónde subiste?" })).toBeDisabled();
    expect(screen.getByText(/Trazado aún no disponible/)).toBeVisible();
  });

  it("muestra un recorrido parcial cuando sólo tiene una parada oficial", () => {
    state.route.paradas = state.route.paradas.slice(0, 1);
    render(<TripScreen />);
    expect(screen.getByRole("button", { name: "Revisar viaje" })).toBeDisabled();
    expect(screen.getByText(/Recorrido parcial/)).toBeVisible();
  });

  it("habilita selección únicamente para la secuencia oficial disponible", () => {
    render(<TripScreen />);
    expect(screen.getByRole("combobox", { name: "¿Dónde subiste?" })).toBeEnabled();
    expect(screen.getByRole("option", { name: "1. Parada 1" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Revisar viaje" })).toBeDisabled();
  });
});
