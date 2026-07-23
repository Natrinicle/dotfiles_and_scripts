# dotfiles_and_scripts

Portable toolkit with two layers:

1. **Environment** — bash startup, modular aliases, authored `~/.local/bin` helpers  
2. **Agent** — Claude/Grok **rules** and **skills** with portable path placeholders  

Optional packaging helpers (`package-toolkit`) keep absolute homes and local
identity out of exports via `${HOME}` / `{…}` placeholders.

## Benefits

| Benefit | Detail |
|---------|--------|
| **Modular aliases** | `shell/bash_aliases.d/*` by concern |
| **Agent portability** | Rules + skills load under `~/.claude` and `~/.grok` |
| **Safe to share** | Secrets and machine-local paths kept out; optional LDAP is example-only |
| **Installable** | `install.sh --shell` / `--agent` / `--all` with backups |
| **Reusable packager** | Ship `package-toolkit` so others can re-export their own trees |

## What's where

```text
.
├── README.md
├── toolkit.yaml
├── install.sh
├── shell/                         # Environment pack
│   ├── bashrc
│   ├── bash_aliases
│   └── bash_aliases.d/
├── bin/                           # Authored scripts (+ voice-recorder)
├── share/                         # Optional unit files / non-PATH assets
├── agent/                         # Shared Claude + Grok pack
│   ├── rules/                     # ~18 rules → ~/.claude/rules + ~/.grok/rules
│   ├── skills/                    # ~32 skills → ~/.claude/skills + ~/.grok/skills
│   ├── PATHS.md                   # {AGENT_HOME}, {MEMORY_ROOT}, bin helpers
│   └── examples/EXCLUDED.md
├── config/
│   ├── local.example.env
│   ├── sanitize-map.yaml
│   └── sanitize-map.example.yaml
└── examples/
    └── ldap.company.example
```

### Environment — alias categories

| File | Role |
|------|------|
| `block` | Disk/SMART, `dd-progress` |
| `compression` | pigz/xz, `extract` |
| `deb_pkg` | apt/dpkg wrappers |
| `direnv` | direnv hook |
| `docker` | image size / registry tags |
| `filesystem` | fsck, open-files, dig-holes, `cpv` |
| `firewall` | ufw cleanup |
| `git` | stats + reset helper |
| `grc` | colored dig/ping/mtr |
| `hardware` | MacBook SMC fan (gated) |
| `ipfs` | IPFS (content-addressed online filesystem) — pin/gc and publish helpers |
| `ipmi` | IPMI chassis helpers |
| `lxc` | optional ksm-wrapper |
| `media` | yt-dlp, ffmpeg, whipper |
| `memory` | mem/swap/zram/ksm stats |
| `network` | nm/ip, dig-short, redirect tests |
| `process` | psgrep / suspend |
| `pyenv` / `python` | pyenv, round, nuitka, venv |
| `ssh` | known_hosts + scp home rc |
| `system` | service, load, dkms-buildall |
| `text` / `utils` | dedup, vercomp, genpass, thefuck |
| `wireguard` | wg helpers |

### Environment — scripts (`bin/` → `~/.local/bin`)

| Script | Benefit to others |
|--------|-------------------|
| `check_all_drives_health` | SMART + FS health table for all disks |
| `adf-ocr.sh` | ADF scan → OCR / local LLM naming |
| `voice-recorder` / `run-voice-recorder.sh` | Ambient mic capture (Silero VAD) → WAV segments; deps in `bin/requirements-voice-recorder.txt` |
| `morning-data-gather` | Batch morning triage (PRs/tickets/IM; calendar if configured) |
| `speakr-api` / `speakr-poll` / `speakr-notes-append` | Speakr recording API helpers |
| `slack-auth-check` | Messaging auth preflight |
| `docker-service-check.sh` | Docker service health check |

Skills reference these as **PATH commands**, not a vendor-specific scripts directory.
See `agent/PATHS.md` for `{MEMORY_ROOT}`, `{AGENT_HOME}`, etc.

### Agent — rules + skills (fully shared)

There is **no** separate Claude vs Grok tree. Both products get the same files:

| Pack path | Installs to |
|-----------|-------------|
| `agent/rules/*` | `~/.claude/rules/` **and** `~/.grok/rules/` |
| `agent/skills/*` | `~/.claude/skills/` **and** `~/.grok/skills/` |

**Rules** include: `code-quality`, `security`, `shell`, `python`, `ansible`,
`terraform`, `helm-k8s`, `iac-plan-analysis`, `otel-instrumentation`,
`model-routing`, `message-scanning`, `readme-freshness`,
`memory-scope-review`, `lazy-load-data` (`{MEMORY_ROOT}`), etc.

