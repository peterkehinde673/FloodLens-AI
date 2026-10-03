"use client";

import { useCallback, useEffect, useState } from "react";
import FloodMap from "@/components/FloodMap";
import {
  Activity,
  CloudRain,
  RadioTower,
  RefreshCw,
  Route,
  Satellite,
  ShieldAlert,
} from "lucide-react";

type Summary = {
  event: string;
  aoi_bbox: number[];
  gap_hours: number;
  before_datetime: string;
  after_datetime: string;
  method: {
    vv_threshold_db: number;
    vh_threshold_db: number;
    minimum_component_pixels: number;
    note: string;
  };
  pixels: {
    valid: number;
    raw_candidate: number;
    cleaned_candidate: number;
    raw_percent: number;
    cleaned_percent: number;
  };
  area_km2: number;
  osm: {
    roads: number;
    bridges: number;
    communities: number;
    potentially_affected_roads: number;
    potentially_affected_bridges: number;
    potentially_isolated_communities: number;
    boundary_exit_nodes: number;
  };
  diagnostics: {
    vv_threshold_db: number;
    vh_threshold_db: number;
    vv_mean_change_db: number;
    vh_mean_change_db: number;
  };
};

const initialStats = [
  { label: "Candidate flood extent", value: "—", icon: CloudRain },
  { label: "Potentially affected roads", value: "—", icon: Route },
  { label: "Potentially affected bridges", value: "—", icon: ShieldAlert },
  { label: "Mapped communities", value: "—", icon: RadioTower },
];

async function loadGeoJson(path: string) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`Unable to load ${path}`);
  return response.json() as Promise<GeoJSON.FeatureCollection>;
}

