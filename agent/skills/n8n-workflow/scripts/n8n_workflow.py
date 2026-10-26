#!/usr/bin/env python3
"""Generate n8n workflow JSON, import via the local API, open the canvas."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE = "http://n8n.localhost"
API_KEY_PATH = Path.home() / ".config" / "n8n" / "api.key"
GENERATED_DIR = Path.home() / ".var" / "n8n" / "generated"
TIMEOUT_S = 20


def _uid() -> str:
    return str(uuid.uuid4())


def _node(
    *,
    name: str,
    ntype: str,
    type_version: float,
    position: list[int],
    parameters: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "parameters": parameters,
        "id": _uid(),
        "name": name,
        "type": ntype,
        "typeVersion": type_version,
        "position": position,
    }
    if extra:
        node.update(extra)
    return node


def _link(src: str, dst: str) -> dict[str, Any]:
    return {src: {"main": [[{"node": dst, "type": "main", "index": 0}]]}}


def template_webhook_respond(name: str) -> dict[str, Any]:
    path = name.lower().replace(" ", "-")[:40] or "ping"
    webhook = _node(
        name="Webhook",
        ntype="n8n-nodes-base.webhook",
        type_version=2,
        position=[0, 0],
        parameters={
            "httpMethod": "GET",
            "path": path,
            "responseMode": "responseNode",
            "options": {},
        },
        extra={"webhookId": _uid()},
    )
    respond = _node(
        name="Respond",
        ntype="n8n-nodes-base.respondToWebhook",
        type_version=1.1,
        position=[280, 0],
        parameters={
            "respondWith": "json",
            "responseBody": "={{ { ok: true, ts: $now.toISO() } }}",
        },
    )
    note = _node(
        name="Sticky",
        ntype="n8n-nodes-base.stickyNote",
        type_version=1,
        position=[-320, -40],
        parameters={
            "content": (
                "# Edit this canvas\n"
                f"Webhook path `{path}`. Activate, then GET "
                f"`/webhook/{path}`.\n"
                "Change nodes here; the agent imported this JSON."
            ),
            "height": 260,
            "width": 280,
        },
    )
    return _workflow(name, [note, webhook, respond], _link("Webhook", "Respond"))


def template_schedule_http(name: str, url: str) -> dict[str, Any]:
    sched = _node(
        name="Every 15m",
        ntype="n8n-nodes-base.scheduleTrigger",
        type_version=1.2,
        position=[0, 0],
        parameters={
            "rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}
        },
    )
    http = _node(
        name="HTTP Request",
        ntype="n8n-nodes-base.httpRequest",
        type_version=4.2,
        position=[280, 0],
        parameters={
            "method": "GET",
            "url": url,
            "options": {},
        },
    )
    note = _node(
        name="Sticky",
        ntype="n8n-nodes-base.stickyNote",
        type_version=1,
        position=[-320, -40],
        parameters={
            "content": (
                "# Schedule → HTTP\n"
                f"Every 15 minutes GET `{url}`.\n"
                "Activate to run. Edit the URL on the canvas."
            ),
            "height": 240,
            "width": 280,
        },
    )
    return _workflow(name, [note, sched, http], _link("Every 15m", "HTTP Request"))


def template_ollama_chat(name: str, model: str) -> dict[str, Any]:
    trig = _node(
        name="When clicking ‘Test workflow’",
        ntype="n8n-nodes-base.manualTrigger",
        type_version=1,
        position=[0, 0],
        parameters={},
    )
    body = json.dumps(
        {
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": "Reply with the word pong."}],
        }
    )
    http = _node(
        name="Ollama chat",
        ntype="n8n-nodes-base.httpRequest",
        type_version=4.2,
        position=[300, 0],
        parameters={
            "method": "POST",
            "url": "http://host.docker.internal:11434/api/chat",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": body,
            "options": {},
        },
    )
    note = _node(
        name="Sticky",
        ntype="n8n-nodes-base.stickyNote",
        type_version=1,
        position=[-340, -40],
        parameters={
            "content": (
                "# Local Ollama\n"
                f"POST `host.docker.internal:11434/api/chat` model `{model}`.\n"
                "Test workflow on the canvas. Host Ollama must listen on "
                "`:11434` (all interfaces)."
            ),
            "height": 280,
            "width": 300,
        },
    )
    return _workflow(
        name,
        [note, trig, http],
        _link("When clicking ‘Test workflow’", "Ollama chat"),
    )


def _workflow(
    name: str, nodes: list[dict[str, Any]], connections: dict[str, Any]
) -> dict[str, Any]:
    return {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


TEMPLATES = {
    "webhook-respond": lambda args: template_webhook_respond(args.name),
    "schedule-http": lambda args: template_schedule_http(
        args.name, args.url or "http://host.docker.internal:11434/api/tags"
    ),
    "ollama-chat": lambda args: template_ollama_chat(
        args.name, args.model or "gemma4:latest"
    ),
}


def load_api_key() -> str:
    env = os.environ.get("N8N_API_KEY", "").strip()
    if env:
        return env
    if API_KEY_PATH.is_file():
        return API_KEY_PATH.read_text(encoding="utf-8").strip()
    return ""


def api_request(
    base: str, method: str, path: str, *, key: str, body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    url = base.rstrip("/") + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if key:
        headers["X-N8N-API-KEY"] = key
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = resp.read()
            payload: Any = json.loads(raw.decode("utf-8")) if raw else {}
            return resp.status, payload
    except HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            payload = {"error": raw.decode("utf-8", errors="replace")}
        return exc.code, payload
    except URLError as exc:
        return 0, {"error": str(exc.reason)}


def cmd_health(args: argparse.Namespace) -> int:
    code, payload = api_request(args.base, "GET", "/healthz", key="")
    print(json.dumps({"status_code": code, "body": payload}, indent=2))
    if code != 200:
        print("n8n is not healthy at", args.base, file=sys.stderr)
        return 1
    key = load_api_key()
    acode, _ = api_request(args.base, "GET", "/api/v1/workflows", key="")
    print(json.dumps({"unauth_workflows": acode}))
    if acode not in {401, 403}:
        print("unauthenticated /api/v1/workflows expected 401/403", file=sys.stderr)
    if not key:
        print(
            "no API key yet — create owner, then ~/.config/n8n/api.key", file=sys.stderr
        )
        return 0
    kcode, _ = api_request(args.base, "GET", "/api/v1/workflows", key=key)
    print(json.dumps({"auth_workflows": kcode}))
    return 0 if kcode == 200 else 1


def _write_generated(name: str, workflow: dict[str, Any]) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower())[:60]
    path = GENERATED_DIR / f"{slug or 'workflow'}.json"
    path.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    return path


def cmd_generate(args: argparse.Namespace) -> int:
    if args.file:
        workflow = json.loads(Path(args.file).read_text(encoding="utf-8"))
    else:
        builder = TEMPLATES[args.template]
        workflow = builder(args)
    out = Path(args.out) if args.out else _write_generated(args.name, workflow)
    if args.out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


def _import(base: str, key: str, workflow: dict[str, Any]) -> tuple[int, Any]:
    return api_request(base, "POST", "/api/v1/workflows", key=key, body=workflow)


def _activate(base: str, key: str, workflow_id: str) -> tuple[int, Any]:
    code, payload = api_request(
        base, "POST", f"/api/v1/workflows/{workflow_id}/activate", key=key, body={}
    )
    if code in {200, 201}:
        return code, payload
    return api_request(
        base,
        "PATCH",
        f"/api/v1/workflows/{workflow_id}",
        key=key,
        body={"active": True},
    )


def _open_url(url: str) -> None:
    subprocess.run(
        ["xdg-open", url],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _editor_url(base: str, workflow_id: str) -> str:
    return f"{base.rstrip('/')}/workflow/{workflow_id}"


def cmd_import(args: argparse.Namespace) -> int:
    key = load_api_key()
    if not key:
        print(
            "No n8n API key. Create the owner at "
            f"{args.base}/ then save a key to {API_KEY_PATH}",
            file=sys.stderr,
        )
        return 2
    workflow = json.loads(Path(args.file).read_text(encoding="utf-8"))
    code, payload = _import(args.base, key, workflow)
    if code not in {200, 201}:
        print(
            json.dumps({"status_code": code, "body": payload}, indent=2),
            file=sys.stderr,
        )
        return 1
    workflow_id = str(payload.get("id") or payload.get("data", {}).get("id") or "")
    if args.activate and workflow_id:
        acode, apayload = _activate(args.base, key, workflow_id)
        if acode not in {200, 201}:
            print(
                json.dumps({"activate_status": acode, "body": apayload}, indent=2),
                file=sys.stderr,
            )
    url = _editor_url(args.base, workflow_id) if workflow_id else args.base
    print(url)
    print(f"[Open in n8n]({url})")
    if args.open:
        _open_url(url)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    builder = TEMPLATES[args.template]
    workflow = builder(args)
    path = _write_generated(args.name, workflow)
    print(f"wrote {path}")
    args.file = str(path)
    return cmd_import(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default=os.environ.get("N8N_BASE_URL", DEFAULT_BASE))
    sub = p.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("health", help="GET /healthz and probe API auth")
    h.set_defaults(func=cmd_health)

    g = sub.add_parser("generate", help="Write workflow JSON")
    g.add_argument("--template", choices=sorted(TEMPLATES), default="webhook-respond")
    g.add_argument("--name", default="Generated workflow")
    g.add_argument("--url", default="")
    g.add_argument("--model", default="gemma4:latest")
    g.add_argument("--file", help="Existing JSON instead of a template")
    g.add_argument("--out", default="")
    g.set_defaults(func=cmd_generate)

    i = sub.add_parser("import", help="POST JSON to /api/v1/workflows")
    i.add_argument("--file", required=True)
    i.add_argument("--activate", action="store_true")
    i.add_argument("--open", action="store_true")
    i.set_defaults(func=cmd_import)

    c = sub.add_parser("create", help="Generate, import, print canvas URL")
    c.add_argument("--template", choices=sorted(TEMPLATES), default="webhook-respond")
    c.add_argument("--name", default="Generated workflow")
    c.add_argument("--url", default="")
    c.add_argument("--model", default="gemma4:latest")
    c.add_argument("--activate", action="store_true")
    c.add_argument("--open", action="store_true")
    c.set_defaults(func=cmd_create)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
