#!/usr/bin/env python3
"""Task 6 baseline: generate explanation text for meme events."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def pick_summary(
    source_status: str,
    canonical: str,
    source_platform: str | None,
    first_seen_time: str | None,
    templates: dict[str, str],
) -> tuple[str | None, str, str | None]:
    if source_status == "probable":
        summary = templates.get(
            "probable",
            "系统根据多平台证据判断，{name} 近期集中传播，疑似最早来源于 {platform}（{time}）。",
        ).format(
            name=canonical,
            platform=source_platform or "未知平台",
            time=first_seen_time or "未知时间",
        )
        return summary, "generated", None

    if source_status == "uncertain":
        summary = templates.get(
            "uncertain",
            "系统检测到 {name} 存在传播趋势，但来源证据存在冲突，当前仅可判定为不确定。",
        ).format(name=canonical)
        return summary, "generated", "来源候选分数接近或证据冲突，建议人工复核"

    summary = templates.get(
        "insufficient_evidence",
        "{name} 已被识别为候选表达，但当前证据不足，暂无法给出可靠来源解释。",
    ).format(name=canonical)
    return summary, "insufficient_context", "解释不足：来源不确定，待人工确认"


def calc_heat_score(hotword_item: dict[str, Any] | None, fallback: float = 0.2) -> float:
    if not hotword_item:
        return fallback
    final_score = safe_float(hotword_item.get("scores", {}).get("final"), fallback)
    return round(max(0.0, min(1.0, final_score)), 4)


def calc_confidence(source_status: str, source_confidence: float | None) -> float:
    sc = safe_float(source_confidence, 0.0)
    if source_status == "probable":
        return round(max(0.0, min(1.0, sc)), 4)
    if source_status == "uncertain":
        return round(max(0.3, min(0.6, sc if sc > 0 else 0.45)), 4)
    return 0.35


def build_trend_snapshot(event_id: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    platform_counts = Counter([str(e.get("platform", "unknown")) for e in evidence if e.get("platform")])
    total = max(1, sum(platform_counts.values()))
    breakdown = {k: round(v / total, 4) for k, v in platform_counts.items()}

    latest_time = None
    for item in evidence:
        t = item.get("post_time")
        if t and (latest_time is None or t > latest_time):
            latest_time = t

    return {
        "id": f"snap_{event_id.split('_')[-1]}",
        "event_id": event_id,
        "snapshot_time": latest_time,
        "heat_value": round(min(1.0, 0.25 + 0.15 * len(evidence)), 4),
        "platform_breakdown": breakdown,
        "sample_count": len(evidence),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate explanation text from attribution results")
    parser.add_argument("--hotwords", required=True, help="Path to Task 3 hotword output")
    parser.add_argument("--clusters", required=True, help="Path to Task 4 cluster output")
    parser.add_argument("--attribute", required=True, help="Path to Task 5 attribution output")
    parser.add_argument("--output", required=True, help="Path to Task 6 summary output")
    parser.add_argument(
        "--config",
        default="ai/config/explanation_templates.json",
        help="Path to explanation template config",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    hotword_data = load_json(Path(args.hotwords))
    cluster_data = load_json(Path(args.clusters))
    attr_data = load_json(Path(args.attribute))
    config = load_json(Path(args.config))

    hotword_map = {
        str(item.get("term", "")): item
        for item in (hotword_data.get("hotwords", []) if isinstance(hotword_data, dict) else [])
    }
    cluster_map = {
        str(item.get("canonical_term", "")): item
        for item in (cluster_data.get("clusters", []) if isinstance(cluster_data, dict) else [])
    }

    evidence_all = attr_data.get("evidence", []) if isinstance(attr_data, dict) else []
    events_attr = attr_data.get("events", []) if isinstance(attr_data, dict) else []

    events_out: list[dict[str, Any]] = []
    trend_snapshots: list[dict[str, Any]] = []

    for event_item in events_attr:
        event_id = str(event_item.get("event_id", ""))
        canonical = str(event_item.get("canonical_term", ""))
        source_status = str(event_item.get("source_status", "insufficient_evidence"))
        source_platform = event_item.get("source_platform")
        source_confidence = event_item.get("source_confidence")
        first_seen_time = event_item.get("first_seen_time")

        summary, explanation_status, default_note = pick_summary(
            source_status,
            canonical,
            source_platform,
            first_seen_time,
            config.get("templates", {}),
        )

        cluster_item = cluster_map.get(canonical, {})
        aliases = cluster_item.get("member_terms", [canonical]) if isinstance(cluster_item, dict) else [canonical]
        aliases = aliases if isinstance(aliases, list) and aliases else [canonical]
        if canonical not in aliases:
            aliases = [canonical] + aliases

        hotword_item = hotword_map.get(canonical)
        keyword_signals = []
        if hotword_item:
            keyword_signals.append(
                {
                    "term": canonical,
                    "frequency": int(hotword_item.get("frequency", 0)),
                    "burst_score": safe_float(hotword_item.get("scores", {}).get("burst"), 0.0),
                }
            )

        confidence = calc_confidence(source_status, source_confidence)
        heat_score = calc_heat_score(hotword_item)

        status = "complete"
        if source_status == "uncertain":
            status = "partial"
        if source_status == "insufficient_evidence":
            status = "needs_review"

        notes = event_item.get("notes") or default_note
        related_evidence = [e for e in evidence_all if str(e.get("event_id", "")) == event_id]
        trend_snapshots.append(build_trend_snapshot(event_id, related_evidence))

        events_out.append(
            {
                "id": event_id,
                "name": canonical,
                "aliases": aliases,
                "summary": summary,
                "status": status,
                "heat_score": heat_score,
                "confidence": confidence,
                "first_seen_time": first_seen_time,
                "source_platform": source_platform,
                "source_confidence": source_confidence,
                "source_status": source_status,
                "representative_evidence_id": event_item.get("representative_evidence_id"),
                "keyword_signals": keyword_signals,
                "explanation_status": explanation_status,
                "notes": notes,
            }
        )

    output = {
        "run_stage": "summarize",
        "config_version": config.get("rule_version", "v0.1"),
        "input_stage": {
            "hotword": hotword_data.get("run_stage", "unknown") if isinstance(hotword_data, dict) else "unknown",
            "cluster": cluster_data.get("run_stage", "unknown") if isinstance(cluster_data, dict) else "unknown",
            "attribute": attr_data.get("run_stage", "unknown") if isinstance(attr_data, dict) else "unknown",
        },
        "events": events_out,
        "evidence": evidence_all,
        "trend_snapshots": trend_snapshots,
        "stats": {
            "event_count": len(events_out),
            "generated_explanation_count": sum(1 for e in events_out if e.get("explanation_status") == "generated"),
            "degraded_explanation_count": sum(1 for e in events_out if e.get("explanation_status") != "generated"),
        },
    }

    dump_json(Path(args.output), output)


if __name__ == "__main__":
    main()
