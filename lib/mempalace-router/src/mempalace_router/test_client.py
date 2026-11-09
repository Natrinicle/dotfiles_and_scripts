"""Tests for the per-target hub client (real HTTP against FakeHub)."""

import dataclasses
import socketserver
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


class GarbageStatusHub(FakeHub):
    """Answers every request with a line that is not an HTTP status line."""

    def __init__(self, **kw):
        super().__init__(**kw)

        class Garbage(socketserver.StreamRequestHandler):
            def handle(self):
                length = 0
                while True:
                    line = self.rfile.readline()
                    if line in (b"\r\n", b"\n", b""):
                        break
                    name, _, value = line.decode("latin-1").partition(":")
                    if name.strip().lower() == "content-length":
                        length = int(value.strip())
                self.rfile.read(length)
                self.wfile.write(b"NOT-HTTP garbage\r\n\r\n")

        self._server.RequestHandlerClass = Garbage


class ClientFixWaveTest(unittest.TestCase):
    _hub = ClientTest._hub
    _target = ClientTest._target

    def test_target_url_ending_in_mcp_posts_to_base_mcp_once(self):
        hub = self._hub()
        target = dataclasses.replace(self._target(hub), url=hub.url + "/mcp")
        client = HubClient(target)
        self.assertEqual(client.resolve()[0], hub.url)
        out = client.call_tool("mempalace_status", {})
        self.assertIn("total_drawers", out)
        self.assertEqual([c[0] for c in hub.calls], ["mempalace_status"])
        self.assertTrue(client.ping())

    def test_bad_status_line_is_transport_error(self):
        hub = self._hub_cls(GarbageStatusHub)
        client = HubClient(self._target(hub), timeout_s=2)
        with self.assertRaises(HubError) as cm:
            client.call_tool("mempalace_status", {})
        self.assertEqual(cm.exception.kind, "transport")
        self.assertFalse(client.ping())

    def _hub_cls(self, cls):
        hub = cls()
        hub.start()
        self.addCleanup(hub.stop)
        return hub

if __name__ == "__main__":
    unittest.main()
