import { useEffect, useState } from "react";
import { fetchLatestReport, fetchRRG, type Report, type RRGPoint } from "../api/client";
import RunButton from "../components/RunButton";
import SectorScorecard from "./SectorScorecard";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-600",
  moderate: "bg-yellow-500",
  elevated: "bg-orange-500",
  high: "bg-red-600",
};

function riskColor(level: string): string {
  return RISK_COLORS[level.toLowerCase()] ?? "bg-slate-600";
}

export default function Dashboard() {
  const [report, setReport] = useState<Report | null | undefined>(undefined);
  const [runsUsed, setRunsUsed] = useState(0);
  const [rrg, setRrg] = useState<Record<string, RRGPoint> | null>(null);

  useEffect(() => {
    fetchLatestReport().then(setReport);
    fetchRRG()
      .then((d) => setRrg(d.rrg_data ?? null))
      .catch(() => setRrg(null));
  }, []);

  function handleRunComplete(newReport: Report) {
    setReport(newReport);
    setRunsUsed((n) => n + 1);
  }

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
        <h2 className="text-2xl font-bold text-slate-200">
          No analysis yet
        </h2>
        <p className="mt-2 text-slate-400">
          Click Run Now to generate your first sector analysis.
        </p>
        <div className="mt-6 flex justify-center">
          <RunButton usedToday={runsUsed} onComplete={handleRunComplete} />
        </div>
      </div>
    );
  }

  // Build top-5 sectors by allocation weight
  const topSectors = Object.entries(report.allocation)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Market Cycle Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-slate-800/60 p-5">
        <div className="flex items-center gap-4">
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
              className={`mt-0.5 inline-block rounded-full px-3 py-0.5 text-xs font-semibold text-white ${riskColor(report.risk_level)}`}
            >
              {report.risk_level}
            </span>
          </div>
        </div>
        <RunButton usedToday={runsUsed} onComplete={handleRunComplete} />
      </div>

      {/* Hot Sectors */}
      <section>
        <h3 className="mb-3 text-lg font-semibold text-slate-200">
          Hot Sectors
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {topSectors.map(([ticker, weight]) => (
            <div
              key={ticker}
              className="rounded-xl border border-slate-700 bg-slate-800/40 p-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-lg font-bold text-indigo-400">
                  {ticker}
                </span>
                <span className="text-xs text-slate-400">
                  {(weight * 100).toFixed(1)}%
                </span>
              </div>
              <div className="mt-1 text-sm text-slate-300">
                Score:{" "}
                <span className="font-medium">
                  {report.sector_scores[ticker] ?? "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

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

      {/* Sector Scorecard */}
      <SectorScorecard rrg={rrg} />
    </div>
  );
}
