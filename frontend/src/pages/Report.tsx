import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { fetchReport, type Report as ReportType } from "../api/client";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-600/20 text-green-400",
  moderate: "bg-yellow-600/20 text-yellow-400",
  elevated: "bg-orange-600/20 text-orange-400",
  high: "bg-red-600/20 text-red-400",
};

const PIE_COLORS = [
  "#6366f1", "#22c55e", "#eab308", "#ef4444", "#3b82f6",
  "#f97316", "#a855f7", "#14b8a6", "#ec4899", "#84cc16", "#06b6d4",
];

const QUADRANT_LABELS: Record<string, { label: string; cls: string }> = {
  Leading: { label: "Leading", cls: "text-green-400" },
  Weakening: { label: "Weakening", cls: "text-yellow-400" },
  Lagging: { label: "Lagging", cls: "text-red-400" },
  Improving: { label: "Improving", cls: "text-blue-400" },
};

function scoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

function riskBadge(level: string): string {
  return RISK_COLORS[level.toLowerCase()] ?? "bg-slate-600/20 text-slate-400";
}

interface PieSlice {
  name: string;
  value: number;
}

function PieTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PieSlice }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm shadow-lg">
      <p className="font-bold text-slate-100">{d.name}</p>
      <p className="text-slate-300">{(d.value * 100).toFixed(1)}%</p>
    </div>
  );
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportType | null | undefined>(
    undefined,
  );

  useEffect(() => {
    if (!id) return;
    fetchReport(Number(id))
      .then(setReport)
      .catch(() => setReport(null));
  }, [id]);

  if (report === undefined) {
    return (
      <div className="flex items-center justify-center py-32">
        <span className="text-slate-400">Loading...</span>
      </div>
    );
  }

  if (report === null) {
    return (
      <div className="mx-auto max-w-2xl py-24 text-center">
        <h2 className="text-2xl font-bold text-slate-200">Report not found</h2>
        <Link to="/history" className="mt-4 text-indigo-400 hover:underline">
          Back to History
        </Link>
      </div>
    );
  }

  // Sorted sector scores
  const sortedScores = Object.entries(report.sector_scores).sort(
    ([, a], [, b]) => b - a,
  );

  // Pie chart data — only sectors with positive allocation
  const pieData: PieSlice[] = Object.entries(report.allocation)
    .filter(([, w]) => w > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([ticker, weight]) => ({ name: ticker, value: weight }));

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/history"
        className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200 transition"
      >
        &larr; History
      </Link>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-slate-800/60 p-5">
        <div className="flex items-center gap-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-slate-400">
              Market Phase
            </span>
            <h2 className="text-xl font-bold text-slate-100">
              {report.cycle_phase}
            </h2>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider text-slate-400">
              Confidence
            </span>
            <p className="text-lg font-semibold text-slate-100">
              {(report.cycle_confidence * 100).toFixed(0)}%
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider text-slate-400">
              Risk Level
            </span>
            <span
              className={`mt-0.5 inline-block rounded-full px-3 py-0.5 text-xs font-semibold ${riskBadge(report.risk_level)}`}
            >
              {report.risk_level}
            </span>
          </div>
        </div>
        <div className="text-sm text-slate-400">
          {report.created_at
            ? new Date(report.created_at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })
            : ""}
          <span className="ml-2 capitalize text-slate-500">
            ({report.trigger})
          </span>
        </div>
      </div>

      {/* Narrative */}
      {report.narrative && (
        <section className="rounded-xl bg-slate-800/40 p-5">
          <h3 className="mb-2 text-lg font-semibold text-slate-200">
            Market Narrative
          </h3>
          <div className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
            {report.narrative}
          </div>
        </section>
      )}

      {/* Sector Scores + Allocation */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Scores table */}
        <section className="rounded-xl border border-slate-700 bg-slate-800/40">
          <h3 className="border-b border-slate-700 px-4 py-3 text-sm font-semibold text-slate-200">
            Sector Scores
          </h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-400">
                <th className="px-4 py-2">Ticker</th>
                <th className="px-4 py-2">Score</th>
                <th className="px-4 py-2">Weight</th>
              </tr>
            </thead>
            <tbody>
              {sortedScores.map(([ticker, score]) => (
                <tr
                  key={ticker}
                  className="border-b border-slate-800 last:border-0"
                >
                  <td className="px-4 py-2 font-bold text-indigo-400">
                    {ticker}
                  </td>
                  <td
                    className={`px-4 py-2 font-semibold ${scoreColor(score)}`}
                  >
                    {score}
                  </td>
                  <td className="px-4 py-2 text-slate-300">
                    {report.allocation[ticker]
                      ? `${(report.allocation[ticker] * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Pie chart */}
        <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-200">
            Portfolio Allocation
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={120}
                  label={({ name, value }) =>
                    `${name} ${(value * 100).toFixed(0)}%`
                  }
                  labelLine={{ stroke: "#64748b" }}
                >
                  {pieData.map((_, i) => (
                    <Cell
                      key={i}
                      fill={PIE_COLORS[i % PIE_COLORS.length]}
                      stroke="transparent"
                    />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-12 text-center text-slate-400">
              No allocation data
            </p>
          )}
        </section>
      </div>

      {/* RRG Snapshot */}
      {report.rrg_data && Object.keys(report.rrg_data).length > 0 && (
        <section className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-200">
            RRG Snapshot
          </h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {(["Leading", "Improving", "Weakening", "Lagging"] as const).map(
              (q) => {
                const sectors = Object.values(report.rrg_data!)
                  .filter((s) => s.quadrant === q)
                  .map((s) => s.ticker);
                const style = QUADRANT_LABELS[q];
                return (
                  <div
                    key={q}
                    className="rounded-lg border border-slate-700 bg-slate-900/50 p-3"
                  >
                    <h4
                      className={`text-xs font-semibold uppercase tracking-wider ${style?.cls ?? "text-slate-400"}`}
                    >
                      {style?.label ?? q}
                    </h4>
                    <div className="mt-2 space-y-1">
                      {sectors.length > 0 ? (
                        sectors.map((t) => (
                          <span
                            key={t}
                            className="mr-2 inline-block text-sm font-medium text-slate-200"
                          >
                            {t}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-500">None</span>
                      )}
                    </div>
                  </div>
                );
              },
            )}
          </div>
        </section>
      )}
    </div>
  );
}
