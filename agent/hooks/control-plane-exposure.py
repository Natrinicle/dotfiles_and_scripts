#!/usr/bin/env python3
"""Deny WAN-opening of Kubernetes / container control-plane ports.

PreToolUse: block kubeadm init/join, k3s/rke2 server install, and opening
:6443 :10250 :2379 :2380 :10257 :10259 :2375 :2376 to the public internet.
UserPromptSubmit: inject the spin-up evidence gate.

Fail-open on parse errors. Escape: SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE=1
after the user named that exception.

kubeadm init phase certs / kubeadm certs / WAN DROP/REJECT stay allowed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

FAIL_OPEN = (
    OSError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    json.JSONDecodeError,
)

PORTS = (6443, 10250, 2379, 2380, 10257, 10259, 2375, 2376)
PORT_RE = r"(?:" + "|".join(str(p) for p in PORTS) + r")"
SHELL_TOOLS = frozenset(
    {"Bash", "bash", "run_terminal_command", "shell", "Shell"}
)
WRITE_TOOLS = frozenset(
    {
        "Write",
        "write",
        "Edit",
        "edit",
        "StrReplace",
        "MultiEdit",
        "search_replace",
    }
)
DOC_SUFFIXES = frozenset({".md", ".txt", ".rst"})
IAC_SUFFIXES = frozenset(
    {".tf", ".tfvars", ".hcl", ".yml", ".yaml", ".json", ".toml"}
)
SKIP_PATH_PARTS = (
    "/rules/",
    "/skills/",
    "/hooks/",
    "/memory/",
    "hookify.",
    "/todo-plans/",
)

KUBEADM_INIT_RE = re.compile(r"\bkubeadm\s+init(?!\s+phase\b)", re.I)
KUBEADM_JOIN_RE = re.compile(r"\bkubeadm\s+join\b", re.I)
K3S_RE = re.compile(
    r"\bk3s\s+server\b|get\.k3s\.io|rancher/install/k3s", re.I
)
RKE2_RE = re.compile(r"\brke2\s+server\b|get\.rke2\.io", re.I)
INSECURE_PORT_RE = re.compile(r"--insecure-port\s*=\s*(?!0\b)\d+", re.I)
DROP_RE = re.compile(
    r"\b(?:DROP|REJECT|drop|reject)\b|\bufw\s+(?:deny|reject|delete)\b", re.I
)
UFW_ALLOW_RE = re.compile(rf"\bufw\s+allow\b[^\n;|&]*\b{PORT_RE}\b", re.I)
IPTABLES_ACCEPT_RE = re.compile(
    rf"\biptables\b[^\n;|&]*\b{PORT_RE}\b[^\n;|&]*\bACCEPT\b"
    rf"|\biptables\b[^\n;|&]*\bACCEPT\b[^\n;|&]*\b{PORT_RE}\b",
    re.I,
)
NFT_ACCEPT_RE = re.compile(
    rf"\bnft\b[^\n;|&]*\b{PORT_RE}\b[^\n;|&]*\baccept\b", re.I
)
WAN_NEAR_PORT_RE = re.compile(
    rf"(?:0\.0\.0\.0/0|::/0).{{0,220}}{PORT_RE}"
    rf"|{PORT_RE}.{{0,220}}(?:0\.0\.0\.0/0|::/0)",
    re.I | re.S,
)
DOCKER_PUBLISH_RE = re.compile(
    rf"(?:-p|--publish)\s+(?:0\.0\.0\.0:)?{PORT_RE}:", re.I
)
DOCKER_LOCAL_PUBLISH_RE = re.compile(
    rf"(?:-p|--publish)\s+127\.0\.0\.1:{PORT_RE}:", re.I
)
PROMPT_RE = re.compile(
    r"kubeadm|\bk3s\b|\brke2\b|kind create|kubernetes cluster|"
    r"new cell|new k8s|helm install|docker compose up|"
    r"spin up|control.?plane|kube-apiserver|kubelet :10250|"
    r"\b6443\b",
    re.I,
)

BLOCK_REASON = (
    "Blocked by system-security / control-plane-exposure: Kubernetes and "
    "container control-plane ports stay off the public internet.\n"
    "Default: API :6443, kubelet :10250, etcd :2379/:2380, scheduler "
    ":10259, controller-manager :10257, Docker :2375/:2376 — VPN / "
    "loopback / cluster overlay only.\n"
    "Do not kubeadm init/join or k3s/rke2 server until the WAN DROP (or "
    "equivalent SG) is in the same change window as extra SANs + a "
    "working VPN kubeconfig. Do not ufw allow / iptables ACCEPT / "
    "0.0.0.0/0 those ports. Do not change --advertise-address to the "
    "VPN IP; DROP on the public NIC instead.\n"
    "Allowed: kubeadm init phase certs, kubeadm certs, iptables/nft "
    "DROP/REJECT of those ports, probes (curl /version), kubectl.\n"
    "Evidence before calling a cell built: listen table + untrusted "
    "non-VPN path cannot reach the control plane. YAML intent is not "
    "evidence.\n"
    "Escape (user must name the exception): "
    "SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE=1"
)

SPINUP_CONTEXT = (
    "system-security spin-up gate: control-plane ports (:6443, :10250, "
    ":2379/:2380, :10257, :10259, Docker :2375/:2376) stay VPN / "
    "loopback / overlay only unless the user named the service public "
    "and auth+TLS are in place. Close WAN on the public NIC; do not "
    "rebind --advertise-address to the VPN IP. Before declaring the "
    "system up: listen table, bind flags, and an untrusted-path probe "
    "that is not 200. Unverified is not private. Load skill "
    "k8s-control-plane-vpn for the sequence. Landing still asks before "
    "SSH/firewall/ACL mutate."
)


def _first(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _tool_name(event: dict[str, Any]) -> str:
    return str(_first(event, "tool_name", "toolName", default="") or "")


def _tool_input(event: dict[str, Any]) -> dict[str, Any]:
    value = _first(event, "tool_input", "toolInput", default={})
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _allow_escape() -> bool:
    return os.environ.get(
        "SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE", ""
    ).strip().lower() in {"1", "true", "yes"}


def _deny_payload(reason: str = BLOCK_REASON) -> dict[str, Any]:
    return {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }


def _prompt_payload() -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": SPINUP_CONTEXT,
        },
        "systemMessage": SPINUP_CONTEXT,
    }


def command_text(event: dict[str, Any]) -> str:
    tool_input = _tool_input(event)
    return str(_first(tool_input, "command", "cmd", default="") or "")


def file_path(event: dict[str, Any]) -> str:
    tool_input = _tool_input(event)
    return str(
        _first(
            tool_input,
            "file_path",
            "target_file",
            "path",
            default="",
        )
        or ""
    )


def file_text(event: dict[str, Any]) -> str:
    tool_input = _tool_input(event)
    parts: list[str] = []
    for key in (
        "new_text",
        "new_string",
        "contents",
        "content",
        "old_string",
        "old_text",
    ):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            parts.append(value)
    return "\n".join(parts)


def user_prompt(event: dict[str, Any]) -> str:
    return str(
        _first(event, "user_prompt", "userPrompt", "prompt", default="") or ""
    )


def skip_file_path(path: str) -> bool:
    if not path:
        return True
    lowered = path.replace("\\", "/").lower()
    suffix = Path(path).suffix.lower()
    if suffix in DOC_SUFFIXES:
        return True
    if any(part in lowered for part in SKIP_PATH_PARTS):
        return True
    if suffix not in IAC_SUFFIXES:
        return True
    return False


def bootstrap_violation(command: str) -> str | None:
    if KUBEADM_INIT_RE.search(command):
        return "kubeadm init"
    if KUBEADM_JOIN_RE.search(command):
        return "kubeadm join"
    if K3S_RE.search(command):
        return "k3s server / installer"
    if RKE2_RE.search(command):
        return "rke2 server / installer"
    if INSECURE_PORT_RE.search(command):
        return "kube-apiserver --insecure-port"
    return None


def open_port_violation(command: str) -> str | None:
    if DROP_RE.search(command):
        return None
    if UFW_ALLOW_RE.search(command):
        return "ufw allow control-plane port"
    if IPTABLES_ACCEPT_RE.search(command):
        return "iptables ACCEPT control-plane port"
    if NFT_ACCEPT_RE.search(command):
        return "nft accept control-plane port"
    if WAN_NEAR_PORT_RE.search(command):
        return "0.0.0.0/0 on a control-plane port"
    if DOCKER_LOCAL_PUBLISH_RE.search(command):
        return None
    if DOCKER_PUBLISH_RE.search(command):
        return "docker publish control-plane port on 0.0.0.0"
    return None


def file_open_violation(path: str, text: str) -> str | None:
    if skip_file_path(path) or not text:
        return None
    if WAN_NEAR_PORT_RE.search(text):
        return f"0.0.0.0/0 near control-plane port in {Path(path).name}"
    return None


def decide_pretool(event: dict[str, Any]) -> dict[str, Any] | None:
    if _allow_escape():
        return None
    tool = _tool_name(event)
    if tool in SHELL_TOOLS:
        command = command_text(event)
        if not command.strip():
            return None
        hit = bootstrap_violation(command) or open_port_violation(command)
        if hit:
            return _deny_payload(f"{BLOCK_REASON}\nMatched: {hit}.")
        return None
    if tool in WRITE_TOOLS:
        path = file_path(event)
        text = file_text(event)
        hit = file_open_violation(path, text)
        if hit:
            return _deny_payload(f"{BLOCK_REASON}\nMatched: {hit}.")
    return None


def decide_prompt(event: dict[str, Any]) -> dict[str, Any] | None:
    text = user_prompt(event)
    if text and PROMPT_RE.search(text):
        return _prompt_payload()
    return None


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    name = str(
        _first(event, "hook_event_name", "hookEventName", default="") or ""
    )
    if name == "UserPromptSubmit":
        return decide_prompt(event)
    return decide_pretool(event)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        if not isinstance(event, dict):
            return 0
        result = decide(event)
    except FAIL_OPEN:
        return 0
    if result:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
