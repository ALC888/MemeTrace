from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .settings import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def encode_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def decode_json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meme_events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                aliases_json TEXT NOT NULL,
                summary TEXT,
                heat_score REAL NOT NULL DEFAULT 0,
                confidence REAL,
                first_seen_time TEXT,
                source_platform TEXT,
                status TEXT NOT NULL DEFAULT 'needs_review',
                source_confidence REAL,
                source_status TEXT,
                representative_evidence_id TEXT,
                keyword_signals_json TEXT NOT NULL,
                explanation_status TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                raw_post_id TEXT,
                platform TEXT,
                snippet TEXT,
                post_time TEXT,
                url TEXT,
                relevance_score REAL NOT NULL DEFAULT 0,
                source_score REAL NOT NULL DEFAULT 0,
                is_source_candidate INTEGER NOT NULL DEFAULT 0,
                evidence_type TEXT,
                FOREIGN KEY(event_id) REFERENCES meme_events(id)
            );

            CREATE TABLE IF NOT EXISTS trend_snapshots (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                snapshot_time TEXT,
                heat_value REAL NOT NULL DEFAULT 0,
                platform_breakdown_json TEXT NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(event_id) REFERENCES meme_events(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_runs (
                run_id TEXT PRIMARY KEY,
                generated_at TEXT,
                source_batch_json TEXT NOT NULL,
                stats_json TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );
            """
        )


def event_count() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM meme_events").fetchone()
        return int(row["c"])


def clear_analysis_data(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM trend_snapshots")
    conn.execute("DELETE FROM evidence")
    conn.execute("DELETE FROM meme_events")
    conn.execute("DELETE FROM analysis_runs")


def import_analysis_run(data: dict[str, Any]) -> int:
    events = data.get("events", []) if isinstance(data, dict) else []
    evidence = data.get("evidence", []) if isinstance(data, dict) else []
    snapshots = data.get("trend_snapshots", []) if isinstance(data, dict) else []

    with get_connection() as conn:
        clear_analysis_data(conn)

        conn.execute(
            """
            INSERT INTO analysis_runs (run_id, generated_at, source_batch_json, stats_json, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(data.get("run_id", "run_unknown")),
                data.get("generated_at"),
                encode_json(data.get("source_batch", {})),
                encode_json(data.get("stats", {})),
                encode_json(data),
            ),
        )

        for item in events:
            conn.execute(
                """
                INSERT INTO meme_events (
                    id, name, aliases_json, summary, heat_score, confidence,
                    first_seen_time, source_platform, status, source_confidence,
                    source_status, representative_evidence_id, keyword_signals_json,
                    explanation_status, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(item.get("id", "")),
                    str(item.get("name", "")),
                    encode_json(item.get("aliases", [])),
                    item.get("summary"),
                    float(item.get("heat_score") or 0),
                    item.get("confidence"),
                    item.get("first_seen_time"),
                    item.get("source_platform"),
                    item.get("status", "needs_review"),
                    item.get("source_confidence"),
                    item.get("source_status"),
                    item.get("representative_evidence_id"),
                    encode_json(item.get("keyword_signals", [])),
                    item.get("explanation_status"),
                    item.get("notes"),
                ),
            )

        for item in evidence:
            conn.execute(
                """
                INSERT INTO evidence (
                    id, event_id, raw_post_id, platform, snippet, post_time, url,
                    relevance_score, source_score, is_source_candidate, evidence_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(item.get("id", "")),
                    str(item.get("event_id", "")),
                    item.get("raw_post_id"),
                    item.get("platform"),
                    item.get("snippet"),
                    item.get("post_time"),
                    item.get("url"),
                    float(item.get("relevance_score") or 0),
                    float(item.get("source_score") or 0),
                    1 if item.get("is_source_candidate") else 0,
                    item.get("evidence_type"),
                ),
            )

        for item in snapshots:
            conn.execute(
                """
                INSERT INTO trend_snapshots (
                    id, event_id, snapshot_time, heat_value, platform_breakdown_json, sample_count
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(item.get("id", "")),
                    str(item.get("event_id", "")),
                    item.get("snapshot_time"),
                    float(item.get("heat_value") or 0),
                    encode_json(item.get("platform_breakdown", {})),
                    int(item.get("sample_count") or 0),
                ),
            )

        return len(events)


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("analysis-run JSON must be an object")
    return data
