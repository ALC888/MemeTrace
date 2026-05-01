#!/usr/bin/env python3
"""Export full analysis run envelope from stage outputs."""

from __future__ import annotations

import argparse
import json
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build final analysis-run JSON envelope")
    parser.add_argument("--normalized", required=True)
    parser.add_argument("--hotwords", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default="run_20260418_demo_task6")
    parser.add_argument("--batch-id", default="batch_20260418_task6")
    parser.add_argument("--source-type", default="public_sample")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    normalized = load_json(Path(args.normalized))
    hotwords = load_json(Path(args.hotwords))
    summary = load_json(Path(args.summary))

    posts = normalized.get("posts", []) if isinstance(normalized, dict) else []
    platforms = sorted({str(p.get("platform", "")) for p in posts if p.get("platform")})

    output = {
        "run_id": args.run_id,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_batch": {
            "batch_id": args.batch_id,
            "source_type": args.source_type,
            "platforms": platforms,
            "record_count": len(posts),
        },
        "events": summary.get("events", []) if isinstance(summary, dict) else [],
        "evidence": summary.get("evidence", []) if isinstance(summary, dict) else [],
        "trend_snapshots": summary.get("trend_snapshots", []) if isinstance(summary, dict) else [],
        "stats": {
            "raw_post_count": len(posts),
            "normalized_post_count": normalized.get("output_count", len(posts)) if isinstance(normalized, dict) else len(posts),
            "candidate_term_count": hotwords.get("stats", {}).get("candidate_term_count", 0) if isinstance(hotwords, dict) else 0,
            "event_count": len(summary.get("events", [])) if isinstance(summary, dict) else 0,
        },
    }

    dump_json(Path(args.output), output)


if __name__ == "__main__":
    main()
