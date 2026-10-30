import type { Route } from "./types";

export function officialStops(route: Route | undefined) {
  return route?.paradas.filter((item) => item.parada.is_official) || [];
}

export function canRegisterTrip(route: Route | undefined) {
  return Boolean(
    route?.puede_registrar_viaje &&
      route.geometria &&
      officialStops(route).length >= 2,
  );
}

export function routeDataMessage(route: Route) {
  if (!route.geometria)
    return "Trazado aún no disponible. Estamos incorporando los datos de este recorrido.";
  if (!officialStops(route).length)
    return "Paradas aún no disponibles. El registro se habilita cuando haya una secuencia de paradas oficiales.";
  return "Recorrido parcial. Todavía no hay suficientes paradas oficiales para registrar un viaje.";
}
