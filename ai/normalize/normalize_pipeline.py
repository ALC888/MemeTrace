#!/usr/bin/env python3
"""Task 2 baseline: text normalization pipeline for meme analysis."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@[\w\u4e00-\u9fff_-]+")
FORWARD_PREFIX_PATTERN = re.compile(r"^(转发微博|转发|repost|RT)\s*[:：]\s*", re.IGNORECASE)
TOPIC_PATTERN = re.compile(r"#([^#]{1,60})#")
REPEAT_CHAR_PATTERN = re.compile(r"([!！?？~～。,.，])\1+")
SPACE_PATTERN = re.compile(r"\s+")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_stopwords(path: Path) -> set[str]:
    words: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(line)
    return words


def normalize_text(raw_text: str, config: dict[str, Any]) -> str:
    text = raw_text or ""

    if config.get("remove_forward_prefix", True):
        text = FORWARD_PREFIX_PATTERN.sub("", text)

    if config.get("remove_urls", True):
        text = URL_PATTERN.sub(" ", text)

    if config.get("remove_mentions", True):
        text = MENTION_PATTERN.sub(" ", text)

    if config.get("normalize_topics", True):
        text = TOPIC_PATTERN.sub(lambda m: f" {m.group(1)} ", text)

    if config.get("collapse_repeat_punct", True):
        text = REPEAT_CHAR_PATTERN.sub(r"\1", text)

    if config.get("normalize_whitespace", True):
        text = SPACE_PATTERN.sub(" ", text)

    return text.strip()


def tokenize(text: str, config: dict[str, Any], stopwords: set[str]) -> list[str]:
    # Basic baseline tokenization: keep Chinese blocks, numbers, and latin words.
    token_pattern = config.get("token_pattern", r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+")
    raw_tokens = re.findall(token_pattern, text)

    min_len = int(config.get("min_token_len", 1))
    normalized_tokens: list[str] = []
    for token in raw_tokens:
        t = token.lower().strip()
        if len(t) < min_len:
            continue
        if t in stopwords:
            continue
        normalized_tokens.append(t)
    return normalized_tokens


def normalize_post(raw_post: dict[str, Any], config: dict[str, Any], stopwords: set[str]) -> dict[str, Any]:
    text = raw_post.get("content", "")
    cleaned = normalize_text(text, config)
    tokens = tokenize(cleaned, config, stopwords)

    result = dict(raw_post)
    result["normalized_content"] = cleaned
    result["tokens"] = tokens
    result["normalization_meta"] = {
        "rule_version": config.get("rule_version", "v0.1"),
        "removed_url": bool(URL_PATTERN.search(text)) if config.get("remove_urls", True) else False,
        "removed_mention": bool(MENTION_PATTERN.search(text)) if config.get("remove_mentions", True) else False,
    }
    return result


def to_post_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    raise ValueError("Input JSON must be an object or an array of objects")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize raw post text for downstream meme analysis")
    parser.add_argument("--input", required=True, help="Path to input raw-post JSON")
    parser.add_argument("--output", required=True, help="Path to output normalized JSON")
    parser.add_argument(
        "--config",
        default="ai/config/normalization.json",
        help="Path to normalization config JSON",
    )
    parser.add_argument(
        "--stopwords",
        default="ai/config/stopwords_zh.txt",
        help="Path to stopwords file",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    config_path = Path(args.config)
    stopwords_path = Path(args.stopwords)

    config = load_json(config_path)
    stopwords = load_stopwords(stopwords_path)
    raw_data = load_json(input_path)

    posts = to_post_list(raw_data)
    normalized_posts = [normalize_post(p, config, stopwords) for p in posts]

    output: dict[str, Any] = {
        "run_stage": "normalize",
        "config_version": config.get("rule_version", "v0.1"),
        "input_count": len(posts),
        "output_count": len(normalized_posts),
        "posts": normalized_posts,
    }

    dump_json(output_path, output)


if __name__ == "__main__":
    main()
