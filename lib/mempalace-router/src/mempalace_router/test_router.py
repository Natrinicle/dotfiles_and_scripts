import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from mempalace_router.client import HubClient
from mempalace_router.config import Target, Targets
from mempalace_router.router import Router
from mempalace_router.testing.fakehub import FakeHub

AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


class DrawerHub(FakeHub):
    """FakeHub plus ``mempalace_get_drawer`` (the stock fake lacks it)."""

    def _tool(self, name, args):
        if name == "mempalace_mine" and name not in self.fail_tools:
            return {"success": True, "files": 0}
        if name == "mempalace_get_drawer":
            drawer = self.drawers.get(args.get("drawer_id"))
            if drawer is None:
                return {"success": False, "error": "drawer not found"}
            return {"drawer_id": args["drawer_id"], "content": drawer["text"],
                    "wing": drawer["wing"], "room": drawer["room"]}
        return super()._tool(name, args)


class RouterTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self._stopped = set()
        self.local = self.start_hub(DrawerHub(token="lt"))
        self.acme = self.start_hub(DrawerHub(token="at"))
        self.targets = self.make_targets(self.local, self.acme)

    def start_hub(self, hub):
        hub.start()
        self.addCleanup(self.stop_hub, hub)
        return hub

    def stop_hub(self, hub):
        if id(hub) not in self._stopped:
            self._stopped.add(id(hub))
            hub.stop()
            hub.join()

    def cred(self, name, token):
        path = self.tmp / f"{name}.cred"
        path.write_text(token)
        return path

    def make_targets(self, local, acme):
        local_t = Target("local", "local", None, local.url, self.cred("local", local.token), None, {})
        acme_t = Target("acme", "company", "Acme", acme.url, self.cred("acme", acme.token), None, {})
        beta_t = Target("beta", "company", "Beta", "http://127.0.0.1:9", self.cred("beta", "x"), None, {})
        by_name = {"local": local_t, "acme": acme_t, "beta": beta_t}
        return Targets(by_name=by_name, local=local_t, companies={"acme": acme_t, "beta": beta_t})

    def make_router(self, **kw):
        kw.setdefault("per_target_timeout_s", 5.0)
        router = Router(self.targets, state_dir=self.tmp / "state", **kw)
        self.addCleanup(router.close)
        return router

    def rpc(self, router, method, params=None, rid=1):
        request = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            request["params"] = params
        return router.handle(request)

    def call(self, router, name, arguments):
        """Return the decoded tool dict, or the JSON-RPC error dict."""
        response = self.rpc(router, "tools/call", {"name": name, "arguments": arguments})
        if "error" in response:
            return response["error"]
        return json.loads(response["result"]["content"][0]["text"])

    def names(self, hub):
        return [c[0] for c in hub.calls]


