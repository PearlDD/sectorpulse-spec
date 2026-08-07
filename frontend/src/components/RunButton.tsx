import { useState } from "react";
import { triggerRun, type Report } from "../api/client";

const MAX_RUNS = 3;

interface RunButtonProps {
  usedToday: number;
  onComplete: (report: Report) => void;
}

export default function RunButton({ usedToday, onComplete }: RunButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remaining = Math.max(0, MAX_RUNS - usedToday);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const report = await triggerRun();
      onComplete(report);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Run failed";
      if (msg.includes("429")) {
        setError("Daily limit reached");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleRun}
        disabled={loading || remaining === 0}
        className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            Running...
          </span>
        ) : (
          "Run Analysis"
        )}
      </button>
      <span className="text-xs text-slate-400">
        {remaining} run{remaining !== 1 ? "s" : ""} remaining today
      </span>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