**Skills** (~32) include packaging, scanners, PII detection, MemPalace, Tofu
plan review, Speakr (`speakr-manage`, `speakr-scanner`), Jira (`jira-scanner`),
and verification helpers such as `check-work` / `code-review`
(usable on either platform).

Memory paths: resolve `~/.claude/memory` or `~/.grok/memory` (often one
symlinked tree).

[!WARNING] I did not copy these from other employers but had my own AI generate
them based on some of the ideas I came into contact with or based on my own
personal use case. Some of them might not be fully fleshed out because I fed in
ideas and gotchas that I hit to my own but don't have access to these tools
to test them against personally. You might need to iterate a few times and PRs
are definitely welcome!

See `agent/examples/EXCLUDED.md` for large or non-portable items left out of this pack.

## Placeholders

### Environment

| Placeholder | Used for |
|-------------|----------|
| `{default_route_host}` | `keep_network_up` ping target |
| `{nm_connection_name}` | NetworkManager bounce |
| `{firefox_profile}` | yt-dlp browser cookies path |
| `{personal_site}` | Optional media comment URL |
| LDAP `{company_*}` | Only if using the LDAP example |

### Agent / packaging

| Placeholder | Used for |
|-------------|----------|
| `{company}` / `{Company}` | Optional org name in prose templates |
| `{company_domain}` | Email/DNS domain in examples |
| `{app_package}` / `{server_package}` | Optional app path templates |
| `{SECURITY_TICKET_PROJECT}` | Optional issue-tracker project key |
| `{MEMORY_ROOT}` / `{AGENT_HOME}` | Agent config and memory roots |

`${HOME}` remains shell-expandable.

## Install

```bash
cd /path/to/dotfiles_and_scripts
./install.sh --dry-run
./install.sh --all              # shell + bin + agent
# or selectively:
./install.sh --shell --bin
./install.sh --agent
source ~/.bashrc                # after shell install
# restart Claude Code / Grok after --agent
```

Optional directory helpers:

```bash
cp examples/ldap.company.example ~/.bash_aliases.d/ldap
# edit placeholders, then source ~/.bash_aliases
```

## Other `~/.local/bin` inventory (not shipped)

Audited on a typical developer machine. **Most entries are not portable authored scripts.**

| Item | Verdict |
|------|---------|
| **pipx / uv tool shims** (ruff, yt-dlp, esptool, semgrep, …) | Install via package managers; do not vendor symlinks |
| **claude / grok / agent** | CLI installs; not source packs |
| **adf-ocr / check_all_drives_health / voice-recorder** | **Shipped** under `bin/` |
| **Backup / sync-conflict copies of scripts** | Skip |
| **reimage-kdialog** | Useful KDE image batch helper, but **upstream third-party** (GPL); install from upstream / distro packaging if needed |
| **blisp** | Binary firmware tool; distribute upstream |
| **git-delta / device-specific venvs** | Distro/`cargo` or project-local, not this pack |

**Bottom line:** prefer documenting tool installs over copying package-manager links.

## Runtime dependencies (not vendored)

| Component | Expected on the machine |
|-----------|-------------------------|
| Speakr API / DB | Local Speakr install; `SPEAKR_API_BASE`, `SPEAKR_DB`, token under `{MEMORY_ROOT}` |
| Slack scraper auth | Optional `/tmp/slack-scraper/auth.json` (or `SLACK_AUTH_FILE`) |
| `voice-recorder` Python deps | `pip install -r bin/requirements-voice-recorder.txt` (or `VR_PYTHON` venv) |
| Calendar | Optional via `CALENDAR_CMD` or `CALENDAR_ICS_URL` (see morning-data-gather) |

## What is intentionally excluded

- Large office-document skill bundles (`docx` / `pptx` / `xlsx` style packs)  
- Optional directory LDAP (example only, not installed by default)  
- Personal memory files / contact dumps  
- Secrets, SSH keys, swap/sync-conflict files  

## Re-export

```bash
# After editing live agent or shell trees:
python3 agent/skills/package-toolkit/scripts/sanitize-copy.py \
  --dest /tmp/out --map config/sanitize-map.yaml ~/.bashrc

# Keep README aligned (rule: readme-freshness)
```

## License / provenance

Shell config and authored scripts are provided as-is for personal reuse.
Agent rules/skills are instructional templates; fill placeholders for your
environment. Scanner/OCR and drive helpers need packages noted in each script
header (`smartctl`, `sane-utils`, `tesseract`, …).
