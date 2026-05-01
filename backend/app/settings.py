from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "memetrace.db"
PIPELINE_OUT_DIR = DATA_DIR / "pipeline_runs"
PIPELINE_FINAL_OUTPUT = DATA_DIR / "analysis-run.latest.json"
