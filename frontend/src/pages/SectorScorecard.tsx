import { useEffect, useState } from "react";
import { fetchSectors, type SectorData } from "../api/client";

const SECTOR_NAMES: Record<string, string> = {
  XLB: "Materials",
  XLC: "Communication Services",
  XLE: "Energy",
  XLF: "Financials",
  XLI: "Industrials",
  XLK: "Technology",
  XLP: "Consumer Staples",
  XLRE: "Real Estate",
  XLU: "Utilities",
  XLV: "Health Care",
  XLY: "Consumer Discretionary",
};

const QUADRANT_BADGES: Record<string, { label: string; cls: string }> = {
  Leading: { label: "Leading", cls: "bg-green-600/20 text-green-400" },
  Weakening: { label: "Weakening", cls: "bg-yellow-600/20 text-yellow-400" },
  Lagging: { label: "Lagging", cls: "bg-red-600/20 text-red-400" },
  Improving: { label: "Improving", cls: "bg-blue-600/20 text-blue-400" },
};

interface SectorRow {
  ticker: string;
  name: string;
  score: number;
  weight: number;
  quadrant: string;
  oversold: boolean;
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

interface Props {
  rrg?: Record<string, { quadrant: string }> | null;
  oversold?: string[];
}

export default function SectorScorecard({ rrg, oversold = [] }: Props) {
  const [data, setData] = useState<SectorData | null | undefined>(undefined);
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    fetchSectors()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (data === undefined) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-slate-400">Loading scorecard...</span>
      </div>
    );
  }

  if (!data) return null;

  const oversoldSet = new Set(oversold);

  const rows: SectorRow[] = Object.entries(data.sector_scores).map(
    ([ticker, score]) => ({
      ticker,
      name: SECTOR_NAMES[ticker] ?? ticker,
      score,
      weight: data.allocation[ticker] ?? 0,
      quadrant: rrg?.[ticker]?.quadrant ?? "—",
      oversold: oversoldSet.has(ticker),
    }),
  );

  rows.sort((a, b) => (sortAsc ? a.score - b.score : b.score - a.score));

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-200">
          Sector Scorecard
        </h3>
        <button
          onClick={() => setSortAsc((v) => !v)}
          className="text-xs text-slate-400 hover:text-slate-200 transition"
        >
          Sort: {sortAsc ? "Low → High" : "High → Low"}
        </button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-800/40">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-400">
              <th className="px-4 py-3">Ticker</th>
              <th className="px-4 py-3">Sector</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Allocation</th>
              <th className="px-4 py-3">Quadrant</th>
              <th className="px-4 py-3">Flags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const badge = QUADRANT_BADGES[row.quadrant];
              return (
                <tr
                  key={row.ticker}
                  className="border-b border-slate-800 last:border-0 hover:bg-slate-700/30 transition"
                >
                  <td className="px-4 py-3 font-bold text-indigo-400">
                    {row.ticker}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{row.name}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-slate-700">
                        <div
                          className={`h-1.5 rounded-full ${scoreBg(row.score)}`}
                          style={{ width: `${row.score}%` }}
                        />
                      </div>
                      <span className={`font-semibold ${scoreColor(row.score)}`}>
                        {row.score}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {row.weight > 0
                      ? `${(row.weight * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {badge ? (
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}
                      >
                        {badge.label}
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.oversold && (
                      <span className="rounded-full bg-orange-600/20 px-2 py-0.5 text-xs font-medium text-orange-400">
                        Oversold
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
