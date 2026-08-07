import { useEffect, useState } from "react";
import {
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  Line,
  ComposedChart,
  ResponsiveContainer,
} from "recharts";
import { fetchRRG, type RRGPoint } from "../api/client";

const QUADRANT_COLORS = {
  Leading: "rgba(34,197,94,0.08)",
  Weakening: "rgba(234,179,8,0.08)",
  Lagging: "rgba(239,68,68,0.08)",
  Improving: "rgba(59,130,246,0.08)",
};

const DOT_COLORS: Record<string, string> = {
  Leading: "#22c55e",
  Weakening: "#eab308",
  Lagging: "#ef4444",
  Improving: "#3b82f6",
};

function quadrantLabel(q: string): string {
  return q.charAt(0).toUpperCase() + q.slice(1);
}

interface PlotPoint {
  ticker: string;
  rs_ratio: number;
  rs_momentum: number;
  quadrant: string;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PlotPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as PlotPoint;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm shadow-lg">
      <p className="font-bold text-slate-100">{d.ticker}</p>
      <p className="text-slate-300">
        RS-Ratio: <span className="font-medium text-white">{d.rs_ratio.toFixed(2)}</span>
      </p>
      <p className="text-slate-300">
        RS-Momentum: <span className="font-medium text-white">{d.rs_momentum.toFixed(2)}</span>
      </p>
      <p className="text-slate-400">
        Quadrant:{" "}
        <span style={{ color: DOT_COLORS[d.quadrant] ?? "#94a3b8" }}>
          {quadrantLabel(d.quadrant)}
        </span>
      </p>
    </div>
  );
}

function DotLabel(props: {
  cx?: number;
  cy?: number;
  payload?: PlotPoint;
}) {
  const { cx = 0, cy = 0, payload } = props;
  if (!payload) return null;
  return (
    <text
      x={cx}
      y={cy - 10}
      textAnchor="middle"
      fill="#e2e8f0"
      fontSize={11}
      fontWeight={600}
    >
      {payload.ticker}
    </text>
  );
}

