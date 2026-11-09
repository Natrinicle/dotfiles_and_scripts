"""Per-target MemPalace hub client.

Wraps ``mempalace.hub_client.forward_json_rpc`` (stateless JSON-RPC POST to
``/mcp``) and maps every failure onto :class:`HubError` with a ``kind``.
"""

import http.client
import itertools
import json
import socket
import urllib.error
import urllib.request
from typing import Literal

from mempalace_router.config import Target, normalize_hub_url

try:
    from mempalace.hub_client import forward_json_rpc as _forward
except ImportError:  # pragma: no cover - exercised only without mempalace installed

    def _forward(base_url, headers, request, *, timeout=600.0):
        """POST one JSON-RPC request to the hub; return None for an empty body."""
        body = json.dumps(request, ensure_ascii=False).encode("utf-8")
        http_request = urllib.request.Request(f"{base_url}/mcp", data=body, headers=dict(headers))
        with urllib.request.urlopen(http_request, timeout=timeout) as response:
            raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


class HubError(Exception):
    """A hub call failed; ``kind`` says how."""

    def __init__(self, kind: Literal["transport", "auth", "timeout", "rpc", "tool"], detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    return isinstance(exc, urllib.error.URLError) and isinstance(
        exc.reason, (TimeoutError, socket.timeout)
    )


class HubClient:
    """JSON-RPC client for one hub target."""

    def __init__(self, target: Target, *, timeout_s: float = 30.0):
        self.target = target
        self.timeout_s = timeout_s
        self._ids = itertools.count(1)

    def resolve(self) -> tuple[str, dict[str, str]]:
        """Return (base url, request headers) for the target."""
        target = self.target
        if target.palace_path is not None:
            from mempalace.server_registry import (
                client_base_url,
                load_server_tokens,
                read_live_serverinfo,
            )

            info = read_live_serverinfo(str(target.palace_path))
            if info is None:
                raise HubError("transport", f"no live hub for palace {target.palace_path}")
            url = client_base_url(info)
            tokens = load_server_tokens(str(target.palace_path))
            token = tokens[0] if tokens else None
        else:
            if not target.url:
                raise HubError("transport", f"target {target.name} has no url or palace_path")
            url = normalize_hub_url(target.url)
            token = None
            if target.token_file is not None:
                try:
                    token = target.token_file.read_text().strip()
                except OSError as exc:
                    raise HubError("auth", f"cannot read credential file: {exc}") from exc
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return url, headers

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        url, headers = self.resolve()
        request = {"jsonrpc": "2.0", "id": next(self._ids), "method": method}
        if params is not None:
            request["params"] = params
        try:
            response = _forward(url, headers, request, timeout=self.timeout_s)
        except urllib.error.HTTPError as exc:
            try:
                kind = "auth" if exc.code in (401, 403) else "transport"
                raise HubError(kind, f"HTTP {exc.code}") from exc
            finally:
                exc.close()
        except (urllib.error.URLError, OSError) as exc:
            kind = "timeout" if _is_timeout(exc) else "transport"
            raise HubError(kind, str(exc)) from exc
        except http.client.HTTPException as exc:  # BadStatusLine, IncompleteRead, ...
            raise HubError("transport", f"{type(exc).__name__}: {exc}") from exc
        except ValueError as exc:
            raise HubError("rpc", f"invalid JSON response: {exc}") from exc
        if not isinstance(response, dict):
            raise HubError("rpc", "empty response")
        if "error" in response:
            raise HubError("rpc", json.dumps(response["error"]))
        return response.get("result") or {}

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool and return its decoded dict payload."""
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        try:
            text = result["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HubError("rpc", "response has no content text") from exc
        if result.get("isError"):
            raise HubError("tool", text)
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise HubError("rpc", f"tool text is not JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise HubError("rpc", "tool payload is not an object")
        return payload

    def list_tools(self) -> list[dict]:
        """Return the hub's tool descriptors."""
        return list(self._rpc("tools/list").get("tools", []))

    def ping(self) -> bool:
        """True when ``GET /healthz`` answers ``ok``."""
        try:
            url, _ = self.resolve()
            with urllib.request.urlopen(f"{url}/healthz", timeout=self.timeout_s) as response:
                return response.read().decode("utf-8", "replace").strip() == "ok"
        except (HubError, OSError, ValueError, http.client.HTTPException):
            return False
