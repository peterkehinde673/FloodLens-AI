"use client";

import { useState } from "react";
import FloodMap from "@/components/FloodMap";
import {
  Activity,
  BrainCircuit,
  CloudRain,
  RadioTower,
  Route,
  ShieldAlert,
} from "lucide-react";

type Analysis = {
  status: string;
  flood_area_km2: number | null;
  affected_roads: Array<{ properties?: { id?: string; status?: string; impact_ratio?: number } }>;
  affected_bridges: Array<{ id: string; name: string; status: string; reason: string }>;
  isolated_communities: string[];
  community_analysis: Array<{ community_id: string; potentially_isolated: boolean; reason?: string }>;
  flood: GeoJSON.FeatureCollection;
  roads: GeoJSON.FeatureCollection;
  communities: GeoJSON.FeatureCollection;
  bridges: GeoJSON.FeatureCollection;
};

const initialStats = [
  { label: "Flood extent", value: "— km²", icon: CloudRain },
  { label: "Affected roads", value: "—", icon: Route },
  { label: "Potentially affected bridges", value: "—", icon: ShieldAlert },
  { label: "Potentially isolated communities", value: "—", icon: RadioTower },
];

export default function Home() {
  const [stats, setStats] = useState(initialStats);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isolated = new Set(analysis?.isolated_communities ?? []);

  async function analyzeEvent() {
    setLoading(true);
    setError("");

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(baseUrl + "/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: "event-01" }),
      });

      if (!response.ok) {
        throw new Error("FloodLens API returned an error.");
      }

      const data: Analysis = await response.json();
      setAnalysis(data);
      setStats([
        {
          label: "Flood extent",
          value: data.flood_area_km2 === null ? "Demo" : data.flood_area_km2.toFixed(2) + " km²",
          icon: CloudRain,
        },
        { label: "Affected roads", value: String(data.affected_roads.length), icon: Route },
        { label: "Potentially affected bridges", value: String(data.affected_bridges.length), icon: ShieldAlert },
        { label: "Potentially isolated communities", value: String(data.isolated_communities.length), icon: RadioTower },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach FloodLens API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#071018] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a151f]/90 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-300">FLOODLENS AI</p>
            <h1 className="mt-1 text-xl font-semibold">Satellite Disaster Intelligence</h1>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1.5 text-xs text-cyan-200">
            <Activity size={14} /> Demo mode · Analysis pipeline
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1500px] p-6">
        <div className="mb-5 grid gap-3 md:grid-cols-4">
          {stats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs">{label}</span><Icon size={16} />
              </div>
              <p className="mt-3 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid min-h-[620px] gap-5 lg:grid-cols-[1fr_360px]">
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[#0b1a25]">
            <div className="absolute left-6 top-6 z-10 rounded-xl border border-white/10 bg-[#071018]/90 px-4 py-3 backdrop-blur">
              <p className="text-xs text-slate-400">EVENT</p>
              <p className="font-medium">Synthetic connectivity demo</p>
            </div>

            <div className="absolute inset-0">
              {analysis ? (
                <FloodMap
                  flood={analysis.flood}
                  roads={analysis.roads}
                  communities={analysis.communities}
                  bridges={analysis.bridges}
                  isolated={isolated}
                />
              ) : (
                <div className="flex h-full items-center justify-center p-6">
                  <div className="w-full max-w-xl">
                    <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200">
                      <BrainCircuit />
                    </div>
                    <h2 className="text-center text-2xl font-semibold">Evidence before inference.</h2>
                    <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-400">
                      FloodLens connects flood extent to road impact and then tests whether mapped communities still have a route to the safe network.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="absolute bottom-5 left-5 right-5 z-10 flex flex-wrap gap-2">
              {[
                ["Flood extent", "bg-sky-400"],
                ["Affected roads", "bg-rose-400"],
                ["Bridges", "bg-amber-400"],
                ["Communities", "bg-slate-200"],
                ["Potential isolation", "bg-red-500"],
              ].map(([label, dot]) => (
                <span key={label} className="flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-1.5 text-xs text-slate-200 backdrop-blur">
                  <span className={"h-2 w-2 rounded-full " + dot} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <aside className="rounded-3xl border border-white/10 bg-white/[0.035] p-5">
            <p className="text-xs font-semibold tracking-[0.2em] text-cyan-300">MISSION PANEL</p>
            <h2 className="mt-2 text-xl font-semibold">Flood impact analysis</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Run the deterministic event to verify the complete flood-to-road-to-isolation pipeline before live satellite processing.
            </p>

            <button
              onClick={analyzeEvent}
              disabled={loading}
              className="mt-6 w-full rounded-xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Analyzing…" : "Analyze event"}
            </button>

            {error && (
              <p className="mt-3 rounded-xl border border-red-400/20 bg-red-400/5 p-3 text-xs leading-5 text-red-200">
                {error}
              </p>
            )}

            {analysis && (
              <div className="mt-5 space-y-3">
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-slate-500">RESULT</p>
                  <p className="mt-1 text-sm">{analysis.status}</p>
                </div>
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-slate-500">ISOLATION EVIDENCE</p>
                  <p className="mt-1 text-sm">
                    {analysis.isolated_communities.join(", ") || "No community flagged"}
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 p-4">
                  <p className="text-xs text-slate-500">NEXT</p>
                  <p className="mt-1 text-sm">
                    Replace the synthetic flood mask with a Sentinel-1 before/after result.
                  </p>
                </div>
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
