"""Command line entry point: ``mempalace-router``."""

import argparse
import logging
import os
import secrets
import sys
from pathlib import Path

from mempalace_router.config import DEFAULT_CONFIG_PATH, ConfigError, load_targets
from mempalace_router.router import Router
from mempalace_router.transports import run_http, run_stdio

DEFAULT_STATE_DIR = "~/.local/share/mempalace-router"
DEFAULT_CRED_FILE = "~/.config/mempalace-router/token"


def ensure_credential_file(path: Path) -> str:
    """Return the bearer credential at ``path``, minting it (mode 0600) if missing."""
    path = Path(path).expanduser()
    try:
        existing = path.read_text().strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        return existing
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    value = secrets.token_urlsafe(32)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(value + "\n")
    os.replace(tmp, path)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mempalace-router", description="Scope-routed MCP forwarder for MemPalace hubs"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--stdio", action="store_true",
        help="serve newline-delimited JSON-RPC on stdin/stdout (default when stdin is not a TTY)",
    )
    mode.add_argument("--http", action="store_true", help="serve HTTP (default when stdin is a TTY)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="targets YAML (default: %(default)s)")
    parser.add_argument(
        "--state-dir", type=Path, default=Path(DEFAULT_STATE_DIR).expanduser(),
        help="ledger/outbox directory (default: %(default)s)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument(
        "--token-file", type=Path, default=Path(DEFAULT_CRED_FILE).expanduser(), dest="cred_file",
        help="HTTP bearer credential file, minted 0600 if missing (default: %(default)s)",
    )
    parser.add_argument(
        "--check-config", action="store_true",
        help="load the config, ensure the credential file, print 'ok' and exit without serving",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    try:
        targets = load_targets(args.config)
    except ConfigError as exc:
        print(f"mempalace-router: {exc}", file=sys.stderr)
        return 2
    credential = ensure_credential_file(args.cred_file)
    if args.check_config:
        print("ok")
        return 0
    try:
        interactive = sys.stdin.isatty()
    except (ValueError, AttributeError):
        interactive = False
    use_http = args.http or (not args.stdio and interactive)
    router = Router(targets, state_dir=args.state_dir)
    try:
        if use_http:
            run_http(router, host=args.host, port=args.port, token=credential)
        else:
            run_stdio(router)
    except KeyboardInterrupt:
        pass
    finally:
        router.close()
    return 0