export default function Home() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [flood, setFlood] = useState<GeoJSON.FeatureCollection | null>(null);
  const [roads, setRoads] = useState<GeoJSON.FeatureCollection | null>(null);
  const [bridges, setBridges] = useState<GeoJSON.FeatureCollection | null>(null);
  const [communities, setCommunities] =
    useState<GeoJSON.FeatureCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [explanation, setExplanation] = useState("");
  const [explanationSource, setExplanationSource] = useState("");
  const [explaining, setExplaining] = useState(false);

  const loadLiveEvent = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const base = "/data/lokoja-2022/";
      const [s, f, r, b, c] = await Promise.all([
        fetch(base + "summary.json", { cache: "no-store" }).then(
          (x) => x.json() as Promise<Summary>,
        ),
        loadGeoJson(base + "flood_candidate_cleaned.geojson"),
        loadGeoJson(base + "affected_roads.geojson"),
        loadGeoJson(base + "bridges.geojson"),
        loadGeoJson(base + "communities.geojson"),
      ]);

      setSummary(s);
      setFlood(f);
      setRoads(r);
      setBridges(b);
      setCommunities(c);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load live Lokoja analysis.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLiveEvent();
  }, [loadLiveEvent]);

  const generateExplanation = useCallback(async () => {
    if (!summary || !communities) return;

    setExplaining(true);
    try {
      const response = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event: summary.event,
          before: new Date(summary.before_datetime).toLocaleDateString(),
          after: new Date(summary.after_datetime).toLocaleDateString(),
          gapDays: Math.round(summary.gap_hours / 24),
          areaKm2: summary.area_km2,
          rawPercent: summary.pixels.raw_percent,
          cleanedPercent: summary.pixels.cleaned_percent,
          affectedRoads: summary.osm.potentially_affected_roads,
          affectedBridges: summary.osm.potentially_affected_bridges,
          communities: communities.features.map((feature) => ({
            name: String(feature.properties?.name ?? "Unnamed community"),
            access_status: String(feature.properties?.access_status ?? ""),
            isolation_reason: String(
              feature.properties?.isolation_reason ?? "",
            ),
            reachable_safe_nodes: Number(
              feature.properties?.reachable_safe_nodes ?? 0,
            ),
          })),
          vvMean: summary.diagnostics.vv_mean_change_db,
          vhMean: summary.diagnostics.vh_mean_change_db,
        }),
      });

      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Explanation failed.");
      setExplanation(payload.text || "");
      setExplanationSource(payload.source || "FloodLens");
    } catch (err) {
      setExplanation(
        err instanceof Error
          ? err.message
          : "Unable to generate the evidence brief.",
      );
      setExplanationSource("FloodLens");
    } finally {
      setExplaining(false);
    }
  }, [summary, communities]);

  const isolated = new Set<string>(
    communities?.features
      .filter(
        (feature) =>
          feature.properties?.access_status === "potentially_isolated",
      )
      .map((feature) => String(feature.properties?.id ?? ""))
      .filter(Boolean) ?? [],
  );

  const stats = summary
    ? [
        {
          label: "Candidate flood extent",
          value: `${summary.area_km2.toFixed(2)} km²`,
          icon: CloudRain,
        },
        {
          label: "Potentially affected roads",
          value: String(summary.osm.potentially_affected_roads),
          icon: Route,
        },
        {
          label: "Potentially affected bridges",
          value: String(summary.osm.potentially_affected_bridges),
          icon: ShieldAlert,
        },
        {
          label: "Mapped communities",
          value: String(summary.osm.communities),
          icon: RadioTower,
        },
        {
          label: "Potentially isolated",
          value: String(summary.osm.potentially_isolated_communities),
          icon: Activity,
        },
      ]
    : initialStats;

  return (
    <main className="min-h-screen bg-[#071018] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a151f]/90 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-300">
              FLOODLENS AI
            </p>
            <h1 className="mt-1 text-xl font-semibold">
              Satellite Disaster Intelligence
            </h1>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1.5 text-xs text-cyan-200">
            <Satellite size={14} /> Live Sentinel-1 event
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1500px] p-6">
        <div className="mb-5 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          {stats.map(({ label, value, icon: Icon }) => (
            <div
              key={label}
              className="rounded-2xl border border-white/10 bg-white/[0.035] p-4"
            >
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs">{label}</span>
                <Icon size={16} />
              </div>
              <p className="mt-3 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid min-h-[620px] gap-5 lg:grid-cols-[1fr_360px]">
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[#0b1a25]">
            <div className="absolute left-6 top-6 z-10 rounded-xl border border-white/10 bg-[#071018]/90 px-4 py-3 backdrop-blur">
              <p className="text-xs text-slate-400">EVENT</p>
              <p className="font-medium">
                Lokoja, Kogi State · 2022 flood event
              </p>
            </div>

            <div className="absolute inset-0">
              {flood && roads && bridges && communities ? (
                <FloodMap
                  flood={flood}
                  roads={roads}
                  communities={communities}
                  bridges={bridges}
                  isolated={isolated}
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <Satellite
                      className="mx-auto text-cyan-300"
                      size={44}
                    />
                    <p className="mt-4 text-lg font-semibold">
                      {loading
                        ? "Loading satellite evidence…"
                        : "Live dataset unavailable"}
                    </p>
                    <p className="mt-2 text-sm text-slate-400">
                      {error ||
                        "FloodLens is preparing the analysis map."}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="absolute bottom-5 left-5 right-5 z-10 flex flex-wrap gap-2">
              {[
                ["Candidate flood extent", "bg-sky-400"],
                ["Potentially affected roads", "bg-rose-400"],
                ["Bridges", "bg-amber-400"],
                ["Communities", "bg-slate-200"],
                ["Potentially isolated", "bg-red-500"],
              ].map(([label, dot]) => (
                <span
                  key={label}
                  className="flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-1.5 text-xs text-slate-200 backdrop-blur"
                >
                  <span className={`h-2 w-2 rounded-full ${dot}`} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <aside className="rounded-3xl border border-white/10 bg-white/[0.035] p-5">
            <p className="text-xs font-semibold tracking-[0.2em] text-cyan-300">
              EVIDENCE PANEL
            </p>
            <h2 className="mt-2 text-xl font-semibold">
              Flood impact analysis
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Sentinel-1 VV/VH change identifies candidate flood/change areas,
              then the result is intersected with OpenStreetMap infrastructure.
            </p>

            <button
              onClick={() => void loadLiveEvent()}
              disabled={loading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              <RefreshCw
                size={15}
                className={loading ? "animate-spin" : ""}
              />
              {loading ? "Loading…" : "Refresh live dataset"}
            </button>

            {summary && (
              <>
                <button
                onClick={() => void generateExplanation()}
                disabled={explaining}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-3 text-sm font-semibold text-cyan-100 disabled:opacity-50"
              >
                <Activity size={15} className={explaining ? "animate-pulse" : ""} />
                {explaining ? "Generating evidence brief…" : "Generate AI evidence brief"}
              </button>

                {explanation && (
                  <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-4">
                  <p className="text-xs font-semibold tracking-[0.16em] text-cyan-300">
                    {explanationSource.toUpperCase()}
                  </p>
                  <p className="mt-2 whitespace-pre-line text-xs leading-6 text-slate-300">
                    {explanation}
                  </p>
                  </div>
                )}

                <div className="mt-5 space-y-3">
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-slate-500">
                    SENTINEL-1 ACQUISITIONS
                  </p>
                  <p className="mt-1 text-sm">
                    Before ·{" "}
                    {new Date(summary.before_datetime).toLocaleDateString()}
                  </p>
                  <p className="text-sm">
                    After ·{" "}
                    {new Date(summary.after_datetime).toLocaleDateString()}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {(summary.gap_hours / 24).toFixed(0)}-day observation gap
                  </p>
                </div>

                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-slate-500">CHANGE SIGNAL</p>
                  <p className="mt-1 text-sm">
                    VV mean: {summary.diagnostics.vv_mean_change_db.toFixed(2)} dB
                  </p>
                  <p className="text-sm">
                    VH mean: {summary.diagnostics.vh_mean_change_db.toFixed(2)} dB
                  </p>
                </div>

                <div className="rounded-xl border border-red-400/20 bg-red-400/5 p-4">
                  <p className="text-xs text-red-300">ACCESSIBILITY</p>
                  <p className="mt-1 text-xs leading-5 text-slate-300">
                    {summary.osm.potentially_isolated_communities} of{" "}
                    {summary.osm.communities} mapped communities are flagged
                    as potentially isolated after removing potentially
                    affected road edges. The graph uses{" "}
                    {summary.osm.boundary_exit_nodes} AOI-boundary road exit
                    nodes as potential destinations.
                  </p>
                </div>

                <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
                  <p className="text-xs text-amber-300">INTERPRETATION</p>
                  <p className="mt-1 text-xs leading-5 text-slate-300">
                    Sentinel-1 VV/VH identifies candidate flood/change areas;
                    satellite evidence alone does not confirm structural
                    damage. Accessibility results are also potential findings
                    limited by OSM completeness and the flood-classification
                    threshold.
                  </p>
                </div>
                </div>
              </>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
