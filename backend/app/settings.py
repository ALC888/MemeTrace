from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = BASE_DIR.parent
REPO_ROOT = Path(os.getenv("MEMETRACE_REPO_ROOT", DEFAULT_REPO_ROOT)).resolve()
AI_PIPELINE_SCRIPT = REPO_ROOT / "ai" / "pipeline" / "run_full_pipeline.py"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "memetrace.db"
PIPELINE_OUT_DIR = DATA_DIR / "pipeline_runs"
PIPELINE_FINAL_OUTPUT = DATA_DIR / "analysis-run.latest.json"
