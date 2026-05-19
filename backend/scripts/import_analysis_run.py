#!/usr/bin/env python3
"""Import an analysis-run JSON file into the backend demo database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.storage import import_analysis_run, load_json_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import analysis-run JSON into backend database")
    parser.add_argument("--input", required=True, help="Path to analysis-run JSON")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input).resolve()

    data = load_json_file(input_path)
    count = import_analysis_run(data)
    print(f"Imported {count} events from {input_path}")


if __name__ == "__main__":
    main()
