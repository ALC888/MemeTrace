from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .sample_data import DEMO_ANALYSIS_RUN
from .schemas import (
    EvidenceItem,
    HotEventDetail,
    HotEventListItem,
    TimelineNode,
    TrendSnapshotItem,
)
from .settings import PIPELINE_FINAL_OUTPUT, PIPELINE_OUT_DIR, REPO_ROOT
from .storage import (
    decode_json,
    event_count,
    get_connection,
    import_analysis_run,
    init_db,
    load_json_file,
)


def bootstrap_data() -> None:
    init_db()
    if event_count() == 0:
        import_analysis_run(DEMO_ANALYSIS_RUN)


def row_to_event_item(row: Any) -> HotEventListItem:
    return HotEventListItem(
        id=row["id"],
        name=row["name"],
        aliases=decode_json(row["aliases_json"], []),
        summary=row["summary"],
        heat_score=float(row["heat_score"] or 0),
        confidence=row["confidence"],
        first_seen_time=row["first_seen_time"],
        source_platform=row["source_platform"],
        status=row["status"],
        evidence_count=int(row["evidence_count"] or 0),
    )


def row_to_evidence(row: Any) -> EvidenceItem:
    return EvidenceItem(
        id=row["id"],
        event_id=row["event_id"],
        raw_post_id=row["raw_post_id"],
        platform=row["platform"],
        snippet=row["snippet"],
        post_time=row["post_time"],
        url=row["url"],
        relevance_score=float(row["relevance_score"] or 0),
        source_score=float(row["source_score"] or 0),
        is_source_candidate=bool(row["is_source_candidate"]),
        evidence_type=row["evidence_type"],
    )


def row_to_snapshot(row: Any) -> TrendSnapshotItem:
    return TrendSnapshotItem(
        id=row["id"],
        event_id=row["event_id"],
        snapshot_time=row["snapshot_time"],
        heat_value=float(row["heat_value"] or 0),
        platform_breakdown=decode_json(row["platform_breakdown_json"], {}),
        sample_count=int(row["sample_count"] or 0),
    )


def list_hot_events(limit: int = 20, offset: int = 0) -> tuple[list[HotEventListItem], int]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    with get_connection() as conn:
        total = int(conn.execute("SELECT COUNT(*) AS c FROM meme_events").fetchone()["c"])
        rows = conn.execute(
            """
            SELECT e.*, COUNT(v.id) AS evidence_count
            FROM meme_events e
            LEFT JOIN evidence v ON v.event_id = e.id
            GROUP BY e.id
            ORDER BY e.heat_score DESC, e.first_seen_time ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [row_to_event_item(row) for row in rows], total


def get_hot_event(event_id: str) -> HotEventDetail:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT e.*, COUNT(v.id) AS evidence_count
            FROM meme_events e
            LEFT JOIN evidence v ON v.event_id = e.id
            WHERE e.id = ?
            GROUP BY e.id
            """,
            (event_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="hot event not found")

        evidence_rows = conn.execute(
            "SELECT * FROM evidence WHERE event_id = ? ORDER BY post_time ASC, source_score DESC",
            (event_id,),
        ).fetchall()
        snapshot_row = conn.execute(
            """
            SELECT * FROM trend_snapshots
            WHERE event_id = ?
            ORDER BY snapshot_time DESC
            LIMIT 1
            """,
            (event_id,),
        ).fetchone()

    base = row_to_event_item(row)
    return HotEventDetail(
        **base.model_dump(),
        source_confidence=row["source_confidence"],
        source_status=row["source_status"],
        representative_evidence_id=row["representative_evidence_id"],
        keyword_signals=decode_json(row["keyword_signals_json"], []),
        explanation_status=row["explanation_status"],
        notes=row["notes"],
        evidence=[row_to_evidence(item) for item in evidence_rows],
        latest_snapshot=row_to_snapshot(snapshot_row) if snapshot_row else None,
    )


def get_timeline(event_id: str) -> tuple[list[TimelineNode], list[TrendSnapshotItem]]:
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM meme_events WHERE id = ?", (event_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="hot event not found")

        evidence_rows = conn.execute(
            "SELECT * FROM evidence WHERE event_id = ? ORDER BY post_time ASC, source_score DESC",
            (event_id,),
        ).fetchall()
        snapshot_rows = conn.execute(
            "SELECT * FROM trend_snapshots WHERE event_id = ? ORDER BY snapshot_time ASC",
            (event_id,),
        ).fetchall()

    nodes = [
        TimelineNode(
            id=row["id"],
            event_id=row["event_id"],
            platform=row["platform"],
            time=row["post_time"],
            title="疑似源头" if row["evidence_type"] == "timeline_anchor" else "传播证据",
            snippet=row["snippet"],
            url=row["url"],
            source_score=float(row["source_score"] or 0),
            node_type=row["evidence_type"] or "evidence",
        )
        for row in evidence_rows
    ]
    return nodes, [row_to_snapshot(row) for row in snapshot_rows]


def search_events(q: str, limit: int = 20) -> list[HotEventListItem]:
    needle = q.strip()
    if not needle:
        return []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT e.*, COUNT(v.id) AS evidence_count
            FROM meme_events e
            LEFT JOIN evidence v ON v.event_id = e.id
            WHERE e.name LIKE ?
               OR e.aliases_json LIKE ?
               OR e.summary LIKE ?
            GROUP BY e.id
            ORDER BY e.heat_score DESC
            LIMIT ?
            """,
            (f"%{needle}%", f"%{needle}%", f"%{needle}%", max(1, min(limit, 50))),
        ).fetchall()
    return [row_to_event_item(row) for row in rows]


def reset_demo_data() -> int:
    return import_analysis_run(DEMO_ANALYSIS_RUN)


def resolve_repo_path(path_value: str) -> Path:
    raw = Path(path_value)
    path = raw if raw.is_absolute() else REPO_ROOT / raw
    resolved = path.resolve()
    repo_root = REPO_ROOT.resolve()
    if repo_root not in resolved.parents and resolved != repo_root:
        raise HTTPException(status_code=400, detail="path must stay inside repository")
    return resolved


def run_ai_pipeline(input_path: str, final_output_path: str | None = None) -> tuple[int, Path]:
    source = resolve_repo_path(input_path)
    if not source.exists():
        raise HTTPException(status_code=400, detail=f"input_path does not exist: {input_path}")

    output = resolve_repo_path(final_output_path) if final_output_path else PIPELINE_FINAL_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "ai" / "pipeline" / "run_full_pipeline.py"),
        "--input",
        str(source),
        "--out-dir",
        str(PIPELINE_OUT_DIR),
        "--final-output",
        str(output),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "AI pipeline failed"
        raise HTTPException(status_code=500, detail=detail)

    count = import_analysis_run(load_json_file(output))
    return count, output
