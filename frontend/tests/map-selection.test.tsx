import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Route } from "@/lib/types";
import { MapView } from "@/components/map-view";
import { RouteDetailScreen } from "@/components/catalog-screens";

const state = vi.hoisted(() => ({
  route: {} as Route,
  sources: {} as Record<string, { data: { features: { id: number }[] } }>,
  handlers: {} as Record<string, (event: unknown) => void>,
  featureState: vi.fn(), easeTo: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "1" }) }));
vi.mock("next/dynamic", async () => {
  const component = await import("@/components/map-view");
  return { default: () => component.MapView };
});
vi.mock("@/components/providers", () => ({ useApp: () => ({ resolvedTheme: "light" }) }));
vi.mock("@/lib/use-resource", () => ({ useResource: (path: string) => ({
  data: path.startsWith("recorridos/") ? state.route : { muestra: false }, loading: false,
}) }));
vi.mock("maplibre-gl", () => ({
  setWorkerUrl: vi.fn(),
  NavigationControl: class {}, ScaleControl: class {},
  LngLatBounds: class { extend() { return this; } isEmpty() { return false; } },
  Popup: class { setLngLat() { return this; } setText() { return this; } addTo() { return this; } },
  Map: class {
    on(event: string, layer: string | ((event?: unknown) => void), callback?: (event: unknown) => void) {
      if (typeof layer === "function") {
        if (["style.load", "render"].includes(event)) queueMicrotask(() => layer());
      } else if (callback) state.handlers[`${event}:${layer}`] = callback;
      return this;
    }
    off() {} addControl() {} addLayer() {} fitBounds() {} remove() {} removeFeatureState() {}
    addSource(name: string, source: typeof state.sources[string]) { state.sources[name] = Object.assign(source, { setData: vi.fn() }); }
    getSource(name: string) { return state.sources[name]; }
    queryRenderedFeatures() { return [{}]; }
    setFeatureState = state.featureState;
    easeTo = state.easeTo;
    getZoom() { return 11; }
    setPaintProperty() {}
  },
}));

beforeEach(() => {
  state.sources = {};
  state.handlers = {};
  state.featureState.mockClear();
  state.easeTo.mockClear();
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => ({}) }));
  Element.prototype.scrollIntoView = vi.fn();
  state.route = {
    id: 1, linea: 1, linea_numero: "60", ramal: 1, ramal_nombre: "A", sentido: "IDA",
    desde: "Cabecera", hasta: "Destino", estado_datos: "disponible", puede_registrar_viaje: true,
    geometria: { type: "MultiLineString", coordinates: [[[-58.4,-34.6],[-58.41,-34.6]]] },
    paradas: [3,1,2].map((id) => ({ id, orden: id, transitada: id === 1,
      parada: { id: id + 90, is_official: true, nombre: `Parada ${id}`,
        direccion: "", barrio: "", coordenadas: [-58.4 + id / 1000, -34.6] },
    })),
  } as Route;
});

describe("mapa y secuencia oficial", () => {
  it("usa occurrence IDs y orden para dibujar puntos y selección inclusiva", async () => {
    render(<MapView routes={[state.route]} selectedOccurrenceId={2} startOccurrenceId={1} endOccurrenceId={3} />);
    await waitFor(() => expect(state.sources.stops?.data.features.map((item) => item.id)).toEqual([1,2,3]));
    await waitFor(() => expect(state.featureState).toHaveBeenCalledWith({ source: "stops", id: 2 }, {
      selected: true, start: false, end: false, in_segment: true,
    }));
    expect(state.easeTo).toHaveBeenCalledWith(expect.objectContaining({ center: state.route.paradas[2].parada.coordenadas }));
  });

  it("sincroniza lista y mapa, conserva el orden y prepara IDs para el alta", async () => {
    render(<RouteDetailScreen />);
    await waitFor(() => expect(state.handlers["click:stop-points"]).toBeDefined());
    const buttons = screen.getAllByRole("button", { name: /Seleccionar parada/ });
    expect(buttons.map((button) => button.textContent)).toEqual(["Parada 1","Parada 2","Parada 3"]);
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(state.featureState).toHaveBeenCalledWith({ source: "stops", id: 1 }, expect.objectContaining({ selected: true })));
    fireEvent.click(screen.getByRole("button", { name: "Usar como subida" }));
    await act(async () => state.handlers["click:stop-points"]({
      features: [{ properties: { occurrence: 3, label: "Parada 3", status: "Oficial" } }], lngLat: {},
    }));
    expect(buttons[2]).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Usar como bajada" }));
    expect(screen.getByText(/Tramo seleccionado: 3 paradas oficiales/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Registrar viaje" })).toHaveAttribute("href", "/viajes/nuevo?linea=1&recorrido=1&inicio=1&fin=3");
  });
});
