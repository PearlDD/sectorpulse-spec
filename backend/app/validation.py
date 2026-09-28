"""Fixed-rule temporal holdout replay; never fit or optimize on the holdout."""

from datetime import date

import numpy as np
import pandas as pd

from app.analysis import METHOD_VERSION, score_sectors

VALIDATION_VERSION = "holdout-replay-v1"


def validate_history(prices: pd.DataFrame, end: date, mode: str) -> dict:
    prices = prices.loc[prices.index <= pd.Timestamp(end)]
    base = {
        "version": VALIDATION_VERSION,
        "method_version": METHOD_VERSION,
        "kind": "synthetic mechanics check"
        if mode == "demo"
        else "retrospective temporal holdout",
        "parameters": {
            "reserved_prefix_fraction": 0.6,
            "holding_sessions": 20,
            "signal_spacing": 21,
            "top_n": 3,
            "round_trip_cost_bps": 20,
        },
        "limitations": [
            "No parameter tuning or training occurs. First 60% of sessions are reserved; only the final 40% is evaluated.",
            "Signals use only prices through signal close. Entry is next observed close, exit 20 sessions after entry.",
            "20 bps round-trip cost charged each period to both sector basket and SPY; illustrative, not calibrated.",
            "Revised adjusted prices, changing sector definitions, and provider gaps prevent certified point-in-time claims.",
            "This is retrospective, not a prospective untouched test. No significance or predictive-edge claim.",
        ],
    }
    if "SPY" not in prices:
        return {
            **base,
            "status": "insufficient_data",
            "reason": "Missing benchmark",
            "folds": [],
        }
    spy = prices["SPY"].dropna()
    start = max(252, int(len(spy) * 0.6))
    folds, skipped = [], []
    if len(spy) < 504:
        return {
            **base,
            "status": "insufficient_data",
            "reason": "Need at least 504 benchmark observations",
            "folds": [],
        }
    for i in range(start, len(spy) - 21, 21):
        signal, entry, exit_day = spy.index[i], spy.index[i + 1], spy.index[i + 21]
        try:
            result = score_sectors(prices.loc[:signal], {}, signal.date())
        except ValueError:
            skipped.append(
                {
                    "signal_date": signal.date().isoformat(),
                    "reason": "Invalid signal inputs",
                }
            )
            continue
        if result["ranking_status"] != "ranked":
            skipped.append(
                {
                    "signal_date": signal.date().isoformat(),
                    "reason": "Insufficient signal coverage",
                }
            )
            continue
        selected = [row["ticker"] for row in result["ranking"][:3]]
        # Never replace selected sectors based on future data availability.
        path = prices.reindex(spy.loc[entry:exit_day].index)[selected + ["SPY"]]
        if (
            path.isna().any().any()
            or (path <= 0).any().any()
            or not np.isfinite(path.to_numpy()).all()
        ):
            skipped.append(
                {
                    "signal_date": signal.date().isoformat(),
                    "reason": "Selected holding-period data incomplete; no substitution",
                }
            )
            continue
        basket = (
            float((path[selected].iloc[-1] / path[selected].iloc[0] - 1).mean()) - 0.002
        )
        benchmark = float(path["SPY"].iloc[-1] / path["SPY"].iloc[0] - 1) - 0.002
        folds.append(
            {
                "signal_date": signal.date().isoformat(),
                "entry_date": entry.date().isoformat(),
                "exit_date": exit_day.date().isoformat(),
                "selected": selected,
                "basket_return_pct": round(100 * basket, 4),
                "benchmark_return_pct": round(100 * benchmark, 4),
                "excess_return_pp": round(100 * (basket - benchmark), 4),
            }
        )
    sufficient = len(folds) >= 6 and len(skipped) <= len(folds)
    return {
        **base,
        "status": "complete" if sufficient else "insufficient_data",
        "reason": "Fixed rule replay only; see limitations"
        if sufficient
        else "Need at least 6 evaluable periods and no more skipped than evaluated periods",
        "reserved_through": spy.index[start - 1].date().isoformat(),
        "folds": folds,
        "skipped": skipped,
        "summary": {
            "periods": len(folds),
            "skipped": len(skipped),
            "mean_excess_pp": round(
                float(np.mean([f["excess_return_pp"] for f in folds])), 4
            )
            if sufficient
            else None,
            "outperformance_fraction": sum(f["excess_return_pp"] > 0 for f in folds)
            / len(folds)
            if sufficient
            else None,
        },
    }
