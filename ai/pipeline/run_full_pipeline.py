#!/usr/bin/env python3
"""Run normalize -> detect -> cluster -> attribute -> summarize -> export."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full offline pipeline for demo")
    parser.add_argument("--input", required=True, help="Path to raw posts input JSON")
    parser.add_argument("--out-dir", default="sample_data/processed/fullrun", help="Output directory for stage files")
    parser.add_argument("--final-output", default="sample_data/processed/analysis-run.task6.output.json")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    py = sys.executable
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    normalized = out_dir / "01.normalized.json"
    hotwords = out_dir / "02.hotwords.json"
    clusters = out_dir / "03.clusters.json"
    attribution = out_dir / "04.attribution.json"
    summary = out_dir / "05.summary.json"
    final_output = Path(args.final_output)

    run_step(
        [
            py,
            "ai/normalize/normalize_pipeline.py",
            "--input",
            args.input,
            "--output",
            str(normalized),
            "--config",
            "ai/config/normalization.json",
            "--stopwords",
            "ai/config/stopwords_zh.txt",
        ]
    )

    run_step(
        [
            py,
            "ai/detect/hotword_detection.py",
            "--input",
            str(normalized),
            "--output",
            str(hotwords),
            "--config",
            "ai/config/hotword_detection.json",
        ]
    )

    run_step(
        [
            py,
            "ai/cluster/similar_expression_cluster.py",
            "--normalized",
            str(normalized),
            "--hotwords",
            str(hotwords),
            "--output",
            str(clusters),
            "--config",
            "ai/config/cluster_rules.json",
        ]
    )

    run_step(
        [
            py,
            "ai/attribute/source_attribution.py",
            "--normalized",
            str(normalized),
            "--clusters",
            str(clusters),
            "--output",
            str(attribution),
            "--config",
            "ai/config/source_attribution.json",
        ]
    )

    run_step(
        [
            py,
            "ai/summarize/explanation_generation.py",
            "--hotwords",
            str(hotwords),
            "--clusters",
            str(clusters),
            "--attribute",
            str(attribution),
            "--output",
            str(summary),
            "--config",
            "ai/config/explanation_templates.json",
        ]
    )

    run_step(
        [
            py,
            "ai/pipeline/export_analysis_run.py",
            "--normalized",
            str(normalized),
            "--hotwords",
            str(hotwords),
            "--summary",
            str(summary),
            "--output",
            str(final_output),
        ]
    )


if __name__ == "__main__":
    main()
