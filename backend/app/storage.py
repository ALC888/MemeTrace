from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .settings import DATA_DIR, DB_PATH

ALLOWED_SOURCE_TYPES = {"mock", "public_sample", "captured_excerpt"}
ALLOWED_EVENT_STATUSES = {"complete", "partial", "needs_review"}
ALLOWED_SOURCE_STATUSES = {"probable", "uncertain", "insufficient_evidence"}


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


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def require_non_empty_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def require_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number")
    return float(value)


def require_number_range(value: Any, path: str) -> float:
    number = require_number(value, path)
    if number < 0 or number > 1:
        raise ValueError(f"{path} must be between 0 and 1")
    return number


def require_optional_number_range(value: Any, path: str) -> None:
    if value is not None:
        require_number_range(value, path)


def validate_analysis_run(data: dict[str, Any]) -> None:
    require_mapping(data, "analysis_run")

    for key in ("events", "evidence", "trend_snapshots", "stats"):
        if key not in data:
            raise ValueError(f"analysis_run.{key} is required")

    events = require_list(data["events"], "analysis_run.events")
    evidence = require_list(data["evidence"], "analysis_run.evidence")
    snapshots = require_list(data["trend_snapshots"], "analysis_run.trend_snapshots")
    require_mapping(data["stats"], "analysis_run.stats")

    source_batch = data.get("source_batch")
    if source_batch is not None:
        source_batch = require_mapping(source_batch, "analysis_run.source_batch")
        source_type = source_batch.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
            raise ValueError(f"analysis_run.source_batch.source_type must be one of: {allowed}")

    event_ids: set[str] = set()
    for idx, raw_event in enumerate(events):
        path = f"analysis_run.events[{idx}]"
        event = require_mapping(raw_event, path)
        event_id = require_non_empty_str(event.get("id"), f"{path}.id")
        if event_id in event_ids:
            raise ValueError(f"{path}.id is duplicated: {event_id}")
        event_ids.add(event_id)

        require_non_empty_str(event.get("name"), f"{path}.name")
        status = require_non_empty_str(event.get("status"), f"{path}.status")
        if status not in ALLOWED_EVENT_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_EVENT_STATUSES))
            raise ValueError(f"{path}.status must be one of: {allowed}")

        require_number_range(event.get("heat_score"), f"{path}.heat_score")
        require_optional_number_range(event.get("confidence"), f"{path}.confidence")
        require_optional_number_range(event.get("source_confidence"), f"{path}.source_confidence")

        source_status = event.get("source_status")
        if source_status is not None and source_status not in ALLOWED_SOURCE_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_SOURCE_STATUSES))
            raise ValueError(f"{path}.source_status must be one of: {allowed}")

    for idx, raw_item in enumerate(evidence):
        path = f"analysis_run.evidence[{idx}]"
        item = require_mapping(raw_item, path)
        require_non_empty_str(item.get("id"), f"{path}.id")
        event_id = require_non_empty_str(item.get("event_id"), f"{path}.event_id")
        if event_id not in event_ids:
            raise ValueError(f"{path}.event_id does not match any event: {event_id}")

        require_optional_number_range(item.get("relevance_score"), f"{path}.relevance_score")
        require_optional_number_range(item.get("source_score"), f"{path}.source_score")

    for idx, raw_item in enumerate(snapshots):
        path = f"analysis_run.trend_snapshots[{idx}]"
        item = require_mapping(raw_item, path)
        require_non_empty_str(item.get("id"), f"{path}.id")
        event_id = require_non_empty_str(item.get("event_id"), f"{path}.event_id")
        if event_id not in event_ids:
            raise ValueError(f"{path}.event_id does not match any event: {event_id}")

        require_optional_number_range(item.get("heat_value"), f"{path}.heat_value")
        platform_breakdown = item.get("platform_breakdown")
        if platform_breakdown is not None:
            platform_breakdown = require_mapping(platform_breakdown, f"{path}.platform_breakdown")
            for platform, value in platform_breakdown.items():
                require_number_range(value, f"{path}.platform_breakdown.{platform}")


def import_analysis_run(data: dict[str, Any]) -> int:
    validate_analysis_run(data)
    init_db()

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
