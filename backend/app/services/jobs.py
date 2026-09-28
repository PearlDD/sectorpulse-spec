"""One durable worker per database. Subprocess isolation enforces a wall timeout."""

import fcntl
import logging
import multiprocessing
import os
import threading
from datetime import date
from pathlib import Path
from typing import TextIO

from app.analysis import METHOD_VERSION, score_sectors
from app.data.demo import demo_macro, demo_prices
from app.data.fetcher import fetch_macro_indicators, fetch_sector_prices
from app.data.snapshot import macro_payload, make_snapshot, restore
from app.db.store import Store
from app.services import explanation
from app.validation import validate_history

logger = logging.getLogger(__name__)


def calculate(snapshot: dict) -> dict:
    prices, macro = restore(snapshot)
    end = date.fromisoformat(snapshot["as_of_date"])
    result = score_sectors(prices, macro, end)
    result.update(
        mode=snapshot["mode"],
        as_of_date=snapshot["as_of_date"],
        source="Synthetic demonstration data"
        if snapshot["mode"] == "demo"
        else "Yahoo adjusted prices; FRED vintage macro",
        macro=macro_payload(snapshot),
        prices={
            ticker: [
                {"date": p["date"], "close": p["value"]}
                for p in points
                if p["date"] >= result["window_start"]
            ]
            for ticker, points in snapshot["prices"].items()
        },
        validation=validate_history(prices, end, snapshot["mode"]),
        limitations=[
            "Educational research, not investment advice or a forecast.",
            "Yahoo adjusted history may be revised; not a certified point-in-time backtest.",
            "SPY observed sessions are used; a licensed exchange calendar is not integrated.",
            "AI explanations are optional, unverified prose and never change calculations.",
        ],
    )
    result["status"] = (
        "partial"
        if result["excluded"] or result["macro"]["status"] != "available"
        else "available"
    )
    return result


def execute_job(db_path: str, job_id: str):
    """Entrypoint for spawned worker; never log raw provider exceptions."""
    store = Store(db_path)
    job = store.job(job_id)
    params = job["params"]
    try:
        if job["kind"] == "explanation":
            store.update_job(job_id, "running", "Generating optional explanation")
            run = store.run(params["run_id"])
            digest, result = explanation.generate(run)
            store.save_explanation(
                job_id,
                params["run_id"],
                explanation.MODEL,
                explanation.PROMPT_VERSION,
                digest,
                result,
            )
            return
        end, mode = date.fromisoformat(params["as_of_date"]), params["mode"]
        store.update_job(job_id, "running", "Fetching prices")
        prices = (
            demo_prices(end)
            if mode == "demo"
            else fetch_sector_prices(end, lookback_days=1400)
        )
        store.update_job(job_id, "running", "Fetching macro vintage")
        macro = demo_macro(end) if mode == "demo" else fetch_macro_indicators(end)
        snapshot = make_snapshot(
            prices, macro, end, mode, bool(os.getenv("FRED_API_KEY", "").strip())
        )
        snapshot["requested_method_version"] = METHOD_VERSION
        snapshot_id = store.snapshot(snapshot, job_id)
        store.update_job(
            job_id, "running", "Computing strength, risk and holdout replay"
        )
        result = calculate(snapshot)
        store.save_run(job_id, snapshot_id, result)
    except Exception as exc:  # noqa: BLE001 - provider/AI errors can contain secrets
        logger.warning("Job %s failed (%s)", job_id, type(exc).__name__)
        code = "analysis_failed" if job["kind"] == "analysis" else "explanation_failed"
        message = (
            "Provider or input validation failed. Previous saved runs are unchanged."
            if job["kind"] == "analysis"
            else "AI provider unavailable or response invalid. Deterministic report is unchanged."
        )
        store.update_job(job_id, "failed", "Failed", code, message)


class JobRunner:
    def __init__(self, store: Store, timeout_seconds: float = 900):
        self.store, self.timeout = store, timeout_seconds
        self.stop = threading.Event()
        self.lock_file: TextIO | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        # Enforce documented single-process deployment; another process cannot mark our jobs interrupted.
        lock = open(Path(self.store.path).with_suffix(".worker.lock"), "a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            raise RuntimeError(
                "Only one SectorPulse server worker may use this database"
            ) from None
        self.lock_file = lock
        self.store.recover()
        self.thread = threading.Thread(
            target=self.loop, daemon=True, name="sectorpulse-dispatcher"
        )
        self.thread.start()

    def loop(self):
        while not self.stop.wait(0.2):
            queued = [
                job for job in reversed(self.store.jobs()) if job["state"] == "queued"
            ]
            if not queued:
                continue
            job = queued[0]
            self.store.update_job(job["id"], "running", "Starting worker")
            worker = multiprocessing.get_context("spawn").Process(
                target=execute_job, args=(self.store.path, job["id"]), daemon=True
            )
            try:
                worker.start()
                import time

                deadline = time.monotonic() + (
                    min(self.timeout, 90)
                    if job["kind"] == "explanation"
                    else self.timeout
                )
                while (
                    worker.is_alive()
                    and not self.stop.is_set()
                    and time.monotonic() < deadline
                ):
                    worker.join(0.2)
                if worker.is_alive():
                    worker.terminate()
                    worker.join(3)
                    if worker.is_alive():
                        worker.kill()
                        worker.join()
                    state = "interrupted" if self.stop.is_set() else "timed_out"
                    if self.store.job(job["id"])["state"] != "succeeded":
                        self.store.update_job(
                            job["id"],
                            state,
                            state,
                            state,
                            "Task stopped. Previous saved reports remain available; retry explicitly.",
                        )
                elif self.store.job(job["id"])["state"] == "running":
                    self.store.update_job(
                        job["id"],
                        "failed",
                        "Worker exited",
                        "worker_exit",
                        "Worker exited unexpectedly. Retry explicitly.",
                    )
            except Exception:  # noqa: BLE001 - isolate dispatcher failures, preserve service
                logger.warning("Unable to launch worker for job %s", job["id"])
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
                self.store.update_job(
                    job["id"],
                    "failed",
                    "Worker launch failed",
                    "worker_start",
                    "Could not start background worker.",
                )

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(10)
        if self.lock_file:
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
