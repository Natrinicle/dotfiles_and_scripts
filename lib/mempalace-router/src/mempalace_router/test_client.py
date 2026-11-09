"""Tests for the per-target hub client (real HTTP against FakeHub)."""

import tempfile
import unittest
from pathlib import Path

from mempalace_router.client import HubClient, HubError
from mempalace_router.config import Target
from mempalace_router.testing.fakehub import FakeHub


class ClientTest(unittest.TestCase):
    def _hub(self, **kw):
        hub = FakeHub(**kw)
        hub.start()
        self.addCleanup(hub.stop)
        return hub

    def _target(self, hub, cred="t"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "acme.cred"
        path.write_text(cred + "\n")
        return Target(name="acme", kind="company", company="acme", url=hub.url,
                      token_file=path, palace_path=None, hints={})

    def test_call_tool_decodes_text_payload(self):
        hub = self._hub(token="right")
        out = HubClient(self._target(hub, "right")).call_tool(
            "mempalace_add_drawer", {"wing": "w", "room": "r", "content": "hello"})
        self.assertTrue(out["success"])
        self.assertTrue(out["drawer_id"].startswith("drawer_"))

    def test_bad_token_raises_auth(self):
        hub = self._hub(token="right")
        with self.assertRaises(HubError) as cm:
            HubClient(self._target(hub, "wrong")).call_tool("mempalace_status", {})
        self.assertEqual(cm.exception.kind, "auth")

    def test_timeout_raises_timeout(self):
        hub = self._hub(latency_s=2)
        with self.assertRaises(HubError) as cm:
            HubClient(self._target(hub), timeout_s=0.5).call_tool("mempalace_status", {})
        self.assertEqual(cm.exception.kind, "timeout")

    def test_logical_failure_returned_not_raised(self):
        hub = self._hub(fail_tools={"mempalace_add_drawer"})
        out = HubClient(self._target(hub)).call_tool(
            "mempalace_add_drawer", {"wing": "w", "room": "r", "content": "x"})
        self.assertFalse(out["success"])

    def test_list_tools_returns_names(self):
        hub = self._hub()
        names = {t["name"] for t in HubClient(self._target(hub)).list_tools()}
        self.assertIn("mempalace_search", names)

    def test_ping_true_when_up(self):
        hub = self._hub()
        self.assertTrue(HubClient(self._target(hub)).ping())

    def test_ping_false_when_down(self):
        hub = self._hub()
        target = self._target(hub)
        hub.stop()
        self.assertFalse(HubClient(target, timeout_s=1).ping())

    def test_down_hub_raises_transport(self):
        hub = self._hub()
        target = self._target(hub)
        hub.stop()
        with self.assertRaises(HubError) as cm:
            HubClient(target, timeout_s=1).call_tool("mempalace_status", {})
        self.assertEqual(cm.exception.kind, "transport")

    def test_resolve_reads_token_file(self):
        hub = self._hub()
        url, headers = HubClient(self._target(hub, "abc")).resolve()
        self.assertEqual(url, hub.url)
        self.assertEqual(headers["Authorization"], "Bearer abc")


if __name__ == "__main__":
    unittest.main()
