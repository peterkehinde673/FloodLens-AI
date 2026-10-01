import { Activity, BrainCircuit, CloudRain, RadioTower, Route, ShieldAlert } from "lucide-react";

const stats = [
  { label: "Flood extent", value: "— km²", icon: CloudRain },
  { label: "Affected roads", value: "—", icon: Route },
  { label: "Potentially affected bridges", value: "—", icon: ShieldAlert },
  { label: "Potentially isolated communities", value: "—", icon: RadioTower }
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#071018] text-slate-100">
      <header className="border-b border-white/10 bg-[#0a151f]/90 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.28em] text-cyan-300">FLOODLENS AI</p>
            <h1 className="mt-1 text-xl font-semibold">Satellite Disaster Intelligence</h1>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1.5 text-xs text-cyan-200">
            <Activity size={14} /> Demo mode · Day 1
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1500px] p-6">
        <div className="mb-5 grid gap-3 md:grid-cols-4">
          {stats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
              <div className="flex items-center justify-between text-slate-400"><span className="text-xs">{label}</span><Icon size={16} /></div>
              <p className="mt-3 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="grid min-h-[620px] gap-5 lg:grid-cols-[1fr_360px]">
          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[#0b1a25]">
            <div className="absolute inset-0 opacity-50" style={{ backgroundImage: "linear-gradient(rgba(100,200,220,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(100,200,220,.08) 1px, transparent 1px)", backgroundSize: "42px 42px" }} />
            <div className="absolute left-6 top-6 rounded-xl border border-white/10 bg-[#071018]/90 px-4 py-3 backdrop-blur">
              <p className="text-xs text-slate-400">EVENT</p><p className="font-medium">Select a flood event</p>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="max-w-md px-6 text-center">
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200"><BrainCircuit /></div>
                <h2 className="text-2xl font-semibold">Evidence before inference.</h2>
                <p className="mt-3 text-sm leading-6 text-slate-400">FloodLens will connect satellite flood evidence to roads, bridges, communities and network accessibility.</p>
              </div>
            </div>
            <div className="absolute bottom-5 left-5 right-5 flex flex-wrap gap-2">
              {["Satellite", "Flood extent", "Affected roads", "Bridges", "Communities", "Potential isolation"].map(x => <span key={x} className="rounded-full border border-white/10 bg-black/30 px-3 py-1.5 text-xs text-slate-300">{x}</span>)}
            </div>
          </div>

          <aside className="rounded-3xl border border-white/10 bg-white/[0.035] p-5">
            <p className="text-xs font-semibold tracking-[0.2em] text-cyan-300">MISSION PANEL</p>
            <h2 className="mt-2 text-xl font-semibold">Flood impact analysis</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">Run a deterministic demo event first. Live satellite retrieval will be added after the core analysis pipeline is verified.</p>
            <button className="mt-6 w-full rounded-xl bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950">Analyze event</button>
            <div className="mt-6 space-y-3">
              <div className="rounded-xl border border-white/10 p-4"><p className="text-xs text-slate-500">NEXT</p><p className="mt-1 text-sm">Load a before/after Sentinel-1 scene</p></div>
              <div className="rounded-xl border border-white/10 p-4"><p className="text-xs text-slate-500">THEN</p><p className="mt-1 text-sm">Generate flood mask and intersect infrastructure</p></div>
              <div className="rounded-xl border border-white/10 p-4"><p className="text-xs text-slate-500">FINALLY</p><p className="mt-1 text-sm">Explain which communities may be isolated</p></div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
