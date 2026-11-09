"""Stdio and HTTP MCP transports for :class:`mempalace_router.router.Router`.

Framing mirrors the upstream hub: stdio is newline-delimited JSON-RPC (one JSON
line in, one JSON line out, no Content-Length headers); HTTP is ``POST /mcp``
with a bearer credential, ``GET /healthz`` (open) and ``GET /statusz`` (bearer).
Logs go to stderr only because stdout is the stdio protocol channel.
"""

import hmac
import json
import logging
import sys
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mempalace_router.router import Router

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 8 * 1024 * 1024


def _startup_flush(router: Router) -> None:
    try:
        router.flush_all()
    except Exception:
        log.exception("startup flush failed")


def _parse_error(detail: str) -> dict:
    return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"parse error: {detail}"}}


def _invalid_request() -> dict:
    return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}


def run_stdio(router: Router, stdin=None, stdout=None) -> None:
    """Serve newline-delimited JSON-RPC until ``stdin`` reaches EOF."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    _startup_flush(router)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError as exc:
            reply = _parse_error(str(exc))
        else:
            reply = router.handle(request) if isinstance(request, dict) else _invalid_request()
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def _make_handler(router: Router, bearer: str):
    expected = bearer.encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code: int, body: bytes = b"", ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            scheme, _, given = header.partition(" ")
            if scheme != "Bearer":
                return False
            return hmac.compare_digest(given.strip().encode(), expected)

        def do_GET(self):
            if self.path == "/healthz":
                self._send(200, b"ok\n", "text/plain")
            elif self.path == "/statusz":
                if not self._authorized():
                    self._send(401, b'{"error":"unauthorized"}')
                    return
                reply = router.handle({
                    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "router_status", "arguments": {}},
                })
                if reply is None or "result" not in reply:
                    self._send(500, json.dumps(reply or {}).encode())
                    return
                self._send(200, reply["result"]["content"][0]["text"].encode())
            else:
                self._send(404, b'{"error":"not found"}')

        def do_POST(self):
            if self.path != "/mcp":
                self._send(404, b'{"error":"not found"}')
                return
            if not self._authorized():
                self._send(401, b'{"error":"unauthorized"}')
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send(411, b'{"error":"content-length required"}')
                return
            if length < 0:
                self._send(400, b'{"error":"bad content-length"}')
                return
            if length > MAX_BODY_BYTES:
                self.close_connection = True
                self._send(413, b'{"error":"body too large"}')
                return
            raw = self.rfile.read(length)
            try:
                request = json.loads(raw)
            except ValueError as exc:
                self._send(200, json.dumps(_parse_error(str(exc))).encode())
                return
            reply = router.handle(request) if isinstance(request, dict) else _invalid_request()
            if reply is None:
                self._send(202)
            else:
                self._send(200, json.dumps(reply).encode())

    return Handler


def make_http_server(router: Router, *, host: str, port: int, token: str) -> ThreadingHTTPServer:
    """Bind (without serving) the HTTP server; ``port=0`` picks a free port."""
    return ThreadingHTTPServer((host, port), _make_handler(router, token))


def run_http(
    router: Router,
    *,
    host: str,
    port: int,
    token: str,
    ready: Callable[[ThreadingHTTPServer], None] | None = None,
) -> None:
    """Serve HTTP until ``shutdown()``; ``ready(server)`` fires once bound."""
    _startup_flush(router)
    server = make_http_server(router, host=host, port=port, token=token)
    try:
        if ready is not None:
            ready(server)
        server.serve_forever()
    finally:
        server.server_close()
