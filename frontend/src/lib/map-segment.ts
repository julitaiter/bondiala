import type { MultiLineString, Position } from "geojson";
import type { Route } from "./types";
import { officialStops } from "./route-data";

type Projection = { component: number; edge: number; point: Position; along: number; distance: number };

function project(geometry: MultiLineString, point: Position): Projection | null {
  // Aproximación local para dibujar, sin intervenir en asociaciones ni progreso.
  const scale = Math.cos(point[1] * Math.PI / 180);
  const meters = 111320;
  const candidates: Projection[] = [];
  let along = 0;
  geometry.coordinates.forEach((part, component) => {
    for (let edge = 0; edge < part.length - 1; edge++) {
      const a = part[edge], b = part[edge + 1];
      const dx = (b[0] - a[0]) * scale, dy = b[1] - a[1];
      const lengthSquared = dx * dx + dy * dy;
      if (!lengthSquared) continue;
      const t = Math.max(0, Math.min(1, (((point[0] - a[0]) * scale * dx) + (point[1] - a[1]) * dy) / lengthSquared));
      const projected = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
      const length = Math.sqrt(lengthSquared) * meters;
      candidates.push({ component, edge, point: projected, along: along + t * length,
        distance: Math.hypot((point[0] - projected[0]) * scale, point[1] - projected[1]) * meters });
      along += length;
    }
  });
  candidates.sort((a, b) => a.distance - b.distance);
  const nearest = candidates[0];
  if (!nearest || candidates.some((candidate) => candidate.distance <= nearest.distance + 1 && Math.abs(candidate.along - nearest.along) > 10)) return null;
  return nearest;
}

export function selectedGeometry(route: Route, startId?: number, endId?: number): MultiLineString | null {
  const stops = officialStops(route);
  const start = stops.find((stop) => stop.id === startId), end = stops.find((stop) => stop.id === endId);
  if (!route.geometria || !start || !end || start.orden >= end.orden) return null;
  const from = project(route.geometria, start.parada.coordenadas), to = project(route.geometria, end.parada.coordenadas);
  if (!from || !to || from.along >= to.along) return null;
  const coordinates: Position[][] = [];
  for (let component = from.component; component <= to.component; component++) {
    const part = route.geometria.coordinates[component];
    const first = component === from.component ? from.edge + 1 : 0;
    const last = component === to.component ? to.edge + 1 : part.length;
    const points = [
      ...(component === from.component ? [from.point] : []),
      ...part.slice(first, last),
      ...(component === to.component ? [to.point] : []),
    ];
    if (points.length >= 2) coordinates.push(points);
  }
  return coordinates.length ? { type: "MultiLineString", coordinates } : null;
}
