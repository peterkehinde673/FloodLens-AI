"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Props = {
  flood: GeoJSON.FeatureCollection;
  roads: GeoJSON.FeatureCollection;
  communities: GeoJSON.FeatureCollection;
  bridges: GeoJSON.FeatureCollection;
  isolated: Set<string>;
};

export default function FloodMap({
  flood,
  roads,
  communities,
  bridges,
  isolated,
}: Props) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;

    const mapStyle =
      process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
      "https://tiles.openfreemap.org/styles/bright";

    const map = new maplibregl.Map({
      container: container.current,
      style: mapStyle,
      center: [6.755, 7.795],
      zoom: 11.2,
      attributionControl: true,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      const isolatedFeatures: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: communities.features.filter((feature) => {
          const id = String(feature.properties?.id ?? "");
          return isolated.has(id);
        }),
      };

      map.addSource("flood", { type: "geojson", data: flood });
      map.addSource("roads", { type: "geojson", data: roads });
      map.addSource("communities", { type: "geojson", data: communities });
      map.addSource("bridges", { type: "geojson", data: bridges });
      map.addSource("isolated", { type: "geojson", data: isolatedFeatures });

      map.addLayer({
        id: "flood-fill",
        type: "fill",
        source: "flood",
        paint: { "fill-color": "#38bdf8", "fill-opacity": 0.38 },
      });

      map.addLayer({
        id: "roads-line",
        type: "line",
        source: "roads",
        paint: { "line-color": "#64748b", "line-width": 2 },
      });

      map.addLayer({
        id: "roads-affected",
        type: "line",
        source: "roads",
        filter: ["==", ["get", "status"], "potentially_affected"],
        paint: { "line-color": "#fb7185", "line-width": 5 },
      });

      map.addLayer({
        id: "bridges-line",
        type: "line",
        source: "bridges",
        paint: { "line-color": "#94a3b8", "line-width": 4 },
      });

      map.addLayer({
        id: "bridges-affected",
        type: "line",
        source: "bridges",
        filter: ["==", ["get", "status"], "potentially_affected"],
        paint: { "line-color": "#f59e0b", "line-width": 8 },
      });

      map.addLayer({
        id: "communities-points",
        type: "circle",
        source: "communities",
        paint: {
          "circle-radius": 6,
          "circle-color": "#e2e8f0",
          "circle-stroke-color": "#0f172a",
          "circle-stroke-width": 2,
        },
      });

      map.addLayer({
        id: "isolated-points",
        type: "circle",
        source: "isolated",
        paint: {
          "circle-radius": 9,
          "circle-color": "#ef4444",
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });

      map.on("click", "communities-points", (event) => {
        const feature = event.features?.[0];
        if (!feature) return;

        new maplibregl.Popup()
          .setLngLat(event.lngLat)
          .setText(String(feature.properties?.name ?? "Community"))
          .addTo(map);
      });

      map.on("mouseenter", "communities-points", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "communities-points", () => {
        map.getCanvas().style.cursor = "";
      });

      map.fitBounds(
        [
          [6.70, 7.75],
          [6.79, 7.85],
        ],
        { padding: 70, maxZoom: 12.5, duration: 0 },
      );
    });

    return () => map.remove();
  }, [flood, roads, communities, bridges, isolated]);

  return <div ref={container} className="absolute inset-0" />;
}
