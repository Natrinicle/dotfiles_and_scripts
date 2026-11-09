import contextlib
import http.client
import io
import json
import os
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from mempalace_router import cli, transports
from mempalace_router.test_router import RouterTestBase
from mempalace_router.transports import MAX_BODY_BYTES, make_http_server, run_http, run_stdio

BEARER = "unit-test-bearer"


class TransportTests(RouterTestBase):
    def start_http(self):
        router = self.make_router()
        ready = threading.Event()
        box = {}

        def on_ready(server):
            box["server"] = server
            ready.set()

        thread = threading.Thread(
            target=run_http, args=(router,),
            kwargs={"host": "127.0.0.1", "port": 0, "token": BEARER, "ready": on_ready},
        )
        thread.start()
        self.assertTrue(ready.wait(10))
        server = box["server"]

        def stop():
            server.shutdown()
            thread.join()

        self.addCleanup(stop)
        return server.server_address[1]

    def start_http_with(self, bearer):
        router = self.make_router()
        server = make_http_server(router, host="127.0.0.1", port=0, token=bearer)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()

        def stop():
            server.shutdown()
            thread.join()
            server.server_close()

        self.addCleanup(stop)
        return server.server_address[1]

    def test_http_rejects_empty_bearer_when_expected_empty(self):
        port = self.start_http_with("")
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        for header in ("Bearer ", "Bearer"):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            self.addCleanup(conn.close)
            conn.request("POST", "/mcp", body=body, headers={"Authorization": header})
            resp = conn.getresponse()
            resp.read()
            self.assertEqual(resp.status, 401)

    def test_http_oversize_body_413(self):
        port = self.start_http()
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        self.addCleanup(conn.close)
        conn.putrequest("POST", "/mcp")
        conn.putheader("Authorization", f"Bearer {BEARER}")
        conn.putheader("Content-Length", str(MAX_BODY_BYTES + 1))
        conn.endheaders()
        resp = conn.getresponse()
        resp.read()
        self.assertEqual(resp.status, 413)

    def test_stdio_blank_lines_skipped(self):
        stdout = io.StringIO()
        line = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        run_stdio(self.make_router(), io.StringIO(f"\n  \n{line}\n\n"), stdout)
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)

    def request(self, port, method, path, body=None, auth=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        self.addCleanup(conn.close)
        headers = {"Authorization": f"Bearer {auth}"} if auth else {}
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read()

    def test_stdio_roundtrip_tools_list(self):
        router = self.make_router()
        lines = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        stdin = io.StringIO("".join(json.dumps(x) + "\n" for x in lines))
        stdout = io.StringIO()
        run_stdio(router, stdin, stdout)
        replies = [json.loads(x) for x in stdout.getvalue().splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["result"]["serverInfo"]["name"], "mempalace-router")
        names = {t["name"] for t in replies[1]["result"]["tools"]}
        self.assertIn("router_targets", names)

    def test_stdio_bad_json_gets_parse_error(self):
        stdout = io.StringIO()
        run_stdio(self.make_router(), io.StringIO("{nope\n"), stdout)
        self.assertEqual(json.loads(stdout.getvalue())["error"]["code"], -32700)

    def test_http_requires_bearer(self):
        port = self.start_http()
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(self.request(port, "POST", "/mcp", body)[0], 401)
        self.assertEqual(self.request(port, "POST", "/mcp", body, auth="wrong")[0], 401)
        status, raw = self.request(port, "POST", "/mcp", body, auth=BEARER)
        self.assertEqual(status, 200)
        names = {t["name"] for t in json.loads(raw)["result"]["tools"]}
        self.assertIn("router_status", names)

    def test_http_notification_gets_202(self):
        port = self.start_http()
        body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        status, raw = self.request(port, "POST", "/mcp", body, auth=BEARER)
        self.assertEqual((status, raw), (202, b""))

    def test_http_healthz_ok(self):
        port = self.start_http()
        self.assertEqual(self.request(port, "GET", "/healthz"), (200, b"ok\n"))

    def test_http_statusz_and_404(self):
        port = self.start_http()
        self.assertEqual(self.request(port, "GET", "/statusz")[0], 401)
        status, raw = self.request(port, "GET", "/statusz", auth=BEARER)
        self.assertEqual(status, 200)
        self.assertIsInstance(json.loads(raw), dict)
        self.assertEqual(self.request(port, "GET", "/nope")[0], 404)


class CliTests(unittest.TestCase):
    def test_cli_mints_token_file_0600(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        config = home / "targets.yaml"
        config.write_text("targets:\n  local:\n    kind: local\n    palace_path: ~/palace\n")
        cred = home / ".config" / "mempalace-router" / "cred"
        out = io.StringIO()
        with patch.dict(os.environ, {"HOME": str(home)}), contextlib.redirect_stdout(out):
            rc = cli.main(["--check-config", "--config", str(config), "--token-file", str(cred)])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "ok")
        self.assertEqual(stat.S_IMODE(cred.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(cred.parent.stat().st_mode), 0o700)
        first = cred.read_text()
        self.assertGreaterEqual(len(first.strip()), 32)
        self.assertEqual(cli.ensure_credential_file(cred), first.strip())

    def test_empty_credential_file_is_reminted(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cred = Path(tmp.name) / "cred"
        for blank in ("", "  \n"):
            cred.write_text(blank)
            cred.chmod(0o644)
            value = cli.ensure_credential_file(cred)
            self.assertGreaterEqual(len(value), 32)
            self.assertEqual(cred.read_text().strip(), value)
            self.assertEqual(stat.S_IMODE(cred.stat().st_mode), 0o600)
        self.assertEqual([p.name for p in Path(tmp.name).iterdir()], ["cred"])

    def test_cli_bad_config_exits_2(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = cli.main(["--check-config", "--config", str(Path(tmp.name) / "missing.yaml")])
        self.assertEqual(rc, 2)
        self.assertIn("not found", err.getvalue())


class StartupFlushTests(RouterTestBase):
    def test_stdio_answers_initialize_while_startup_flush_hangs(self):
        router = self.make_router()
        started = threading.Event()

        def slow_flush():
            started.set()
            time.sleep(2)

        class Clock(io.StringIO):
            first = None

            def write(self, text):
                if self.first is None:
                    self.first = time.monotonic()
                return super().write(text)

        stdout = Clock()
        line = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        with patch.object(router, "flush_all", side_effect=slow_flush):
            begin = time.monotonic()
            run_stdio(router, io.StringIO(line + "\n"), stdout)
        self.assertTrue(started.is_set())
        self.assertLess(stdout.first - begin, 1.0)
        self.assertEqual(json.loads(stdout.getvalue())["result"]["serverInfo"]["name"], "mempalace-router")

    def test_startup_flush_runs_in_daemon_thread(self):
        router = self.make_router()
        seen = []
        with patch.object(router, "flush_all", side_effect=lambda: seen.append(threading.current_thread())):
            transports._startup_flush(router).join(5)
        self.assertEqual(len(seen), 1)
        self.assertIsNot(seen[0], threading.main_thread())
        self.assertTrue(seen[0].daemon)

if __name__ == "__main__":
    unittest.main()
