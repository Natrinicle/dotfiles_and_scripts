import json
import unittest
import urllib.error
import urllib.request

from mempalace_router.testing.fakehub import FakeHub


def _post(url, payload, token):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _call(hub, name, arguments, token="abc", rid=1):
    out = _post(
        hub.url + "/mcp",
        {"jsonrpc": "2.0", "id": rid, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}},
        token,
    )
    return json.loads(out["result"]["content"][0]["text"])


class FakeHubTest(unittest.TestCase):
    def _hub(self, **kw):
        hub = FakeHub(token="abc", **kw)
        hub.start()
        self.addCleanup(hub.stop)
        return hub

    def test_fakehub_roundtrip_add_and_search(self):
        hub = self._hub()
        body = _call(hub, "mempalace_add_drawer",
                     {"wing": "w", "room": "r", "content": "hello palace"})
        self.assertTrue(body["success"])
        self.assertIn("drawer_id", body)
        hits = _call(hub, "mempalace_search", {"query": "palace"})["results"]
        self.assertEqual(hits[0]["drawer_id"], body["drawer_id"])
        self.assertEqual(hits[0]["effective_distance"], 0.0)
        self.assertEqual(hub.calls[0][0], "mempalace_add_drawer")
        self.assertEqual(hub.taxonomy, {"w": {"r": 1}})

    def test_fakehub_duplicate_content_already_exists(self):
        hub = self._hub()
        args = {"wing": "w", "room": "r", "content": "same"}
        first = _call(hub, "mempalace_add_drawer", args)
        second = _call(hub, "mempalace_add_drawer", args)
        self.assertTrue(second["success"])
        self.assertTrue(second["already_exists"])
        self.assertEqual(second["drawer_id"], first["drawer_id"])

    def test_fakehub_rejects_bad_token(self):
        hub = self._hub()
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            _post(hub.url + "/mcp",
                  {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "wrong")
        self.addCleanup(ctx.exception.close)
        self.assertEqual(ctx.exception.code, 401)

    def test_fakehub_healthz_without_auth(self):
        hub = self._hub()
        with urllib.request.urlopen(hub.url + "/healthz", timeout=5) as resp:
            self.assertEqual(resp.read(), b"ok\n")

    def test_fakehub_tools_list(self):
        hub = self._hub()
        out = _post(hub.url + "/mcp",
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, "abc")
        tools = {t["name"]: t for t in out["result"]["tools"]}
        self.assertEqual(len(tools), 11)
        self.assertIn("mempalace_get_taxonomy", tools)
        self.assertEqual(tools["mempalace_search"]["inputSchema"]["type"], "object")

    def test_fakehub_supersede_requires_current_old(self):
        hub = self._hub()
        added = _call(hub, "mempalace_kg_add",
                      {"subject": "s", "predicate": "p", "object": "old"})
        self.assertTrue(added["success"])
        bad = _call(hub, "mempalace_kg_supersede",
                    {"subject": "s", "predicate": "p",
                     "old_object": "nope", "new_object": "new"})
        self.assertFalse(bad["success"])
        good = _call(hub, "mempalace_kg_supersede",
                     {"subject": "s", "predicate": "p",
                      "old_object": "old", "new_object": "new"})
        self.assertTrue(good["success"])
        current = _call(hub, "mempalace_kg_query", {"entity": "s"})
        self.assertEqual([f["object"] for f in current["facts"]], ["new"])

    def test_fakehub_fail_tools(self):
        hub = self._hub(fail_tools={"mempalace_status"})
        self.assertEqual(_call(hub, "mempalace_status", {}),
                         {"success": False, "error": "forced"})

    def test_fakehub_delete_and_listings(self):
        hub = self._hub()
        d = _call(hub, "mempalace_add_drawer",
                  {"wing": "w", "room": "r", "content": "x"})
        self.assertEqual(_call(hub, "mempalace_list_wings", {})["wings"], {"w": 1})
        self.assertEqual(_call(hub, "mempalace_list_rooms", {"wing": "w"})["rooms"], {"r": 1})
        self.assertEqual(_call(hub, "mempalace_get_taxonomy", {})["taxonomy"], {"w": {"r": 1}})
        self.assertTrue(_call(hub, "mempalace_delete_drawer", {"drawer_id": d["drawer_id"]})["success"])
        self.assertEqual(hub.drawers, {})


if __name__ == "__main__":
    unittest.main()
