"""Smoke tests for the AETHER Phase 1 backend.

Run against a running server:
  AETHER_BASE_URL=http://127.0.0.1:5467 python3 -m unittest tests.test_backend_smoke -v
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import unittest

BASE = os.environ.get("AETHER_BASE_URL", "http://127.0.0.1:5467")
API_PREFIX = "/api"

_admin_token_cache = {"token": None}


def _admin_token():
    """Cache an admin bearer token (default admin/admin account)."""
    if _admin_token_cache["token"]:
        return _admin_token_cache["token"]
    data = json.dumps({"username": "admin", "password": "admin"}).encode()
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            _admin_token_cache["token"] = json.loads(r.read().decode())["token"]
    except urllib.error.HTTPError:
        _admin_token_cache["token"] = None
    return _admin_token_cache["token"]


def _request(method, path, body=None, token=None, api=True, parse_json=True):
    url = BASE + (API_PREFIX + path if api else path)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if token is None:
        token = _admin_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            if not parse_json:
                return r.status, raw
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        with e:
            raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


class BackendSmokeTests(unittest.TestCase):
    def test_health(self):
        status, data = _request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "AETHER")

    def test_auth_flow(self):
        status, data = _request("POST", "/auth/login", {"username": "admin", "password": "admin"})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        token = data["token"]

        status, data = _request("GET", "/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["username"], "admin")

        status, _ = _request("POST", "/auth/logout", token=token)
        self.assertEqual(status, 200)

        # Stateless bearer token remains valid until expiry (logout clears the cookie).
        status, data = _request("GET", "/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["username"], "admin")

        status, _ = _request("GET", "/auth/me", token="bogus.token.value")
        self.assertEqual(status, 401)

        status, _ = _request("POST", "/auth/login", {"username": "admin", "password": "wrong"})
        self.assertEqual(status, 401)

    def test_files_crud(self):
        status, data = _request("POST", "/files", {"path": "smoke.txt", "content": "hello"})
        self.assertEqual(status, 200)

        status, data = _request("GET", "/files/text?path=smoke.txt")
        self.assertEqual(status, 200)
        self.assertEqual(data["content"], "hello")

        status, data = _request("GET", "/files")
        self.assertEqual(status, 200)
        names = [e["name"] for e in data["entries"]]
        self.assertIn("smoke.txt", names)

        status, data = _request("GET", "/files/search?q=smoke")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["results"]), 1)

        status, data = _request("POST", "/files/rename", {"path": "smoke.txt", "new_path": "renamed.txt"})
        self.assertEqual(status, 200)

        status, _ = _request("DELETE", "/files", {"path": "renamed.txt"})
        self.assertEqual(status, 200)

    def test_providers_and_models(self):
        status, data = _request("GET", "/providers")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["providers"]), 10)

        import time
        model_id = f"smoke-model-{int(time.time())}"
        status, data = _request("POST", "/models/register", {
            "provider_id": 1, "model_id": model_id, "capabilities": '["chat"]'
        })
        self.assertEqual(status, 200)

        status, data = _request("GET", "/v1/models")
        self.assertEqual(status, 200)
        self.assertIn(model_id, [m["id"] for m in data["data"]])

        # No provider key configured → honest configuration hint, not a fake completion
        status, data = _request("POST", "/v1/chat/completions", {
            "model": model_id, "messages": [{"role": "user", "content": "hi"}]
        })
        self.assertEqual(status, 403)
        self.assertIn("API key", data["error"])

    def test_video_models(self):
        status, data = _request("GET", "/providers")
        self.assertEqual(status, 200)
        video_providers = [p for p in data["providers"] if "video" in p.get("capabilities", "")]
        if not video_providers:
            self.skipTest("No video provider configured")
        pid = video_providers[0]["id"]
        status, data = _request("GET", f"/video/models?provider_id={pid}")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["models"]), 1)

    def test_video_generate_requires_prompt(self):
        status, data = _request("POST", "/video/generate", {
            "provider_id": 1,
            "duration": 5,
        })
        self.assertEqual(status, 400)
        self.assertIn("prompt", data["error"])

    def test_video_crud(self):
        status, data = _request("GET", "/video")
        self.assertEqual(status, 200)
        self.assertIsInstance(data["videos"], list)

    def test_stubs_return_501(self):
        # integrations is still Phase 7 stub (video is Phase 5, implemented)
        status, _ = _request("GET", "/integrations")
        self.assertEqual(status, 501)

    def test_images_list(self):
        status, data = _request("GET", "/images")
        self.assertEqual(status, 200)
        self.assertIsInstance(data["images"], list)

    def test_image_generate_requires_key(self):
        # Register imgtest provider with no key -> 403 on generate.
        status, data = _request("POST", "/providers", {
            "name": "imgtest", "display_name": "Img Test",
            "base_url": "http://127.0.0.1:19973",
            "capabilities": '["image"]',
        })
        if status == 409:
            status, pdata = _request("GET", "/providers")
            pid = [p["id"] for p in pdata["providers"] if p["name"] == "imgtest"][0]
        elif "provider" in data:
            pid = data["provider"]["id"]
        else:
            self.fail(f"Could not create imgtest provider: status={status} data={data}")
        status, data = _request("POST", "/images/generate", {
            "provider_id": pid, "model": "dall-e-3", "prompt": "test image",
        })
        self.assertEqual(status, 403)
        self.assertIn("API key", data["error"])

    def test_skills_crud(self):
        # List built-in skills
        status, data = _request("GET", "/skills")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["skills"]), 1)

        # Get a skill
        skill_id = data["skills"][0]["id"]
        status, data = _request("GET", f"/skill?id={skill_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["skill"]["id"], skill_id)

    def test_skills_execution_file_reader(self):
        # First create a file to read
        _request("POST", "/files", {"path": "skill_test.txt", "content": "hello from skill test"})

        # Execute file_reader skill
        status, data = _request("POST", "/skills/execute", {
            "skill": "file_reader",
            "function": "read_file",
            "params": {"path": "skill_test.txt"},
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["result"]["content"], "hello from skill test")
        self.assertTrue(data["result"]["ok"])

    def test_skills_execution_file_writer(self):
        status, data = _request("POST", "/skills/execute", {
            "skill": "file_writer",
            "function": "write_file",
            "params": {"path": "skill_written.txt", "content": "written by skill"},
        })
        self.assertEqual(status, 200)
        self.assertTrue(data["result"]["ok"])

        # Verify the file was written
        status, data = _request("GET", "/files/text?path=skill_written.txt")
        self.assertEqual(status, 200)
        self.assertEqual(data["content"], "written by skill")

    def test_agents_and_tasks(self):
        # Create an agent
        status, data = _request("POST", "/agents", {
            "name": "Test Agent",
            "model": "custom-test",
            "system_prompt": "You are a helpful test agent.",
        })
        self.assertEqual(status, 200)
        agent_id = data["agent"]["id"]

        # List agents
        status, data = _request("GET", "/agents")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["agents"]), 1)

        # Create a task
        status, data = _request("POST", "/tasks", {
            "agent_id": agent_id,
            "title": "Test task",
        })
        self.assertEqual(status, 200)
        task_id = data["task"]["id"]

        # List tasks
        status, data = _request("GET", "/tasks")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["tasks"]), 1)

        # Get task
        status, data = _request("GET", f"/task?id={task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["task"]["id"], task_id)

    def test_gateway_requires_key(self):
        # Register a model, then call chat with no provider key -> honest 403.
        status, data = _request("POST", "/models/register", {
            "provider_id": 1, "model_id": "nokey-model", "capabilities": '["chat"]'
        })
        self.assertIn(status, (200, 409))
        status, data = _request("POST", "/v1/chat/completions", {
            "model": "nokey-model",
            "messages": [{"role": "user", "content": "hi"}],
        })
        self.assertEqual(status, 403)
        self.assertIn("API key", data["error"])

    def test_gateway_unknown_model(self):
        status, _ = _request("POST", "/v1/chat/completions", {
            "model": "does-not-exist",
            "messages": [{"role": "user", "content": "hi"}],
        })
        self.assertEqual(status, 404)

    def test_not_found(self):
        # Client-side router: unknown UI routes fall back to the SPA (index.html).
        status, _ = _request("GET", "/does-not-exist", api=False, parse_json=False)
        self.assertEqual(status, 200)
        # Unknown API routes still return 404 JSON.
        status, data = _request("GET", "/nope")
        self.assertEqual(status, 404)
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main()
