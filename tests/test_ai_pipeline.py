from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class AIPipelineRegressionTest(unittest.TestCase):
    def test_public_sample_full_pipeline(self) -> None:
        temp_dir = REPO_ROOT / "sample_data" / "out" / "test-ai-pipeline"
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        out_dir = temp_dir / "fullrun"
        final_output = temp_dir / "analysis-run.json"

        cmd = [
            sys.executable,
            str(REPO_ROOT / "ai" / "pipeline" / "run_full_pipeline.py"),
            "--input",
            str(REPO_ROOT / "sample_data" / "raw-posts.public-sample.json"),
            "--out-dir",
            str(out_dir),
            "--final-output",
            str(final_output),
        ]
        completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            self.fail(completed.stderr or completed.stdout or "AI pipeline failed")

        self.assertTrue(final_output.exists(), "final analysis-run output should exist")

        with final_output.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("generated_at", data)
        self.assertEqual("public_sample", data["source_batch"]["source_type"])
        self.assertGreaterEqual(data["stats"]["event_count"], 1)
        self.assertEqual(6, data["stats"]["raw_post_count"])
        self.assertTrue(data["events"], "events should not be empty")

        first_event = data["events"][0]
        self.assertEqual("某梗", first_event["name"])
        self.assertIn(first_event["status"], {"complete", "partial", "needs_review"})
        self.assertGreaterEqual(first_event["heat_score"], 0.0)
        self.assertLessEqual(first_event["heat_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
