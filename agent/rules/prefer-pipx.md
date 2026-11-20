# Prefer pipx for Python CLI tools

When installing a **Python CLI or PyPI app** (`pip install …`, a console script):

1. Use **pipx** (`pipx install`; `pipx inject --include-apps` for extra apps in that venv).
2. Do not use `pip install --user`, `sudo pip`, or apt `python3-<name>` for those tools when pipx can provide the same apps.
3. Native non-Python CLIs stay **apt** (`tshark`, `sigrok-cli`, Debian `binwalk`).

Host binary: `{pipx}` on PATH (often `/usr/bin/pipx`). Apps land in `${HOME}/.local/bin`.

Do not `pipx uninstall` or replace an apt Python library a project already imports unless named.

Palace unique phrase: `pip tools prefer pipx not apt python3-pwntools 2026-11-20`