class RouterTests(RouterTestBase):
    def test_tools_list_adds_scope_and_router_tools(self):
        router = self.make_router()
        tools = self.rpc(router, "tools/list")["result"]["tools"]
        by_name = {t["name"]: t for t in tools}
        for name, tool in by_name.items():
            if name.startswith("mempalace_"):
                scope = tool["inputSchema"]["properties"]["scope"]
                self.assertEqual(scope["type"], "array")
                self.assertEqual(scope["items"], {"type": "string"})
                self.assertEqual(
                    scope["description"], "Targets: local always included; at most one company")
        for name in ("router_targets", "router_retract", "router_replicate",
                     "router_mine", "router_flush", "router_status"):
            self.assertEqual(by_name[name]["inputSchema"]["type"], "object")
        self.assertIn("mempalace_search", by_name)

    def test_read_default_scope_hits_only_local(self):
        self.local.drawers["d1"] = {"text": "note one", "wing": "w", "room": "r"}
        self.acme.drawers["d2"] = {"text": "note two", "wing": "w", "room": "r"}
        router = self.make_router()
        out = self.call(router, "mempalace_search", {"query": "note"})
        self.assertEqual([h["text"] for h in out["results"]], ["note one"])
        self.assertEqual(self.acme.calls, [])
        self.assertNotIn("degraded", out)

    def test_search_company_scope_merges_both(self):
        self.local.drawers["d1"] = {"text": "note one", "wing": "w", "room": "r"}
        self.acme.drawers["d2"] = {"text": "note two", "wing": "w", "room": "r"}
        router = self.make_router()
        out = self.call(router, "mempalace_search", {"query": "note", "scope": ["acme"]})
        self.assertEqual({h["target"] for h in out["results"]}, {"local", "acme"})
        self.assertEqual(len(out["results"]), 2)
        self.assertEqual(out["notes"], ["local added to scope"])

    def test_search_degrades_on_target_timeout(self):
        slow = self.start_hub(FakeHub(token="at", latency_s=2))
        slow._server.handle_error = lambda request, client_address: None  # client hangs up by design
        self.targets = self.make_targets(self.local, slow)
        self.local.drawers["d1"] = {"text": "note one", "wing": "w", "room": "r"}
        router = self.make_router(per_target_timeout_s=1.0)
        out = self.call(router, "mempalace_search", {"query": "note", "scope": ["acme"]})
        self.assertEqual(out["degraded"], ["acme"])
        self.assertEqual([h["target"] for h in out["results"]], ["local"])

    def test_write_local_first_then_company_with_tag_and_ledger(self):
        router = self.make_router()
        args = {"wing": "w", "room": "r", "content": "hello", "scope": ["local", "acme"]}
        out = self.call(router, "mempalace_add_drawer", args)
        self.assertEqual(self.names(self.local)[0], "mempalace_add_drawer")
        self.assertEqual(len(self.local.drawers), 1)
        self.assertEqual(len(self.acme.drawers), 1)
        self.assertEqual(out["filed_to"], ["local", "acme"])
        self.assertEqual(out["tag"], "filed → acme + local")
        rows = router.ledger.lookup(out["call_id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target"], "acme")
        self.assertEqual(rows[0]["tool"], "mempalace_add_drawer")
        self.assertEqual(rows[0]["local_ref"], out["drawer_id"])
        self.assertIn(rows[0]["remote_ref"], self.acme.drawers)
        self.assertNotIn("scope", self.local.calls[0][1])
        self.assertNotIn("scope", [a for n, a in self.acme.calls if n == "mempalace_add_drawer"][0])

    def test_write_company_only_scope_still_writes_local(self):
        router = self.make_router()
        out = self.call(router, "mempalace_kg_add",
                        {"subject": "S", "predicate": "p", "object": "o", "scope": ["acme"]})
        self.assertEqual(len(self.local.facts), 1)
        self.assertEqual(len(self.acme.facts), 1)
        self.assertEqual(out["notes"], ["local added to scope"])
        rows = router.ledger.lookup(out["call_id"])
        self.assertEqual(rows[0]["tool"], "mempalace_kg_add")
        self.assertTrue(rows[0]["remote_ref"].startswith("t_"))

    def test_write_two_companies_rejected(self):
        router = self.make_router()
        err = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme", "beta"]})
        self.assertEqual(err["code"], -32602)
        self.assertEqual(err["data"], {"code": "cross_company_scope"})
        self.assertEqual(self.local.calls, [])

    def test_write_unknown_target_rejected(self):
        router = self.make_router()
        err = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["nope"]})
        self.assertEqual(err["code"], -32602)
        self.assertEqual(err["data"], {"code": "unknown_target"})
        err = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": "acme"})
        self.assertEqual(err["code"], -32602)
        self.assertEqual(err["message"], "scope must be a list of target names")
        self.assertEqual(self.local.calls, [])

    def test_secret_refused_on_company_only(self):
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": f"key {AWS_KEY}", "scope": ["acme"]})
        self.assertEqual(out["refused"], {"acme": "secret_pattern:aws_access_key"})
        self.assertEqual(len(self.local.drawers), 1)
        self.assertEqual(self.acme.calls, [])
        self.assertNotIn("filed_to", out)
        self.assertEqual(router.ledger.lookup(out["call_id"]), [])

    def test_company_logical_error_is_partial_not_ledgered(self):
        failing = self.start_hub(FakeHub(token="at", fail_tools={"mempalace_add_drawer"}))
        self.targets = self.make_targets(self.local, failing)
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme"]})
        self.assertEqual(out["partial"], {"acme": "forced"})
        self.assertEqual(len(self.local.drawers), 1)
        self.assertEqual(router.ledger.lookup(out["call_id"]), [])
        self.assertEqual(router.outbox.pending("acme"), [])
        self.assertNotIn("filed_to", out)

    def test_company_down_queues_outbox_and_flush_drains(self):
        client = HubClient(self.targets.by_name["acme"], timeout_s=2.0)
        router = self.make_router(clients={"acme": client})
        self.stop_hub(self.acme)
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "queued", "scope": ["acme"]})
        self.assertEqual(out["queued_for"], ["acme"])
        self.assertEqual(len(self.local.drawers), 1)
        self.assertEqual(len(router.outbox.pending("acme")), 1)
        self.assertEqual(router.ledger.lookup(out["call_id"]), [])
        todo = self.call(router, "router_targets", {})["todo"]
        self.assertEqual(todo, ["push 1 queued writes to acme (router_flush)"])

        revived = self.start_hub(FakeHub(token="at"))
        client.target = dataclasses.replace(client.target, url=revived.url)
        flushed = self.call(router, "router_flush", {"target": "acme"})
        self.assertEqual(flushed["pushed"], 1)
        self.assertEqual(len(revived.drawers), 1)
        self.assertEqual(router.outbox.pending("acme"), [])
        rows = router.ledger.lookup(out["call_id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["local_ref"], out["drawer_id"])
        status = self.call(router, "router_status", {})
        self.assertEqual(status["ledger_rows"], 1)
        self.assertEqual(status["outbox_pending"]["acme"], 0)

    def test_kg_query_applies_correction_to_older_side(self):
        old = {"subject": "S", "predicate": "p", "object": "A", "valid_from": "2026-01-01",
               "valid_to": None, "current": True}
        new = {"subject": "S", "predicate": "p", "object": "B", "valid_from": "2026-06-01",
               "valid_to": None, "current": True}
        self.local.facts.append(dict(old))
        self.acme.facts.append(dict(new))
        router = self.make_router()
        out = self.call(router, "mempalace_kg_query", {"entity": "S", "scope": ["acme"]})
        self.assertEqual(out["conflicts"][0]["action"], "supersede_local")
        self.assertEqual(len(out["corrections"]), 1)
        self.assertTrue(out["corrections"][0]["applied"])
        self.assertEqual(out["corrections"][0]["target"], "local")
        supersede = [a for n, a in self.local.calls if n == "mempalace_kg_supersede"]
        self.assertEqual(supersede, [{"subject": "S", "predicate": "p",
                                      "old_object": "A", "new_object": "B"}])
        self.assertEqual([f["object"] for f in self.local.facts if f["current"]], ["B"])
        self.assertNotIn("mempalace_kg_supersede", self.names(self.acme))

    def test_kg_query_as_of_skips_correction(self):
        self.local.facts.append({"subject": "S", "predicate": "p", "object": "A",
                                 "valid_from": "2026-01-01", "valid_to": None, "current": True})
        self.acme.facts.append({"subject": "S", "predicate": "p", "object": "B",
                                "valid_from": "2026-06-01", "valid_to": None, "current": True})
        router = self.make_router()
        out = self.call(router, "mempalace_kg_query",
                        {"entity": "S", "scope": ["acme"], "as_of": "2026-07-01"})
        self.assertEqual(len(out["conflicts"]), 1)
        self.assertNotIn("corrections", out)
        self.assertNotIn("mempalace_kg_supersede", self.names(self.local))

    def test_retract_by_call_id_deletes_remote_keeps_local(self):
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "retract me", "scope": ["acme"]})
        self.assertEqual(len(self.acme.drawers), 1)
        done = self.call(router, "router_retract", {"ref": out["call_id"]})
        self.assertEqual(done["retracted"], 1)
        self.assertEqual(done["by_target"], {"acme": 1})
        self.assertEqual(done["errors"], [])
        self.assertEqual(self.acme.drawers, {})
        self.assertEqual(len(self.local.drawers), 1)
        self.assertEqual(router.ledger.lookup(out["call_id"]), [])

    def test_retract_kg_and_refuses_local_target(self):
        router = self.make_router()
        out = self.call(router, "mempalace_kg_add",
                        {"subject": "S", "predicate": "p", "object": "o", "scope": ["acme"]})
        err = self.call(router, "router_retract", {"ref": out["call_id"], "target": "local"})
        self.assertEqual(err["code"], -32602)
        done = self.call(router, "router_retract", {"ref": out["call_id"]})
        self.assertEqual(done["retracted"], 1)
        self.assertFalse(self.acme.facts[0]["current"])
        self.assertTrue(self.local.facts[0]["current"])

    def test_replicate_to_company_maps_wing(self):
        self.local.drawers["d1"] = {"text": "plan", "wing": "k8s", "room": "notes"}
        self.acme.taxonomy = {"kubernetes": {"notes": 1}}
        router = self.make_router()
        out = self.call(router, "router_replicate", {"ref_or_fact": "d1", "to": ["acme"]})
        self.assertEqual(out["by_target"]["acme"]["status"], "filed")
        (drawer,) = self.acme.drawers.values()
        self.assertEqual((drawer["wing"], drawer["room"]), ("kubernetes", "notes"))
        self.assertEqual(len(router.ledger.lookup("d1")), 1)
        fact = self.call(router, "router_replicate",
                         {"ref_or_fact": {"subject": "S", "predicate": "p", "object": AWS_KEY},
                          "to": ["acme"]})
        self.assertEqual(fact["by_target"]["acme"]["status"], "refused")
        err = self.call(router, "router_replicate", {"ref_or_fact": "d1", "to": ["nope"]})
        self.assertEqual(err["code"], -32602)

    def test_router_mine_company_chunks_and_single_job_id(self):
        src = self.tmp / "notes"
        (src / "sub").mkdir(parents=True)
        (src / "a.md").write_text("first para\n\nsecond para\n")
        (src / "sub" / "b.txt").write_text("\n\n".join(c * 1000 for c in "xyz"))
        (src / "skip.bin").write_text("ignored")
        router = self.make_router()
        out = self.call(router, "router_mine",
                        {"dir": str(src), "scope": ["acme"], "wing": "w", "room": "r"})
        self.assertEqual((out["files"], out["chunks"]), (2, 4))
        self.assertEqual(out["by_target"]["acme"]["filed"], 4)
        self.assertEqual(len(self.acme.drawers), 4)
        self.assertIn("mempalace_mine", self.names(self.local))
        self.assertEqual(self.local.calls[0][1], {"path": str(src)})
        rows = router.ledger.lookup(out["job_id"])
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["mine_job_id"] for r in rows}, {out["job_id"]})
        sources = [a["source_file"] for n, a in self.acme.calls if n == "mempalace_add_drawer"]
        self.assertEqual(sources, ["a.md", "sub/b.txt", "sub/b.txt", "sub/b.txt"])
        err = self.call(router, "router_mine", {"dir": str(src), "scope": ["acme"]})
        self.assertEqual(err["code"], -32602)

    def test_local_only_tool_ignores_scope(self):
        router = self.make_router()
        out = self.call(router, "mempalace_sync", {"scope": ["acme"]})
        self.assertEqual(self.acme.calls, [])
        self.assertEqual(self.names(self.local), ["mempalace_sync"])
        self.assertNotIn("scope", self.local.calls[0][1])
        self.assertEqual(out["notes"], ["scope ignored for local-only tool"])

    def test_local_down_is_rpc_error(self):
        router = self.make_router()
        self.stop_hub(self.local)
        err = self.call(router, "mempalace_search", {"query": "x", "scope": ["acme"]})
        self.assertEqual(err["code"], -32000)
        self.assertEqual(err["message"], "local_unreachable")
        self.acme.calls.clear()
        err = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme"]})
        self.assertEqual(err["code"], -32000)
        self.assertEqual(self.acme.calls, [])
        self.assertEqual(router.outbox.pending("acme"), [])


