#!/usr/bin/env python3
"""Task 3 baseline: hotword detection from normalized posts."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
CJK_SEGMENT_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,8}")
HOTWORD_CORE_PATTERN = re.compile(r"[\u4e00-\u9fff]{0,3}梗[\u4e00-\u9fff]{0,3}")


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


def split_chinese_segments(text: str) -> list[str]:
    return CJK_SEGMENT_PATTERN.findall(text or "")


def extract_candidates_from_post(post: dict[str, Any], config: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    max_token_len = int(config.get("max_token_len", 10))

    for tag in (post.get("extra", {}) or {}).get("topic_tags", []):
        if isinstance(tag, str) and tag.strip():
            candidates.append(tag.strip())

    for token in post.get("tokens", []) or []:
        if not isinstance(token, str):
            continue
        t = token.strip()
        if not t:
            continue

        # Keep short direct token for baseline counting.
        if 2 <= len(t) <= max_token_len:
            candidates.append(t)

        # For long phrase tokens, pull concise "*梗*" spans and Chinese segments.
        if len(t) > max_token_len:
            candidates.extend(HOTWORD_CORE_PATTERN.findall(t))
            candidates.extend(split_chinese_segments(t))

    normalized_content = post.get("normalized_content", "")
    candidates.extend(HOTWORD_CORE_PATTERN.findall(normalized_content))

    return [c for c in candidates if CJK_PATTERN.search(c)]


def normalize_term(term: str) -> str:
    return re.sub(r"\s+", "", term.strip().lower())


def build_windows(posts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(posts, key=lambda p: parse_time(p.get("publish_time")))
    split_idx = max(1, math.ceil(len(ordered) / 2))
    return ordered[:split_idx], ordered[split_idx:]


def score_candidates(
    posts: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    denylist = {normalize_term(w) for w in config.get("denylist", [])}
    min_freq = int(config.get("min_freq", 2))
    min_post_count = int(config.get("min_post_count", 2))
    min_score = float(config.get("min_score", 0.3))

    prev_window, curr_window = build_windows(posts)

    term_freq: Counter[str] = Counter()
    term_posts: defaultdict[str, set[str]] = defaultdict(set)
    prev_freq: Counter[str] = Counter()
    curr_freq: Counter[str] = Counter()

    for post in posts:
        post_id = str(post.get("id", ""))
        seen_in_post: set[str] = set()
        for raw in extract_candidates_from_post(post, config):
            term = normalize_term(raw)
            if not term or term in denylist:
                continue
            term_freq[term] += 1
            seen_in_post.add(term)
        for term in seen_in_post:
            term_posts[term].add(post_id)

    prev_ids = {str(p.get("id", "")) for p in prev_window}
    curr_ids = {str(p.get("id", "")) for p in curr_window}

    for post in posts:
        post_id = str(post.get("id", ""))
        bucket = prev_freq if post_id in prev_ids else curr_freq if post_id in curr_ids else None
        if bucket is None:
            continue
        for raw in extract_candidates_from_post(post, config):
            term = normalize_term(raw)
            if not term or term in denylist:
                continue
            bucket[term] += 1

    max_freq = max(term_freq.values()) if term_freq else 1
    total_posts = max(1, len(posts))
    weights = config.get("weights", {"frequency": 0.5, "burst": 0.3, "cross_post": 0.2})

    ranked: list[dict[str, Any]] = []
    for term, freq in term_freq.items():
        post_count = len(term_posts[term])
        if freq < min_freq or post_count < min_post_count:
            continue

        prev_count = prev_freq[term]
        curr_count = curr_freq[term]
        freq_score = freq / max_freq
        burst_ratio = (curr_count + 1) / (prev_count + 1)
        burst_score = min(1.0, max(0.0, (burst_ratio - 1.0) / 2.0))
        cross_post_score = post_count / total_posts

        final_score = (
            float(weights.get("frequency", 0.5)) * freq_score
            + float(weights.get("burst", 0.3)) * burst_score
            + float(weights.get("cross_post", 0.2)) * cross_post_score
        )

        if final_score < min_score:
            continue

        ranked.append(
            {
                "term": term,
                "frequency": freq,
                "post_count": post_count,
                "window_counts": {
                    "prev": prev_count,
                    "curr": curr_count,
                },
                "scores": {
                    "frequency": round(freq_score, 4),
                    "burst": round(burst_score, 4),
                    "cross_post": round(cross_post_score, 4),
                    "final": round(final_score, 4),
                },
                "evidence": {
                    "reason": "matched_frequency_and_cross_post",
                    "burst_ratio": round(burst_ratio, 4),
                },
            }
        )

    ranked.sort(key=lambda item: item["scores"]["final"], reverse=True)

    stats = {
        "total_posts": len(posts),
        "candidate_term_count": len(term_freq),
        "qualified_term_count": len(ranked),
    }
    return ranked, stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect hotword candidates from normalized posts")
    parser.add_argument("--input", required=True, help="Path to normalized JSON from Task 2")
    parser.add_argument("--output", required=True, help="Path to hotword output JSON")
    parser.add_argument(
        "--config",
        default="ai/config/hotword_detection.json",
        help="Path to hotword config JSON",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    config_path = Path(args.config)

    normalized_data = load_json(input_path)
    config = load_json(config_path)

    posts = normalized_data.get("posts", []) if isinstance(normalized_data, dict) else []
    ranked, stats = score_candidates(posts, config)
    top_n = int(config.get("top_n", 10))

    output = {
        "run_stage": "detect",
        "config_version": config.get("rule_version", "v0.1"),
        "input_stage": normalized_data.get("run_stage", "unknown") if isinstance(normalized_data, dict) else "unknown",
        "top_n": top_n,
        "hotwords": ranked[:top_n],
        "stats": stats,
    }

    dump_json(output_path, output)


if __name__ == "__main__":
    main()
