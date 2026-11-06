"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
import type { FeatureCollection, Feature, Geometry } from "geojson";
import type { Route } from "@/lib/types";
import { officialStops } from "@/lib/route-data";
import { selectedGeometry } from "@/lib/map-segment";
import { useApp } from "./providers";

export function MapView({
  routes,
  full = false,
  selectedOccurrenceId,
  startOccurrenceId,
  endOccurrenceId,
  onSelectStop,
}: {
  routes: Route[];
  full?: boolean;
  selectedOccurrenceId?: number;
  startOccurrenceId?: number;
  endOccurrenceId?: number;
  onSelectStop?: (occurrenceId: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useApp();
  const [error, setError] = useState("");
  const mapRef = useRef<maplibregl.Map | undefined>(undefined);
  const selectionCallback = useRef(onSelectStop);
  const [ready, setReady] = useState(0);
  useEffect(() => { selectionCallback.current = onSelectStop; }, [onSelectStop]);
  useEffect(() => {
    if (!container.current) return;
    container.current.setAttribute("aria-busy", "true");
    let map: maplibregl.Map | undefined;
    let cancelled = false;
    async function initialize() {
      try {
        const config = await fetch("/map-config").then((r) => r.json());
        if (cancelled || !container.current) return;
        const tokens = getComputedStyle(document.documentElement);
        const background = tokens.getPropertyValue("--surface-alt").trim();
        const text = tokens.getPropertyValue("--text-primary").trim();
        const accent = tokens.getPropertyValue("--brand-accent").trim();
        const blank: StyleSpecification = {
          version: 8,
          sources: {},
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": background },
            },
          ],
        };
        const style: string | StyleSpecification = (resolvedTheme === "dark"
          ? config.dark
          : config.light) || {
          ...blank,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution:
                '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
            },
          },
          layers: [
            ...blank.layers,
            {
              id: "osm",
              type: "raster",
              source: "osm",
              paint:
                resolvedTheme === "dark"
                  ? {
                      "raster-saturation": -1,
                      "raster-brightness-max": 0.4,
                      "raster-brightness-min": 0.08,
                    }
                  : { "raster-saturation": -0.85, "raster-opacity": 0.65 },
            },
          ],
        };
        maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        map = new maplibregl.Map({
          container: container.current,
          style,
          center: [-58.435, -34.61],
          zoom: 11,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.addControl(
          new maplibregl.NavigationControl({ showCompass: false }),
          "top-right",
        );
        map.addControl(
          new maplibregl.ScaleControl({ unit: "metric" }),
          "bottom-right",
        );
        map.on("error", () => {
          if (!cancelled)
            setError(
              "Parte del mapa base no está disponible. Podés seguir consultando los recorridos y sus paradas.",
            );
        });
        // El catálogo propio se dibuja sin esperar las teselas del proveedor.
        map.on("style.load", () => {
          if (!map || cancelled) return;
          const features: Feature[] = routes.flatMap((route) =>
            route.geometria
              ? [
                  {
                    type: "Feature",
                    geometry: route.geometria,
                    properties: {
                      color: route.colores?.color_principal || text,
                      label: `Línea ${route.linea_numero} · Ramal ${route.ramal_nombre} · ${route.sentido}`,
                    },
                  },
                ]
              : [],
          );
          map.addSource("routes", {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features,
            } as FeatureCollection<Geometry>,
          });
          map.addLayer({
            id: "route-outline",
            type: "line",
            source: "routes",
            layout: { "line-join": "round", "line-cap": "round" },
            paint: { "line-color": background, "line-width": 9 },
          });
          map.addLayer({
            id: "route-lines",
            type: "line",
            source: "routes",
            layout: { "line-join": "round", "line-cap": "round" },
            paint: {
              "line-color": ["get", "color"],
              "line-width": 5,
              "line-opacity": 0.95,
            },
          });
          map.addSource("selected-segment", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({ id: "selected-segment-line", type: "line", source: "selected-segment",
            layout: { "line-join": "round", "line-cap": "round" },
            paint: { "line-color": accent, "line-width": 7, "line-opacity": 1 },
          });
          const stops: Feature[] = routes.flatMap((route) =>
            officialStops(route).map((stop) => ({
              type: "Feature" as const,
              id: stop.id,
              geometry: {
                type: "Point" as const,
                coordinates: stop.parada.coordenadas,
              },
              properties: {
                visited: stop.transitada,
                occurrence: stop.id,
                label: stop.parada.nombre,
                status: `Oficial · ${stop.transitada ? "Transitada" : "Pendiente"}`,
              },
            })),
          );
          map.addSource("stops", {
            type: "geojson",
            attribution: stops.length
              ? '<a href="https://data.buenosaires.gob.ar/dataset/colectivos-paradas" target="_blank" rel="noopener">BA Data · Paradas CABA</a> · <a href="https://creativecommons.org/licenses/by/2.5/ar/" target="_blank" rel="noopener">CC BY 2.5 AR</a>'
              : "",
            data: {
              type: "FeatureCollection",
              features: stops,
            } as FeatureCollection,
          });
          map.addLayer({
            id: "stop-points",
            type: "circle",
            source: "stops",
            paint: {
              "circle-radius": [
                "interpolate",
                ["linear"],
                ["zoom"],
                9,
                3,
                15,
                7,
              ],
              "circle-color": ["case",
                ["boolean", ["feature-state", "start"], false], tokens.getPropertyValue("--interactive").trim(),
                ["boolean", ["feature-state", "end"], false], tokens.getPropertyValue("--success").trim(),
                ["boolean", ["feature-state", "selected"], false], accent,
                ["boolean", ["feature-state", "in_segment"], false], accent,
                ["get", "visited"], accent, background],
              "circle-stroke-color": text,
              "circle-stroke-width": 1.5,
            },
          });
          map.addLayer({
            id: "selected-stop", type: "circle", source: "stops",
            paint: {
              "circle-radius": 12,
              "circle-color": "transparent",
              "circle-stroke-color": text,
              "circle-stroke-width": ["case", ["boolean", ["feature-state", "selected"], false], 3, 0],
            },
          });
          setReady((value) => value + 1);
          const bounds = new maplibregl.LngLatBounds();
          routes.forEach((route) =>
            route.geometria?.coordinates.forEach((part) =>
              part.forEach((point) => bounds.extend([point[0], point[1]])),
            ),
          );
          if (!bounds.isEmpty())
            map.fitBounds(bounds, { padding: 45, maxZoom: 14, duration: 0 });
          const rendered = () => {
            if (!map || cancelled) return;
            if (
              !features.length ||
              map.queryRenderedFeatures({ layers: ["route-lines"] }).length
            ) {
              container.current?.setAttribute("aria-busy", "false");
              map.off("render", rendered);
            }
          };
          map.on("render", rendered);
          for (const layer of ["stop-points", "route-lines"]) {
            map.on("mouseenter", layer, () => {
              if (map) map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", layer, () => {
              if (map) map.getCanvas().style.cursor = "";
            });
            map.on("click", layer, (event) => {
              const props = event.features?.[0]?.properties;
              if (layer === "stop-points" && props?.occurrence)
                selectionCallback.current?.(Number(props.occurrence));
              if (map && props)
                new maplibregl.Popup()
                  .setLngLat(event.lngLat)
                  .setText(
                    `${props.label}${props.status ? ` · ${props.status}` : ""}`,
                  )
                  .addTo(map);
            });
          }
        });
      } catch {
        if (!cancelled)
          setError(
            "Tu navegador no pudo abrir el mapa. Podés consultar las paradas en la lista de cada recorrido.",
          );
      }
    }
    setError("");
    void initialize();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = undefined;
    };
  }, [routes, resolvedTheme]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getSource("stops")) return;
    const stops = routes.flatMap(officialStops);
    const start = stops.find((item) => item.id === startOccurrenceId);
    const end = stops.find((item) => item.id === endOccurrenceId);
    map.removeFeatureState({ source: "stops" });
    for (const stop of stops) {
      const flags = {
        selected: stop.id === selectedOccurrenceId,
        start: stop.id === startOccurrenceId,
        end: stop.id === endOccurrenceId,
        in_segment: Boolean(start && end && start.orden <= stop.orden && stop.orden <= end.orden),
      };
      if (Object.values(flags).some(Boolean))
        map.setFeatureState({ source: "stops", id: stop.id }, flags);
    }
    map.setPaintProperty("route-lines", "line-opacity", start && end ? 0.55 : 0.95);
    const segment = routes.flatMap((route) => {
      const geometry = selectedGeometry(route, startOccurrenceId, endOccurrenceId);
      return geometry ? [{ type: "Feature" as const, geometry, properties: {} }] : [];
    });
    (map.getSource("selected-segment") as maplibregl.GeoJSONSource | undefined)?.setData({ type: "FeatureCollection", features: segment });
    const selected = stops.find((item) => item.id === selectedOccurrenceId);
    if (selected) map.easeTo({ center: selected.parada.coordenadas, zoom: Math.max(map.getZoom(), 14),
      duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 400 });
  }, [routes, selectedOccurrenceId, startOccurrenceId, endOccurrenceId, ready]);
  if (!routes.some((route) => route.geometria !== null))
    return (
      <div className="state">
        <h3>Trazado todavía no disponible</h3>
        <p>
          Este recorrido está en el catálogo. El mapa se habilita cuando se
          incorpora su geometría.
        </p>
      </div>
    );
  return (
    <div className={`map-container ${full ? "full-map" : ""}`}>
      <div
        ref={container}
        className="map-canvas"
        role="region"
        aria-label="Mapa interactivo de recorridos y paradas"
        data-selected-occurrence={selectedOccurrenceId}
        data-start-occurrence={startOccurrenceId}
        data-end-occurrence={endOccurrenceId}
      />
      {error && (
        <p className="map-error" role="status">
          {error}
        </p>
      )}
      <div className="map-legend">
        <span>
          <i className="done" /> Transitada
        </span>
        <span>
          <i /> Pendiente
        </span>
        <span>Seleccioná una parada</span>
        {startOccurrenceId && <span>Inicio: azul</span>}
        {endOccurrenceId && <span>Fin: verde</span>}
      </div>
    </div>
  );
}