class RouterProtocolTests(RouterTestBase):
    def test_initialize_renamed_notification_and_unknown_method(self):
        router = self.make_router()
        out = self.rpc(router, "initialize", {"protocolVersion": "2024-11-05"})
        self.assertEqual(out["result"]["serverInfo"]["name"], "mempalace-router")
        self.assertEqual(out["result"]["protocolVersion"], "2024-11-05")
        self.assertIsNone(router.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(self.rpc(router, "bogus/method")["error"]["code"], -32601)

    def test_id_bound_tools_rejected_with_company_scope(self):
        self.local.drawers["y"] = {"text": "u", "wing": "w", "room": "r"}
        self.local.taxonomy = {"w": {"r": 1}}
        router = self.make_router()
        for tool in ("mempalace_get_drawer", "mempalace_delete_drawer", "mempalace_update_drawer"):
            err = self.call(router, tool, {"drawer_id": "y", "scope": ["acme"]})
            self.assertEqual(err["code"], -32602)
            self.assertEqual(err["message"], "ids are per-palace; use router_retract / local scope")
        self.assertEqual(self.local.calls, [])
        self.assertEqual(self.acme.calls, [])
        out = self.call(router, "mempalace_get_drawer", {"drawer_id": "y"})
        self.assertEqual(out["content"], "u")
        self.assertEqual(self.call(router, "mempalace_delete_drawer", {"drawer_id": "y"})["success"], True)

    def test_mutating_tools_are_local_only_with_company_scope(self):
        router = self.make_router()
        for tool in ("artifact_put", "event_append", "task_create", "create_tunnel", "diary_read"):
            out = self.call(router, f"mempalace_{tool}", {"scope": ["acme"]})
            self.assertEqual(out["notes"], ["scope ignored for local-only tool"])
        self.assertEqual(self.acme.calls, [])
        self.assertEqual(len(self.local.calls), 5)

    def test_unknown_tool_routed_local_only_with_note(self):
        router = self.make_router()
        out = self.call(router, "mempalace_brand_new", {"scope": ["acme"]})
        self.assertEqual(out["notes"], ["unknown tool routed local-only"])
        self.assertEqual(self.acme.calls, [])
        self.assertEqual(self.names(self.local), ["mempalace_brand_new"])

    def test_kg_correction_supersede_company_is_guarded_and_ledgered(self):
        def fact(s, o, frm):
            return {"subject": s, "predicate": "p", "object": o, "valid_from": frm,
                    "valid_to": None, "current": True}

        # company side loses: local is newer
        self.local.facts.append(fact("S1", "NEW", "2026-06-01"))
        self.acme.facts.append(fact("S1", "OLD", "2026-01-01"))
        self.local.facts.append(fact("S2", AWS_KEY, "2026-06-01"))
        self.acme.facts.append(fact("S2", "OLD", "2026-01-01"))
        router = self.make_router()
        out = self.call(router, "mempalace_kg_query", {"entity": "S1", "scope": ["acme"]})
        (corr,) = out["corrections"]
        self.assertEqual((corr["target"], corr["applied"], corr["status"]), ("acme", True, "filed"))
        self.assertEqual(self.call(router, "router_status", {})["ledger_rows"], 1)
        rows = router.ledger.lookup(self.acme._triple_id(self.acme.facts[-1]))
        self.assertEqual((rows[0]["target"], rows[0]["tool"]), ("acme", "mempalace_kg_supersede"))
        self.assertEqual(rows[0]["payload"]["new_object"], "NEW")
        # guarded: the winning object looks like a secret, so it must not reach the company
        before = len([c for c in self.acme.calls if c[0] == "mempalace_kg_supersede"])
        out = self.call(router, "mempalace_kg_query", {"entity": "S2", "scope": ["acme"]})
        (corr,) = out["corrections"]
        self.assertFalse(corr["applied"])
        self.assertEqual(corr["error"], "secret_pattern:aws_access_key")
        after = len([c for c in self.acme.calls if c[0] == "mempalace_kg_supersede"])
        self.assertEqual(before, after)
        self.assertEqual(self.call(router, "router_status", {})["ledger_rows"], 1)

    def test_write_queues_behind_pending_outbox(self):
        router = self.make_router()
        router.outbox.enqueue(target="acme", tool="mempalace_kg_add",
                              arguments={"subject": "S", "predicate": "p", "object": "first"},
                              local_ref=None, call_id="c0")
        out = self.call(router, "mempalace_kg_add",
                        {"subject": "S", "predicate": "p", "object": "second", "scope": ["acme"]})
        self.assertEqual(out["queued_for"], ["acme"])
        self.assertEqual(self.acme.calls, [])
        self.assertEqual([r["arguments"]["object"] for r in router.outbox.pending("acme")],
                         ["first", "second"])
        flushed = self.call(router, "router_flush", {"target": "acme"})
        self.assertEqual(flushed["pushed"], 2)
        self.assertEqual([f["object"] for f in self.acme.facts], ["first", "second"])

    def test_local_write_failure_skips_company(self):
        bad = self.start_hub(DrawerHub(token="lt", fail_tools={"mempalace_add_drawer", "mempalace_mine"}))
        self.targets = self.make_targets(bad, self.acme)
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme"]})
        self.assertEqual(out["company_skipped"], "local write failed")
        self.assertFalse(out["success"])
        self.assertEqual(self.acme.calls, [])
        src = self.tmp / "m"
        src.mkdir()
        (src / "a.md").write_text("hello")
        out = self.call(router, "router_mine",
                        {"dir": str(src), "scope": ["acme"], "wing": "w", "room": "r"})
        self.assertEqual(out["company_skipped"], "local write failed")
        self.assertEqual(self.acme.calls, [])

    def test_taxonomy_unavailable_is_not_cached_or_aliased(self):
        down = self.start_hub(DrawerHub(token="at", fail_tools={"mempalace_get_taxonomy"}))
        self.targets = self.make_targets(self.local, down)
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "k8s", "room": "notes", "content": "x", "scope": ["acme"]})
        self.assertIn("taxonomy unavailable for acme; names unmapped", out["notes"])
        (drawer,) = down.drawers.values()
        self.assertEqual((drawer["wing"], drawer["room"]), ("k8s", "notes"))
        self.assertEqual(router.taxmap("acme").wings, {})
        self.assertEqual(router._remote_tax, {})

    def test_two_targets_of_same_company_rejected(self):
        extra = Target("acme2", "company", "Acme", self.acme.url, self.cred("acme2", "at"), None, {})
        self.targets.by_name["acme2"] = extra
        self.targets.companies["acme2"] = extra
        router = self.make_router()
        err = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme", "acme2"]})
        self.assertEqual((err["code"], err["message"]), (-32602, "one target per company in scope"))
        self.assertEqual(self.local.calls, [])

    def test_mine_frontmatter_wing_room_with_argument_override(self):
        src = self.tmp / "fm"
        src.mkdir()
        (src / "a.md").write_text("---\nwing: fw\nroom: fr\n---\nbody text\n")
        router = self.make_router()
        out = self.call(router, "router_mine", {"dir": str(src), "scope": ["acme"]})
        self.assertEqual(out["by_target"]["acme"]["filed"], 1)
        (drawer,) = self.acme.drawers.values()
        self.assertEqual((drawer["wing"], drawer["room"], drawer["text"]), ("fw", "fr", "body text"))
        (src / "a.md").write_text("---\nwing: fw\nroom: fr\n---\nother body\n")
        out = self.call(router, "router_mine", {"dir": str(src), "scope": ["acme"], "wing": "aw"})
        self.assertEqual(out["by_target"]["acme"]["filed"], 1)
        self.assertEqual(sorted(d["wing"] for d in self.acme.drawers.values()), ["aw", "fw"])
        (src / "b.txt").write_text("no frontmatter")
        err = self.call(router, "router_mine", {"dir": str(src), "scope": ["acme"]})
        self.assertEqual(err["code"], -32602)

    def test_non_dict_params_rejected(self):
        router = self.make_router()
        out = router.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": ["x"]})
        self.assertEqual(out["error"]["code"], -32602)

    def test_no_remote_id_is_partial_and_not_ledgered(self):
        class NoIdHub(FakeHub):
            def _t_add_drawer(self, a):
                return {"success": True}

        bare = self.start_hub(NoIdHub(token="at"))
        self.targets = self.make_targets(self.local, bare)
        router = self.make_router()
        out = self.call(router, "mempalace_add_drawer",
                        {"wing": "w", "room": "r", "content": "x", "scope": ["acme"]})
        self.assertEqual(out["partial"], {"acme": "no remote id"})
        self.assertEqual(self.call(router, "router_status", {})["ledger_rows"], 0)

    def test_tool_schemas_omit_empty_required(self):
        router = self.make_router()
        tools = {t["name"]: t for t in self.rpc(router, "tools/list")["result"]["tools"]}
        self.assertNotIn("required", tools["router_targets"]["inputSchema"])
        self.assertEqual(tools["router_flush"]["inputSchema"]["required"], ["target"])

    def test_list_wings_returns_by_target_and_local_top_level(self):
        self.acme.taxonomy = {"w": {"r": 2}}
        router = self.make_router()
        out = self.call(router, "mempalace_list_wings", {"scope": ["acme"]})
        self.assertEqual(out["by_target"]["acme"], {"wings": {"w": 2}})
        self.assertEqual(out["wings"], {})

    def test_flush_all_swallows_errors(self):
        router = self.make_router()
        self.stop_hub(self.acme)
        router.outbox.enqueue(target="acme", tool="mempalace_kg_add",
                              arguments={"subject": "S", "predicate": "p", "object": "o"},
                              local_ref=None, call_id="c1")
        router.flush_all()
        self.assertEqual(len(router.outbox.pending("acme")), 1)


if __name__ == "__main__":
    unittest.main()
