import type { Route } from "./types";

export function officialStops(route: Route | undefined) {
  return route?.paradas.filter((item) => item.parada.is_official).sort((a, b) => a.orden - b.orden) || [];
}

export function canRegisterTrip(route: Route | undefined) {
  return Boolean(
    route?.puede_registrar_viaje &&
      !route.requiere_rematch && route.estado_datos !== "ambiguo" &&
      route.geometria &&
      officialStops(route).length >= 2,
  );
}

export function routeDataMessage(route: Route) {
  if (!route.geometria)
    return "Trazado aún no disponible. Estamos incorporando los datos de este recorrido.";
  if (route.estado_datos === "ambiguo")
    return "La secuencia de este recorrido está en revisión. El registro se habilita cuando sus paradas puedan ordenarse con seguridad.";
  if (route.requiere_rematch)
    return "Recorrido parcial. Estamos actualizando el orden de las paradas sobre el nuevo trazado.";
  if (route.estado_datos === "parcial" && canRegisterTrip(route))
    return "Recorrido parcial. Podés registrar el tramo entre las paradas oficiales disponibles.";
  if (!officialStops(route).length)
    return "Paradas aún no disponibles. El registro se habilita cuando haya una secuencia de paradas oficiales.";
  return "Recorrido parcial. Todavía no hay suficientes paradas oficiales para registrar un viaje.";
}
