import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchReports, type ReportSummary } from "../api/client";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-600/20 text-green-400",
  moderate: "bg-yellow-600/20 text-yellow-400",
  elevated: "bg-orange-600/20 text-orange-400",
  high: "bg-red-600/20 text-red-400",
};

function riskBadge(level: string): string {
  return RISK_COLORS[level.toLowerCase()] ?? "bg-slate-600/20 text-slate-400";
}

const PAGE_SIZE = 20;

export default function History() {
  const navigate = useNavigate();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);

  function load(offset: number, append: boolean) {
    setLoading(true);
    fetchReports(PAGE_SIZE, offset)
      .then((data) => {
        setReports((prev) => (append ? [...prev, ...data] : data));
        setHasMore(data.length === PAGE_SIZE);
      })
      .catch(() => setHasMore(false))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(0, false);
  }, []);

  if (!loading && reports.length === 0) {
    return (
      <div className="mx-auto max-w-2xl py-24 text-center">
        <h2 className="text-2xl font-bold text-slate-200">No reports yet</h2>
        <p className="mt-2 text-slate-400">
          Run an analysis from the Dashboard to generate your first report.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Analysis History</h1>
        <p className="mt-1 text-sm text-slate-400">
          Browse past sector rotation reports
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-800/40">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-wider text-slate-400">
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Cycle Phase</th>
              <th className="px-4 py-3">Risk Level</th>
              <th className="px-4 py-3">Trigger</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr
                key={r.id}
                onClick={() => navigate(`/report/${r.id}`)}
                className="cursor-pointer border-b border-slate-800 last:border-0 hover:bg-slate-700/30 transition"
              >
                <td className="px-4 py-3 text-slate-200">
                  {r.created_at
                    ? new Date(r.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </td>
                <td className="px-4 py-3 font-medium text-slate-100">
                  {r.cycle_phase}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskBadge(r.risk_level)}`}
                  >
                    {r.risk_level}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400 capitalize">
                  {r.trigger}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && (
        <div className="flex justify-center py-4">
          <span className="text-slate-400">Loading...</span>
        </div>
      )}

      {hasMore && !loading && (
        <div className="flex justify-center">
          <button
            onClick={() => load(reports.length, true)}
            className="rounded-lg border border-slate-700 px-5 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 transition"
          >
            Load More
          </button>
        </div>
      )}
    </div>
  );
}