export default function RRGChart() {
  const [sectors, setSectors] = useState<Record<string, RRGPoint> | null | undefined>(undefined);

  useEffect(() => {
    fetchRRG()
      .then((data) => setSectors(data.rrg_data))
      .catch(() => setSectors(null));
  }, []);

  if (sectors === undefined) {
    return (
      <div className="flex items-center justify-center py-32">
        <span className="text-slate-400">Loading...</span>
      </div>
    );
  }

  if (!sectors || Object.keys(sectors).length === 0) {
    return (
      <div className="mx-auto max-w-2xl py-24 text-center">
        <h2 className="text-2xl font-bold text-slate-200">No RRG data available</h2>
        <p className="mt-2 text-slate-400">
          Run an analysis from the Dashboard to generate RRG data.
        </p>
      </div>
    );
  }

  const points: PlotPoint[] = Object.values(sectors).map((s) => ({
    ticker: s.ticker,
    rs_ratio: s.rs_ratio,
    rs_momentum: s.rs_momentum,
    quadrant: s.quadrant,
  }));

  // Compute axis domain with padding
  const allRatios = points.map((p) => p.rs_ratio);
  const allMomentums = points.map((p) => p.rs_momentum);

  // Include trail points in domain calculation
  Object.values(sectors).forEach((s) => {
    if (s.trail) {
      s.trail.forEach((t) => {
        allRatios.push(t.rs_ratio);
        allMomentums.push(t.rs_momentum);
      });
    }
  });

  const pad = 0.5;
  const xMin = Math.min(95, Math.min(...allRatios) - pad);
  const xMax = Math.max(105, Math.max(...allRatios) + pad);
  const yMin = Math.min(95, Math.min(...allMomentums) - pad);
  const yMax = Math.max(105, Math.max(...allMomentums) + pad);

  // Build trail line data per sector
  const trailLines: { ticker: string; data: { rs_ratio: number; rs_momentum: number }[]; color: string }[] = [];
  Object.values(sectors).forEach((s) => {
    if (s.trail && s.trail.length > 1) {
      trailLines.push({
        ticker: s.ticker,
        data: [...s.trail, { rs_ratio: s.rs_ratio, rs_momentum: s.rs_momentum }],
        color: DOT_COLORS[s.quadrant] ?? "#94a3b8",
      });
    }
  });

  // Improving sectors for "Next-Hot" callout
  const improving = points.filter((p) => p.quadrant === "Improving");

  // Group points by quadrant for coloring
  const byQuadrant: Record<string, PlotPoint[]> = {};
  for (const p of points) {
    (byQuadrant[p.quadrant] ??= []).push(p);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Relative Rotation Graph</h1>
        <p className="mt-1 text-sm text-slate-400">
          Sector momentum vs. relative strength — track rotation dynamics
        </p>
      </div>

      <div className="rounded-xl bg-slate-800/40 p-4">
        <ResponsiveContainer width="100%" height={520}>
          <ComposedChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

            {/* Quadrant backgrounds */}
            <ReferenceArea x1={100} x2={xMax} y1={100} y2={yMax} fill={QUADRANT_COLORS.Leading} fillOpacity={1} />
            <ReferenceArea x1={100} x2={xMax} y1={yMin} y2={100} fill={QUADRANT_COLORS.Weakening} fillOpacity={1} />
            <ReferenceArea x1={xMin} x2={100} y1={yMin} y2={100} fill={QUADRANT_COLORS.Lagging} fillOpacity={1} />
            <ReferenceArea x1={xMin} x2={100} y1={100} y2={yMax} fill={QUADRANT_COLORS.Improving} fillOpacity={1} />

            <XAxis
              dataKey="rs_ratio"
              type="number"
              domain={[xMin, xMax]}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              label={{ value: "RS-Ratio", position: "insideBottom", offset: -10, fill: "#94a3b8" }}
              stroke="#475569"
            />
            <YAxis
              dataKey="rs_momentum"
              type="number"
              domain={[yMin, yMax]}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              label={{ value: "RS-Momentum", angle: -90, position: "insideLeft", offset: 0, fill: "#94a3b8" }}
              stroke="#475569"
            />

            {/* Center reference lines */}
            <ReferenceLine x={100} stroke="#64748b" strokeDasharray="4 4" />
            <ReferenceLine y={100} stroke="#64748b" strokeDasharray="4 4" />

            {/* Quadrant labels */}
            <ReferenceArea
              x1={xMax - (xMax - 100) * 0.4}
              x2={xMax - (xMax - 100) * 0.05}
              y1={yMax - (yMax - 100) * 0.15}
              y2={yMax - (yMax - 100) * 0.05}
              fill="transparent"
              label={{ value: "Leading", fill: "#22c55e", fontSize: 13, fontWeight: 600 }}
            />
            <ReferenceArea
              x1={xMax - (xMax - 100) * 0.4}
              x2={xMax - (xMax - 100) * 0.05}
              y1={yMin + (100 - yMin) * 0.05}
              y2={yMin + (100 - yMin) * 0.15}
              fill="transparent"
              label={{ value: "Weakening", fill: "#eab308", fontSize: 13, fontWeight: 600 }}
            />
            <ReferenceArea
              x1={xMin + (100 - xMin) * 0.05}
              x2={xMin + (100 - xMin) * 0.4}
              y1={yMin + (100 - yMin) * 0.05}
              y2={yMin + (100 - yMin) * 0.15}
              fill="transparent"
              label={{ value: "Lagging", fill: "#ef4444", fontSize: 13, fontWeight: 600 }}
            />
            <ReferenceArea
              x1={xMin + (100 - xMin) * 0.05}
              x2={xMin + (100 - xMin) * 0.4}
              y1={yMax - (yMax - 100) * 0.15}
              y2={yMax - (yMax - 100) * 0.05}
              fill="transparent"
              label={{ value: "Improving", fill: "#3b82f6", fontSize: 13, fontWeight: 600 }}
            />

            {/* Trail lines */}
            {trailLines.map((trail) => (
              <Line
                key={`trail-${trail.ticker}`}
                data={trail.data}
                dataKey="rs_momentum"
                stroke={trail.color}
                strokeWidth={1.5}
                strokeOpacity={0.4}
                dot={false}
                isAnimationActive={false}
                type="linear"
              />
            ))}

            {/* Scatter dots by quadrant */}
            {Object.entries(byQuadrant).map(([quadrant, qPoints]) => (
              <Scatter
                key={quadrant}
                data={qPoints}
                fill={DOT_COLORS[quadrant] ?? "#94a3b8"}
                label={<DotLabel />}
              />
            ))}

            <Tooltip content={<CustomTooltip />} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Next-Hot Candidates callout */}
      {improving.length > 0 && (
        <div className="rounded-xl border border-blue-500/30 bg-blue-950/30 p-5">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-blue-400">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-400" />
            Next-Hot Candidates
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Sectors in the Improving quadrant — gaining momentum and rotating toward leadership
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            {improving.map((s) => (
              <div
                key={s.ticker}
                className="rounded-lg border border-blue-500/20 bg-blue-900/20 px-4 py-2"
              >
                <span className="font-bold text-blue-300">{s.ticker}</span>
                <span className="ml-2 text-xs text-slate-400">
                  RS-R {s.rs_ratio.toFixed(1)} / RS-M {s.rs_momentum.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
