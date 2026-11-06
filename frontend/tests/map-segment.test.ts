import { describe, expect, it } from "vitest";
import type { Route } from "@/lib/types";
import { selectedGeometry } from "@/lib/map-segment";

function route(parts: number[][][], from: [number, number], to: [number, number]) {
  return { geometria: { type: "MultiLineString", coordinates: parts }, paradas: [from, to].map((coordenadas, index) => ({
    id: index + 1, orden: index + 1, parada: { coordenadas, is_official: true },
  })) } as Route;
}
describe("tramo visual sobre la geometría existente", () => {
  it("conserva las curvas y los vértices del trazado sin unir paradas en recta", () => {
    const data = route([[[0,0],[0.01,0],[0.01,0.01]]], [0.005,0], [0.01,0.005]);
    const before = JSON.stringify(data);
    const geometry = selectedGeometry(data, 1, 2);
    expect(geometry?.coordinates[0]).toHaveLength(3);
    expect(geometry?.coordinates[0][1]).toEqual([0.01,0]);
    expect(JSON.stringify(data)).toBe(before);
  });
  it("preserva la separación entre componentes de MultiLineString", () => {
    const geometry = selectedGeometry(route([[[0,0],[0.01,0]],[[0.02,0],[0.03,0]]], [0.005,0], [0.025,0]), 1, 2);
    expect(geometry?.coordinates).toHaveLength(2);
    expect(geometry?.coordinates[0].at(-1)).toEqual([0.01,0]);
    expect(geometry?.coordinates[1][0]).toEqual([0.02,0]);
  });
  it("omite el resaltado cuando la proyección sobre un loop es ambigua", () => {
    const data = route([[[0,0],[0.01,0]],[[0.01,0],[0,0]]], [0.002,0], [0.008,0]);
    expect(selectedGeometry(data, 1, 2)).toBeNull();
  });
});
