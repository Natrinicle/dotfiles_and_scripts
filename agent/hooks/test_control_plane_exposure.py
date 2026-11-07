#!/usr/bin/env python3
"""Unit tests for control-plane-exposure.py."""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


def _load():
    path = HOOKS / "control-plane-exposure.py"
    spec = importlib.util.spec_from_file_location("control_plane_exposure", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CP = _load()


def _shell(command: str, tool: str = "run_terminal_command") -> dict:
    return {"tool_name": tool, "tool_input": {"command": command}}


class ControlPlaneExposureTests(unittest.TestCase):
    def test_kubeadm_init_is_denied(self) -> None:
        result = CP.decide(_shell("kubeadm init --pod-network-cidr=192.168.0.0/16"))
        assert result is not None
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("kubeadm init", result["reason"])

    def test_kubeadm_init_phase_certs_is_allowed(self) -> None:
        self.assertIsNone(
            CP.decide(_shell("kubeadm init phase certs apiserver"))
        )

    def test_kubeadm_certs_renew_is_allowed(self) -> None:
        self.assertIsNone(CP.decide(_shell("kubeadm certs renew apiserver")))

    def test_kubeadm_join_is_denied(self) -> None:
        result = CP.decide(_shell("kubeadm join 10.0.0.1:6443 --token x"))
        assert result is not None
        self.assertIn("kubeadm join", result["reason"])

    def test_iptables_drop_is_allowed(self) -> None:
        self.assertIsNone(
            CP.decide(
                _shell(
                    "iptables -I INPUT 1 -i eth0 -p tcp -m multiport "
                    "--dports 6443,10250 -j DROP"
                )
            )
        )

    def test_iptables_accept_is_denied(self) -> None:
        result = CP.decide(
            _shell("iptables -A INPUT -p tcp --dport 6443 -j ACCEPT")
        )
        assert result is not None
        self.assertIn("iptables ACCEPT", result["reason"])

    def test_ufw_allow_6443_is_denied(self) -> None:
        result = CP.decide(_shell("ufw allow 6443/tcp"))
        assert result is not None
        self.assertIn("ufw allow", result["reason"])

    def test_ufw_allow_80_is_allowed(self) -> None:
        self.assertIsNone(CP.decide(_shell("ufw allow 80/tcp")))

    def test_curl_version_probe_is_allowed(self) -> None:
        self.assertIsNone(
            CP.decide(
                _shell("curl -sk --max-time 8 https://203.0.113.9:6443/version")
            )
        )

    def test_kubectl_is_allowed(self) -> None:
        self.assertIsNone(CP.decide(_shell("kubectl get nodes")))

    def test_docker_publish_6443_denied(self) -> None:
        result = CP.decide(_shell("docker run -p 6443:6443 nginx"))
        assert result is not None
        self.assertIn("docker publish", result["reason"])

    def test_docker_loopback_publish_allowed(self) -> None:
        self.assertIsNone(
            CP.decide(_shell("docker run -p 127.0.0.1:6443:6443 nginx"))
        )

    def test_tf_wan_open_denied(self) -> None:
        result = CP.decide(
            {
                "tool_name": "write",
                "tool_input": {
                    "target_file": "/tmp/sg.tf",
                    "contents": (
                        'ingress { from_port = 6443\n'
                        'cidr_blocks = ["0.0.0.0/0"] }'
                    ),
                },
            }
        )
        assert result is not None
        self.assertIn("0.0.0.0/0", result["reason"])

    def test_markdown_mention_allowed(self) -> None:
        self.assertIsNone(
            CP.decide(
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": "/tmp/notes.md",
                        "content": "Do not open 0.0.0.0/0 on :6443",
                    },
                }
            )
        )

    def test_prompt_injects_on_kubeadm(self) -> None:
        result = CP.decide(
            {
                "hook_event_name": "UserPromptSubmit",
                "user_prompt": "spin up a kubernetes cluster on the new cell",
            }
        )
        assert result is not None
        self.assertIn(
            "spin-up gate",
            result["hookSpecificOutput"]["additionalContext"],
        )

    def test_prompt_silent_unrelated(self) -> None:
        self.assertIsNone(
            CP.decide(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "user_prompt": "what time is it",
                }
            )
        )

    def test_escape_hatch(self) -> None:
        old = os.environ.get("SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE")
        os.environ["SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE"] = "1"
        try:
            self.assertIsNone(CP.decide(_shell("kubeadm init")))
        finally:
            if old is None:
                os.environ.pop("SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE", None)
            else:
                os.environ["SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE"] = old


if __name__ == "__main__":
    unittest.main()
