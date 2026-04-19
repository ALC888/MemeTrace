#!/usr/bin/env python3
"""Task 4 baseline: cluster similar expressions into single meme events."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

CJK_SPAN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,8}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_term(term: str) -> str:
    return re.sub(r"\s+", "", (term or "").strip().lower())


def ngrams(text: str, n: int) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def cosine_on_counter(a: dict[str, int], b: dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def char_counter(text: str) -> dict[str, int]:
    counter: dict[str, int] = {}
    for ch in text:
        counter[ch] = counter.get(ch, 0) + 1
    return counter


def keyword_overlap_score(left: str, right: str) -> float:
    left_parts = set(CJK_SPAN_PATTERN.findall(left)) or {left}
    right_parts = set(CJK_SPAN_PATTERN.findall(right)) or {right}
    return jaccard(left_parts, right_parts)


def vector_proxy_score(left: str, right: str) -> float:
    # Offline-friendly proxy for semantic similarity in baseline stage.
    left_vec = char_counter(left)
    right_vec = char_counter(right)
    return cosine_on_counter(left_vec, right_vec)


def gather_candidate_terms(normalized_posts: list[dict[str, Any]], hotwords: list[dict[str, Any]]) -> set[str]:
    terms: set[str] = set()

    for item in hotwords:
        term = normalize_term(str(item.get("term", "")))
        if term:
            terms.add(term)

    for post in normalized_posts:
        extra = post.get("extra", {}) if isinstance(post.get("extra", {}), dict) else {}
        for tag in extra.get("topic_tags", []) or []:
            t = normalize_term(str(tag))
            if t:
                terms.add(t)

        for token in post.get("tokens", []) or []:
            t = normalize_term(str(token))
            if not t:
                continue
            if "梗" in t:
                terms.add(t)

    return terms


def build_alias_index(config: dict[str, Any]) -> tuple[dict[str, str], dict[str, set[str]]]:
    alias_map = config.get("alias_map", {})
    reverse: dict[str, str] = {}
    canonical_to_aliases: dict[str, set[str]] = {}

    for canonical, aliases in alias_map.items():
        c = normalize_term(canonical)
        if not c:
            continue
        canonical_to_aliases.setdefault(c, set()).add(c)
        reverse[c] = c
        for alias in aliases:
            a = normalize_term(str(alias))
            if not a:
                continue
            canonical_to_aliases[c].add(a)
            reverse[a] = c

    return reverse, canonical_to_aliases


def cluster_terms(
    terms: set[str],
    hotwords: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    alias_reverse, canonical_to_aliases = build_alias_index(config)
    overlap_threshold = float(config.get("keyword_overlap_threshold", 0.5))
    vector_threshold = float(config.get("vector_similarity_threshold", 0.75))

    hotword_scores = {normalize_term(str(h.get("term", ""))): float(h.get("scores", {}).get("final", 0.0)) for h in hotwords}

    # Start with canonical buckets from alias map.
    clusters: dict[str, set[str]] = {k: set(v) for k, v in canonical_to_aliases.items()}
    term_mapping: dict[str, dict[str, Any]] = {}

    # Seed mapping from alias map.
    for term in terms:
        if term in alias_reverse:
            canonical = alias_reverse[term]
            clusters.setdefault(canonical, set()).add(term)
            term_mapping[term] = {
                "term": term,
                "canonical_term": canonical,
                "method": "alias_dict",
                "keyword_overlap": 1.0,
                "vector_similarity": 1.0,
            }

    # Create canonical cluster for every hotword term.
    for term in hotword_scores:
        if not term:
            continue
        clusters.setdefault(term, set()).add(term)
        if term not in term_mapping:
            term_mapping[term] = {
                "term": term,
                "canonical_term": term,
                "method": "exact",
                "keyword_overlap": 1.0,
                "vector_similarity": 1.0,
            }

    # Attach remaining terms to closest existing canonical if thresholds pass.
    unresolved = [t for t in terms if t not in term_mapping]
    canonicals = list(clusters.keys())

    for term in unresolved:
        best_canonical = None
        best_overlap = 0.0
        best_vector = 0.0
        best_score = -1.0

        for canonical in canonicals:
            overlap = keyword_overlap_score(term, canonical)
            vec = vector_proxy_score(term, canonical)
            score = 0.6 * overlap + 0.4 * vec

            if score > best_score:
                best_score = score
                best_canonical = canonical
                best_overlap = overlap
                best_vector = vec

        if best_canonical and (best_overlap >= overlap_threshold or best_vector >= vector_threshold):
            clusters.setdefault(best_canonical, set()).add(term)
            term_mapping[term] = {
                "term": term,
                "canonical_term": best_canonical,
                "method": "similarity",
                "keyword_overlap": round(best_overlap, 4),
                "vector_similarity": round(best_vector, 4),
            }
        else:
            clusters.setdefault(term, set()).add(term)
            term_mapping[term] = {
                "term": term,
                "canonical_term": term,
                "method": "singleton",
                "keyword_overlap": round(best_overlap, 4),
                "vector_similarity": round(best_vector, 4),
            }

    cluster_items: list[dict[str, Any]] = []
    for idx, canonical in enumerate(sorted(clusters.keys()), start=1):
        members = sorted(clusters[canonical])
        support_score = max((hotword_scores.get(m, 0.0) for m in members), default=0.0)
        cluster_items.append(
            {
                "cluster_id": f"cluster_{idx:04d}",
                "canonical_term": canonical,
                "member_terms": members,
                "aliases": [m for m in members if m != canonical],
                "support": {
                    "max_hotword_score": round(support_score, 4),
                    "member_count": len(members),
                },
            }
        )

    mappings = [term_mapping[k] for k in sorted(term_mapping.keys())]
    return cluster_items, mappings


def build_post_cluster_links(
    normalized_posts: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    term_to_canonical = {m["term"]: m["canonical_term"] for m in mappings}
    links: list[dict[str, Any]] = []

    for post in normalized_posts:
        post_id = str(post.get("id", ""))
        terms_in_post: set[str] = set()

        extra = post.get("extra", {}) if isinstance(post.get("extra", {}), dict) else {}
        for tag in extra.get("topic_tags", []) or []:
            terms_in_post.add(normalize_term(str(tag)))

        for token in post.get("tokens", []) or []:
            t = normalize_term(str(token))
            if t:
                terms_in_post.add(t)

        mapped_clusters = sorted({term_to_canonical[t] for t in terms_in_post if t in term_to_canonical})
        if mapped_clusters:
            links.append(
                {
                    "post_id": post_id,
                    "cluster_terms": mapped_clusters,
                }
            )

    return links


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster similar meme expressions into canonical events")
    parser.add_argument("--normalized", required=True, help="Path to Task 2 normalized JSON")
    parser.add_argument("--hotwords", required=True, help="Path to Task 3 hotwords JSON")
    parser.add_argument("--output", required=True, help="Path to Task 4 cluster output JSON")
    parser.add_argument(
        "--config",
        default="ai/config/cluster_rules.json",
        help="Path to clustering config JSON",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    normalized_path = Path(args.normalized)
    hotwords_path = Path(args.hotwords)
    output_path = Path(args.output)
    config_path = Path(args.config)

    normalized_data = load_json(normalized_path)
    hotword_data = load_json(hotwords_path)
    config = load_json(config_path)

    normalized_posts = normalized_data.get("posts", []) if isinstance(normalized_data, dict) else []
    hotwords = hotword_data.get("hotwords", []) if isinstance(hotword_data, dict) else []

    terms = gather_candidate_terms(normalized_posts, hotwords)
    clusters, mappings = cluster_terms(terms, hotwords, config)
    post_links = build_post_cluster_links(normalized_posts, mappings)

    output = {
        "run_stage": "cluster",
        "config_version": config.get("rule_version", "v0.1"),
        "input_stage": {
            "normalized": normalized_data.get("run_stage", "unknown") if isinstance(normalized_data, dict) else "unknown",
            "hotword": hotword_data.get("run_stage", "unknown") if isinstance(hotword_data, dict) else "unknown",
        },
        "clusters": clusters,
        "term_mappings": mappings,
        "post_cluster_links": post_links,
        "stats": {
            "candidate_term_count": len(terms),
            "cluster_count": len(clusters),
            "mapped_term_count": len(mappings),
            "linked_post_count": len(post_links),
        },
    }

    dump_json(output_path, output)


if __name__ == "__main__":
    main()
