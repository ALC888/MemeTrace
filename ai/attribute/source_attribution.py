#!/usr/bin/env python3
"""Task 5 baseline: source attribution scoring for meme events."""

from __future__ import annotations

import argparse
import json
import math
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


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    return datetime.fromisoformat(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_interaction(metrics: dict[str, Any]) -> float:
    like_count = safe_float(metrics.get("like_count"), 0.0)
    comment_count = safe_float(metrics.get("comment_count"), 0.0)
    share_count = safe_float(metrics.get("share_count"), 0.0)
    view_count = safe_float(metrics.get("view_count"), 0.0)

    # Log scaling keeps high-volume items bounded for stable scoring.
    raw = like_count + 2.0 * comment_count + 3.0 * share_count + 0.02 * view_count
    return max(0.0, min(1.0, math.log1p(raw) / 8.0))


def term_relevance_score(post: dict[str, Any], cluster_terms: set[str]) -> float:
    text = str(post.get("normalized_content", ""))
    if not text:
        return 0.0

    matches = 0
    for term in cluster_terms:
        if term and term in text:
            matches += 1

    if not cluster_terms:
        return 0.0
    ratio = matches / len(cluster_terms)
    return max(0.0, min(1.0, ratio))


def time_score(rank_idx: int) -> float:
    # Earliest rank gets full score, lower ranks decay.
    return max(0.0, 1.0 - 0.25 * rank_idx)


def build_event_candidates(
    canonical_term: str,
    post_ids: list[str],
    post_index: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    platform_weight_map = config.get("platform_weights", {})
    weights = config.get(
        "score_weights",
        {"time": 0.45, "platform": 0.2, "relevance": 0.2, "representative": 0.15},
    )

    cluster_terms = {canonical_term}
    posts = [post_index[pid] for pid in post_ids if pid in post_index]
    posts = sorted(posts, key=lambda p: parse_time(p.get("publish_time")))

    candidates: list[dict[str, Any]] = []
    for idx, post in enumerate(posts):
        platform = str(post.get("platform", ""))
        metrics = post.get("metrics", {}) if isinstance(post.get("metrics", {}), dict) else {}

        t_score = time_score(idx)
        p_score = safe_float(platform_weight_map.get(platform, 0.8), 0.8)
        r_score = term_relevance_score(post, cluster_terms)
        rep_score = normalize_interaction(metrics)

        final_score = (
            safe_float(weights.get("time", 0.45)) * t_score
            + safe_float(weights.get("platform", 0.2)) * p_score
            + safe_float(weights.get("relevance", 0.2)) * r_score
            + safe_float(weights.get("representative", 0.15)) * rep_score
        )

        candidates.append(
            {
                "raw_post_id": str(post.get("id", "")),
                "platform": platform,
                "post_time": post.get("publish_time"),
                "score": round(final_score, 4),
                "score_breakdown": {
                    "time": round(t_score, 4),
                    "platform": round(p_score, 4),
                    "relevance": round(r_score, 4),
                    "representative": round(rep_score, 4),
                },
                "snippet": str(post.get("normalized_content", ""))[:80],
                "url": post.get("url"),
            }
        )

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def make_source_status(
    best_score: float,
    candidate_count: int,
    config: dict[str, Any],
) -> tuple[str, str | None, float | None]:
    probable_threshold = safe_float(config.get("probable_threshold", 0.7), 0.7)
    uncertain_threshold = safe_float(config.get("uncertain_threshold", 0.5), 0.5)
    min_candidates = int(config.get("min_candidates", 2))

    if candidate_count < min_candidates:
        return "insufficient_evidence", "候选证据不足，未达到最小候选数", None

    if best_score >= probable_threshold:
        return "probable", None, round(best_score, 4)

    if best_score >= uncertain_threshold:
        return "uncertain", "分值中等，建议人工复核", round(best_score, 4)

    return "insufficient_evidence", "最高分低于不确定阈值", None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Source attribution scoring for clustered meme events")
    parser.add_argument("--normalized", required=True, help="Path to Task 2 normalized output")
    parser.add_argument("--clusters", required=True, help="Path to Task 4 cluster output")
    parser.add_argument("--output", required=True, help="Path to Task 5 attribution output")
    parser.add_argument(
        "--config",
        default="ai/config/source_attribution.json",
        help="Path to source attribution config",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    normalized_data = load_json(Path(args.normalized))
    cluster_data = load_json(Path(args.clusters))
    config = load_json(Path(args.config))

    posts = normalized_data.get("posts", []) if isinstance(normalized_data, dict) else []
    links = cluster_data.get("post_cluster_links", []) if isinstance(cluster_data, dict) else []
    clusters = cluster_data.get("clusters", []) if isinstance(cluster_data, dict) else []

    post_index = {str(p.get("id", "")): p for p in posts}

    term_to_posts: dict[str, list[str]] = {}
    for link in links:
        post_id = str(link.get("post_id", ""))
        for term in link.get("cluster_terms", []) or []:
            term_to_posts.setdefault(str(term), []).append(post_id)

    event_results: list[dict[str, Any]] = []
    evidence_results: list[dict[str, Any]] = []

    for idx, cluster in enumerate(clusters, start=1):
        canonical = str(cluster.get("canonical_term", ""))
        event_id = f"event_{idx:04d}"

        post_ids = term_to_posts.get(canonical, [])
        candidates = build_event_candidates(canonical, post_ids, post_index, config)

        best = candidates[0] if candidates else None
        best_score = safe_float(best.get("score"), 0.0) if best else 0.0
        source_status, notes, source_confidence = make_source_status(best_score, len(candidates), config)

        source_platform = best.get("platform") if best and source_status != "insufficient_evidence" else None
        first_seen_time = None
        if post_ids:
            first_seen_time = min(
                (post_index[pid].get("publish_time") for pid in post_ids if pid in post_index),
                default=None,
            )

        representative_evidence_id = None
        for rank, cand in enumerate(candidates, start=1):
            evidence_id = f"evi_{idx:04d}_{rank:02d}"
            if rank == 1:
                representative_evidence_id = evidence_id

            evidence_results.append(
                {
                    "id": evidence_id,
                    "event_id": event_id,
                    "raw_post_id": cand.get("raw_post_id"),
                    "platform": cand.get("platform"),
                    "snippet": cand.get("snippet"),
                    "post_time": cand.get("post_time"),
                    "url": cand.get("url"),
                    "relevance_score": cand.get("score_breakdown", {}).get("relevance", 0.0),
                    "source_score": cand.get("score", 0.0),
                    "is_source_candidate": rank <= int(config.get("top_source_candidates", 3)),
                    "evidence_type": "timeline_anchor" if rank == 1 else "text_match",
                }
            )

        candidate_sources = [
            {
                "raw_post_id": c.get("raw_post_id"),
                "platform": c.get("platform"),
                "post_time": c.get("post_time"),
                "score": c.get("score"),
                "score_breakdown": c.get("score_breakdown"),
            }
            for c in candidates[: int(config.get("top_source_candidates", 3))]
        ]

        event_results.append(
            {
                "event_id": event_id,
                "canonical_term": canonical,
                "source_status": source_status,
                "source_platform": source_platform,
                "source_confidence": source_confidence,
                "first_seen_time": first_seen_time,
                "representative_evidence_id": representative_evidence_id,
                "candidate_sources": candidate_sources,
                "notes": notes,
            }
        )

    output = {
        "run_stage": "attribute",
        "config_version": config.get("rule_version", "v0.1"),
        "input_stage": {
            "normalized": normalized_data.get("run_stage", "unknown") if isinstance(normalized_data, dict) else "unknown",
            "cluster": cluster_data.get("run_stage", "unknown") if isinstance(cluster_data, dict) else "unknown",
        },
        "events": event_results,
        "evidence": evidence_results,
        "stats": {
            "event_count": len(event_results),
            "evidence_count": len(evidence_results),
            "probable_count": sum(1 for e in event_results if e.get("source_status") == "probable"),
            "uncertain_count": sum(1 for e in event_results if e.get("source_status") == "uncertain"),
            "insufficient_count": sum(1 for e in event_results if e.get("source_status") == "insufficient_evidence"),
        },
    }

    dump_json(Path(args.output), output)


if __name__ == "__main__":
    main()
