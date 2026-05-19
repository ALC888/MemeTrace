from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DEPS = REPO_ROOT / "backend" / ".deps"
if str(BACKEND_DEPS) not in sys.path:
    sys.path.insert(0, str(BACKEND_DEPS))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app
from backend.app.services import bootstrap_data
from backend.app.storage import import_analysis_run, load_json_file

SAMPLE_ANALYSIS_RUN = REPO_ROOT / "backend" / "sample_data" / "analysis-run.public-sample.json"


async def asgi_request(
    path: str,
    method: str = "GET",
    query_string: str = "",
    json_body: dict | None = None,
) -> tuple[int, dict, bytes]:
    body = b""
    headers: list[tuple[bytes, bytes]] = []
    if json_body is not None:
        body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("utf-8"),
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    sent = False
    messages: list[dict] = []

    async def receive() -> dict:
        nonlocal sent
        if sent:
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(scope, receive, send)

    status_code = 500
    response_headers: dict[str, str] = {}
    response_body = b""
    for message in messages:
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            response_body += message.get("body", b"")

    return status_code, response_headers, response_body


class BackendAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        bootstrap_data()

    def setUp(self) -> None:
        import_analysis_run(load_json_file(SAMPLE_ANALYSIS_RUN))

    def request_json(
        self,
        path: str,
        method: str = "GET",
        query_string: str = "",
        json_body: dict | None = None,
    ) -> tuple[int, dict]:
        status, _, body = asyncio.run(asgi_request(path, method=method, query_string=query_string, json_body=json_body))
        return status, json.loads(body.decode("utf-8"))

    def test_health_endpoint(self) -> None:
        status, payload = self.request_json("/api/health")
        self.assertEqual(200, status)
        self.assertEqual("ok", payload["status"])

    def test_hot_events_endpoint(self) -> None:
        status, payload = self.request_json("/api/hot-events")
        self.assertEqual(200, status)
        self.assertEqual(1, payload["total"])
        self.assertEqual("电子榨菜", payload["items"][0]["name"])

    def test_hot_event_detail_endpoint(self) -> None:
        status, payload = self.request_json("/api/hot-events/event_0001")
        self.assertEqual(200, status)
        self.assertEqual("event_0001", payload["id"])
        self.assertTrue(payload["evidence"])

    def test_timeline_endpoint(self) -> None:
        status, payload = self.request_json("/api/hot-events/event_0001/timeline")
        self.assertEqual(200, status)
        self.assertEqual("event_0001", payload["event_id"])
        self.assertGreaterEqual(len(payload["nodes"]), 1)

    def test_search_endpoint(self) -> None:
        status, payload = self.request_json("/api/search", query_string="q=%E7%94%B5%E5%AD%90")
        self.assertEqual(200, status)
        self.assertEqual(1, payload["total"])

    def test_reanalyze_reset_demo_seed(self) -> None:
        status, payload = self.request_json("/api/admin/reanalyze", method="POST", json_body={})
        self.assertEqual(200, status)
        self.assertEqual("demo_seed", payload["mode"])
        self.assertGreaterEqual(payload["event_count"], 1)

    def test_reanalyze_with_public_sample_input(self) -> None:
        temp_output = REPO_ROOT / "backend" / "data" / "test-analysis-run.json"
        if temp_output.exists():
            temp_output.unlink()
        self.addCleanup(lambda: temp_output.exists() and temp_output.unlink())

        status, payload = self.request_json(
            "/api/admin/reanalyze",
            method="POST",
            json_body={
                "input_path": "sample_data/raw-posts.public-sample.json",
                "final_output_path": str(temp_output),
            },
        )
        self.assertEqual(200, status)
        self.assertEqual("ai_pipeline", payload["mode"])
        self.assertEqual(str(temp_output), payload["output_path"])
        self.assertTrue(temp_output.exists())


if __name__ == "__main__":
    unittest.main()
