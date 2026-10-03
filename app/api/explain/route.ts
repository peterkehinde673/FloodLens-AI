import { NextResponse } from "next/server";

type RequestBody = {
  event: string;
  before: string;
  after: string;
  gapDays: number;
  areaKm2: number;
  rawPercent: number;
  cleanedPercent: number;
  affectedRoads: number;
  affectedBridges: number;
  communities: Array<{
    name: string;
    access_status?: string;
    isolation_reason?: string;
    reachable_safe_nodes?: number;
  }>;
  vvMean: number;
  vhMean: number;
};

function fallback(body: RequestBody) {
  const isolated = body.communities.filter(
    (item) => item.access_status === "potentially_isolated",
  );

  return [
    `FloodLens analyzed Sentinel-1 observations from ${body.before} to ${body.after}, a ${body.gapDays}-day interval. The SAR change model identified approximately ${body.areaKm2.toFixed(2)} km² of candidate flood/change extent after spatial cleanup.`,
    `The infrastructure overlay contains ${body.affectedRoads} potentially affected road segments and ${body.affectedBridges} potentially affected bridges. The road-network model flags ${isolated.length} of ${body.communities.length} mapped communities as potentially isolated from the configured AOI boundary exits.`,
    isolated.length
      ? `Potentially isolated mapped locations: ${isolated.map((item) => item.name).join(", ")}. This is a network-accessibility inference, not confirmation that those communities were physically cut off.`
      : "No mapped community is currently flagged as potentially isolated by the road-network model.",
    "Interpretation: Sentinel-1 VV/VH backscatter change is evidence of candidate surface change consistent with inundation, but it does not by itself prove structural damage. OSM completeness, acquisition timing, registration, vegetation and other surface changes can affect the result.",
  ].join(" ");
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as RequestBody;
    const apiKey = process.env.GEMINI_API_KEY;
    const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";

    if (!apiKey) {
      return NextResponse.json({
        source: "FloodLens deterministic fallback",
        text: fallback(body),
      });
    }

    const prompt = `You are the evidence-explanation layer for FloodLens AI, a disaster mapping system.

Write a concise operational evidence brief for a disaster-response reviewer.

Rules:
- Treat all flood and infrastructure findings as potential, not confirmed physical damage.
- Do not invent facts, roads, communities, causes, or casualties.
- Clearly distinguish satellite evidence from road-network inference.
- Mention uncertainty from Sentinel-1 change detection and OpenStreetMap completeness.
- Use the supplied measurements exactly.
- Keep the answer to 3 short paragraphs and no markdown table.

Evidence:
Event: ${body.event}
Before acquisition: ${body.before}
After acquisition: ${body.after}
Observation gap: ${body.gapDays} days
Candidate extent: ${body.areaKm2.toFixed(4)} km²
Raw candidate pixels: ${body.rawPercent.toFixed(2)}%
Cleaned candidate pixels: ${body.cleanedPercent.toFixed(2)}%
VV mean change: ${body.vvMean.toFixed(2)} dB
VH mean change: ${body.vhMean.toFixed(2)} dB
Potentially affected roads: ${body.affectedRoads}
Potentially affected bridges: ${body.affectedBridges}
Mapped communities: ${body.communities.length}
Potentially isolated communities:
${body.communities
  .filter((item) => item.access_status === "potentially_isolated")
  .map((item) => `- ${item.name}: ${item.isolation_reason || "no route to configured boundary exits"}`)
  .join("\n") || "- None"}

Return only the evidence brief.`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            temperature: 0.2,
            maxOutputTokens: 500,
          },
        }),
      },
    );

    if (!response.ok) {
      return NextResponse.json({
        source: "FloodLens deterministic fallback",
        text: fallback(body),
        warning: `Gemini request failed with HTTP ${response.status}.`,
      });
    }

    const payload = await response.json();
    const text =
      payload?.candidates?.[0]?.content?.parts
        ?.map((part: { text?: string }) => part.text || "")
        .join("")
        .trim() || fallback(body);

    return NextResponse.json({
      source: `Gemini (${model})`,
      text,
    });
  } catch {
    return NextResponse.json(
      { error: "Unable to generate the evidence brief." },
      { status: 400 },
    );
  }
}
