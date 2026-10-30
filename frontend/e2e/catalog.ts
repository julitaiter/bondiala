import type { APIRequestContext } from "@playwright/test";
import type { Page, Route } from "../src/lib/types";

export async function officialTestRoute(request: APIRequestContext): Promise<Route> {
  let endpoint: string | null = "/api/v1/recorridos/";
  while (endpoint) {
    const response = await request.get(endpoint);
    if (!response.ok()) throw new Error(`Catálogo de prueba: HTTP ${response.status()}`);
    const catalogue: Page<Route> = await response.json();
    const route = catalogue.results.find((item) =>
      item.puede_registrar_viaje && item.geometria && item.paradas.length >= 3 &&
      item.paradas.every((stop) => stop.parada.is_official),
    );
    if (route) return route;
    endpoint = catalogue.next ? new URL(catalogue.next).pathname + new URL(catalogue.next).search : null;
  }
  throw new Error(
    "Falta un recorrido con al menos tres paradas oficiales. Importá el fixture oficial verificado y ejecutá --match-routes antes de E2E.",
  );
}
