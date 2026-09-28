"""SQLite journal: immutable calculation inputs/results and durable job states."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ACTIVE = ("queued", "running")


def now() -> str:
    return datetime.now(UTC).isoformat()


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, dedupe_key TEXT NOT NULL, kind TEXT NOT NULL,
                    params TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    error_code TEXT, error_message TEXT, run_id TEXT, snapshot_id TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS jobs_active ON jobs(dedupe_key)
                    WHERE state IN ('queued','running');
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, sha256 TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    created_at TEXT NOT NULL, mode TEXT NOT NULL, as_of_date TEXT NOT NULL,
                    status TEXT NOT NULL, method_version TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS explanations (
                    run_id TEXT PRIMARY KEY REFERENCES runs(id), created_at TEXT NOT NULL,
                    model TEXT NOT NULL, prompt_version TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL, payload TEXT NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, kind: str, params: dict) -> tuple[dict, bool]:
        key = hashlib.sha256(encode([kind, params]).encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM jobs WHERE dedupe_key=? AND state IN ('queued','running')",
                (key,),
            ).fetchone()
            if row:
                return self.job_dict(row), True
            if (
                db.execute(
                    "SELECT count(*) FROM jobs WHERE state IN ('queued','running')"
                ).fetchone()[0]
                >= 4
            ):
                raise ValueError("queue_full")
            job_id, timestamp = uuid.uuid4().hex, now()
            db.execute(
                "INSERT INTO jobs (id,dedupe_key,kind,params,state,stage,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    key,
                    kind,
                    encode(params),
                    "queued",
                    "Waiting for worker",
                    timestamp,
                    timestamp,
                ),
            )
        return self.job(job_id), False

    @staticmethod
    def job_dict(row) -> dict:
        result = dict(row)
        result["params"] = json.loads(result["params"])
        result.pop("dedupe_key", None)
        return result

    def job(self, job_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            return self.job_dict(row)

    def jobs(self, limit: int = 30) -> list[dict]:
        with self.connect() as db:
            return [
                self.job_dict(row)
                for row in db.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            ]

    def update_job(
        self,
        job_id: str,
        state: str,
        stage: str,
        code: str | None = None,
        message: str | None = None,
    ):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET state=?,stage=?,updated_at=?,error_code=?,error_message=? WHERE id=?",
                (state, stage, now(), code, message, job_id),
            )

    def recover(self):
        with self.connect() as db:
            db.execute(
                "UPDATE jobs SET state='interrupted',stage='Interrupted',error_code='server_restart',error_message='Server restarted before completion. Retry explicitly.',updated_at=? WHERE state IN ('queued','running')",
                (now(),),
            )

    def snapshot(self, payload: dict, job_id: str) -> str:
        snapshot_id, content = uuid.uuid4().hex, encode(payload)
        with self.connect() as db:
            db.execute(
                "INSERT INTO snapshots VALUES (?,?,?,?)",
                (
                    snapshot_id,
                    now(),
                    hashlib.sha256(content.encode()).hexdigest(),
                    content,
                ),
            )
            db.execute(
                "UPDATE jobs SET snapshot_id=? WHERE id=?", (snapshot_id, job_id)
            )
        return snapshot_id

    def read_snapshot(self, snapshot_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM snapshots WHERE id=?", (snapshot_id,)
            ).fetchone()
            if not row:
                raise KeyError(snapshot_id)
            return {**dict(row), "payload": json.loads(row["payload"])}

    def save_run(self, job_id: str, snapshot_id: str, payload: dict) -> str:
        run_id, timestamp = uuid.uuid4().hex, now()
        payload = {
            **payload,
            "id": run_id,
            "snapshot_id": snapshot_id,
            "updated_at": timestamp,
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    snapshot_id,
                    timestamp,
                    payload["mode"],
                    payload["as_of_date"],
                    payload["status"],
                    payload["method_version"],
                    encode(payload),
                ),
            )
            db.execute(
                "UPDATE jobs SET state='succeeded',stage='Saved',updated_at=?,run_id=? WHERE id=?",
                (timestamp, run_id, job_id),
            )
        return run_id

    def run(self, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM runs WHERE id=?", (run_id,)
            ).fetchone()
            if not row:
                raise KeyError(run_id)
            return json.loads(row[0])

    def runs(
        self, mode: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        with self.connect() as db:
            query = "SELECT id,snapshot_id,created_at,mode,as_of_date,status,method_version FROM runs"
            args: list[Any] = []
            if mode:
                query += " WHERE mode=?"
                args.append(mode)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            return [dict(row) for row in db.execute(query, [*args, limit, offset])]

    def save_explanation(
        self,
        job_id: str,
        run_id: str,
        model: str,
        prompt_version: str,
        input_hash: str,
        result: dict,
    ):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO explanations VALUES (?,?,?,?,?,?)",
                (run_id, now(), model, prompt_version, input_hash, encode(result)),
            )
            db.execute(
                "UPDATE jobs SET state='succeeded',stage='Explanation saved',run_id=?,updated_at=? WHERE id=?",
                (run_id, now(), job_id),
            )

    def explanation(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM explanations WHERE run_id=?", (run_id,)
            ).fetchone()
            return {**dict(row), "payload": json.loads(row["payload"])} if row else None
