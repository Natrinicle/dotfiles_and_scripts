"""In-process fake MemPalace hub for tests.

Mimics a real hub's stateless JSON-RPC 2.0 ``POST /mcp``: tool dicts come
back JSON-encoded in ``result.content[0].text``; a logical failure is
``{"success": false, "error": ...}`` inside that text; wrong or missing
bearer gives HTTP 401; ``GET /healthz`` answers ``ok\\n`` without auth.
"""

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_TOOLS = {
    "mempalace_search": ({"query": {"type": "string"}, "wing": {"type": "string"},
                          "room": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]),
    "mempalace_kg_query": ({"entity": {"type": "string"}}, ["entity"]),
    "mempalace_add_drawer": ({"wing": {"type": "string"}, "room": {"type": "string"},
                              "content": {"type": "string"}}, ["wing", "room", "content"]),
    "mempalace_kg_add": ({"subject": {"type": "string"}, "predicate": {"type": "string"},
                          "object": {"type": "string"}}, ["subject", "predicate", "object"]),
    "mempalace_kg_supersede": ({"subject": {"type": "string"}, "predicate": {"type": "string"},
                                "old_object": {"type": "string"},
                                "new_object": {"type": "string"}},
                               ["subject", "predicate", "old_object", "new_object"]),
    "mempalace_kg_invalidate": ({"subject": {"type": "string"}, "predicate": {"type": "string"},
                                 "object": {"type": "string"}},
                                ["subject", "predicate", "object"]),
    "mempalace_delete_drawer": ({"drawer_id": {"type": "string"}}, ["drawer_id"]),
    "mempalace_list_wings": ({}, []),
    "mempalace_list_rooms": ({"wing": {"type": "string"}}, []),
    "mempalace_get_taxonomy": ({}, []),
    "mempalace_status": ({}, []),
}


class FakeHub(threading.Thread):
    def __init__(self, *, token="t", latency_s=0.0, fail_tools=frozenset()):
        super().__init__(daemon=True)
        self.token = token
        self.latency_s = latency_s
        self.fail_tools = set(fail_tools)
        self.calls = []
        self.drawers = {}
        self.facts = []
        self.taxonomy = {}
        self._lock = threading.Lock()
        hub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/healthz":
                    self._send(200, b"ok\n", "text/plain")
                else:
                    self._send(404, b"not found\n", "text/plain")

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                if self.headers.get("Authorization") != f"Bearer {hub.token}":
                    self._send(401, json.dumps({"error": "unauthorized"}))
                    return
                if self.path != "/mcp":
                    self._send(404, b"not found\n", "text/plain")
                    return
                req = json.loads(raw)
                if hub.latency_s:
                    time.sleep(hub.latency_s)
                self._send(200, json.dumps(hub._rpc(req)))

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True

    @property
    def url(self):
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def run(self):
        self._server.serve_forever(poll_interval=0.02)

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    # -- JSON-RPC ---------------------------------------------------------

    def _rpc(self, req):
        rid = req.get("id")
        method = req.get("method")
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fake-mempalace", "version": "0"}}
        elif method == "tools/list":
            result = {"tools": [
                {"name": n, "description": n,
                 "inputSchema": {"type": "object", "properties": p, "required": r}}
                for n, (p, r) in _TOOLS.items()]}
        elif method == "tools/call":
            params = req.get("params") or {}
            name, args = params.get("name"), params.get("arguments") or {}
            with self._lock:
                self.calls.append((name, args))
                out = self._tool(name, args)
            result = {"content": [{"type": "text", "text": json.dumps(out)}]}
        else:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _tool(self, name, args):
        if name in self.fail_tools:
            return {"success": False, "error": "forced"}
        if name not in _TOOLS:
            return {"success": False, "error": f"unknown tool: {name}"}
        return getattr(self, "_t_" + name[len("mempalace_"):])(args)

    # -- tools ------------------------------------------------------------

    def _t_search(self, a):
        q = a.get("query", "").lower()
        hits = [(i, d) for i, d in self.drawers.items()
                if q in d["text"].lower()
                and a.get("wing") in (None, d["wing"])
                and a.get("room") in (None, d["room"])]
        results = [{"drawer_id": i, "text": d["text"], "wing": d["wing"], "room": d["room"],
                    "effective_distance": round(0.1 * rank, 6)}
                   for rank, (i, d) in enumerate(hits)]
        return {"query": a.get("query", ""), "results": results[: a.get("limit", 5)]}

    def _t_add_drawer(self, a):
        did = "drawer_" + hashlib.sha256(a["content"].encode()).hexdigest()[:16]
        if did in self.drawers:
            return {"success": True, "drawer_id": did, "already_exists": True}
        self.drawers[did] = {"text": a["content"], "wing": a["wing"], "room": a["room"]}
        rooms = self.taxonomy.setdefault(a["wing"], {})
        rooms[a["room"]] = rooms.get(a["room"], 0) + 1
        return {"success": True, "drawer_id": did, "wing": a["wing"], "room": a["room"]}

    def _t_delete_drawer(self, a):
        d = self.drawers.pop(a.get("drawer_id"), None)
        if d is None:
            return {"success": False, "error": "drawer not found"}
        rooms = self.taxonomy[d["wing"]]
        rooms[d["room"]] -= 1
        if not rooms[d["room"]]:
            del rooms[d["room"]]
        if not rooms:
            del self.taxonomy[d["wing"]]
        return {"success": True, "drawer_id": a["drawer_id"]}

    def _current(self, s, p, o):
        return next((f for f in self.facts if f["subject"] == s and f["predicate"] == p
                     and f["object"] == o and f["current"]), None)

    def _t_kg_add(self, a):
        self.facts.append({"subject": a["subject"], "predicate": a["predicate"],
                           "object": a["object"], "current": True})
        return {"success": True}

    def _t_kg_supersede(self, a):
        old = self._current(a["subject"], a["predicate"], a["old_object"])
        if old is None:
            return {"success": False, "error": "old_object is not a current fact"}
        old["current"] = False
        self.facts.append({"subject": a["subject"], "predicate": a["predicate"],
                           "object": a["new_object"], "current": True})
        return {"success": True}

    def _t_kg_invalidate(self, a):
        fact = self._current(a["subject"], a["predicate"], a["object"])
        if fact is None:
            return {"success": False, "error": "fact is not current"}
        fact["current"] = False
        return {"success": True}

    def _t_kg_query(self, a):
        e = a.get("entity")
        facts = [f for f in self.facts if f["current"] and e in (f["subject"], f["object"])]
        return {"entity": e, "facts": facts, "count": len(facts)}

    def _t_list_wings(self, a):
        return {"wings": {w: sum(r.values()) for w, r in self.taxonomy.items()}}

    def _t_list_rooms(self, a):
        return {"wing": a.get("wing"), "rooms": dict(self.taxonomy.get(a.get("wing"), {}))}

    def _t_get_taxonomy(self, a):
        return {"taxonomy": {w: dict(r) for w, r in self.taxonomy.items()}}

    def _t_status(self, a):
        return {"total_drawers": len(self.drawers), "wings": dict(self._t_list_wings({})["wings"])}
