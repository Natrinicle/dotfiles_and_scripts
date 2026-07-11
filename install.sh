#!/usr/bin/env bash
# Install environment and/or agent toolkits into the current user's home.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.dotfiles_and_scripts_backup_$(date +%Y%m%d%H%M%S)}"
DRY_RUN=0
DO_SHELL=0
DO_AGENT=0
DO_BIN=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --all           Install shell + bin + agent packs (default if no target flags)
  --shell         Install bashrc / bash_aliases / bash_aliases.d
  --bin           Install bin/* -> ~/.local/bin
  --agent         Install shared agent/rules + agent/skills into Claude and Grok
  --dry-run       Print actions only
  --backup-dir D  Backup directory (default: timestamped under \$HOME)
  -h, --help      Show this help

Shell installs:
  shell/bashrc          -> ~/.bashrc
  shell/bash_aliases    -> ~/.bash_aliases
  shell/bash_aliases.d  -> ~/.bash_aliases.d/  (merge; does not delete extras)
  bin/*                 -> ~/.local/bin/

Agent installs (single shared trees):
  agent/rules/*         -> ~/.claude/rules/  and  ~/.grok/rules/
  agent/skills/*        -> ~/.claude/skills/ and  ~/.grok/skills/

Does not install examples/ unless you copy them yourself.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) DO_SHELL=1; DO_BIN=1; DO_AGENT=1; shift ;;
    --shell) DO_SHELL=1; shift ;;
    --bin) DO_BIN=1; shift ;;
    --agent) DO_AGENT=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --backup-dir) BACKUP_DIR=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ $DO_SHELL -eq 0 && $DO_BIN -eq 0 && $DO_AGENT -eq 0 ]]; then
  DO_SHELL=1
  DO_BIN=1
  DO_AGENT=1
fi

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY: $*"
  else
    "$@"
  fi
}

backup_path() {
  local src=$1
  local rel=${2:-$(basename "$src")}
  if [[ -e $src ]]; then
    run mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
    run cp -a "$src" "$BACKUP_DIR/$rel"
  fi
}

install_tree_merge() {
  local from=$1 to=$2 bsub=$3
  [[ -d $from ]] || return 0
  run mkdir -p "$to"
  local f base
  while IFS= read -r -d '' f; do
    base=${f#"$from"/}
    if [[ -e $to/$base ]]; then
      backup_path "$to/$base" "$bsub/$base"
    fi
    run mkdir -p "$to/$(dirname "$base")"
    run cp -a "$f" "$to/$base"
  done < <(find "$from" -type f -print0)
}

echo "Backup directory: $BACKUP_DIR"

if [[ $DO_SHELL -eq 1 ]]; then
  if [[ -f $ROOT/shell/bashrc ]]; then
    backup_path "$HOME/.bashrc" "shell/bashrc"
    run cp "$ROOT/shell/bashrc" "$HOME/.bashrc"
  fi
  if [[ -f $ROOT/shell/bash_aliases ]]; then
    backup_path "$HOME/.bash_aliases" "shell/bash_aliases"
    run cp "$ROOT/shell/bash_aliases" "$HOME/.bash_aliases"
  fi
  if [[ -d $ROOT/shell/bash_aliases.d ]]; then
    run mkdir -p "$HOME/.bash_aliases.d"
    for f in "$ROOT/shell/bash_aliases.d"/*; do
      [[ -f $f ]] || continue
      base=$(basename "$f")
      if [[ -f $HOME/.bash_aliases.d/$base ]]; then
        backup_path "$HOME/.bash_aliases.d/$base" "shell/bash_aliases.d/$base"
      fi
      run cp "$f" "$HOME/.bash_aliases.d/$base"
    done
  fi
fi

if [[ $DO_BIN -eq 1 ]]; then
  run mkdir -p "$HOME/.local/bin"
  for f in "$ROOT/bin"/*; do
    [[ -f $f ]] || continue
    base=$(basename "$f")
    if [[ -e $HOME/.local/bin/$base ]]; then
      backup_path "$HOME/.local/bin/$base" "bin/$base"
    fi
    run cp "$f" "$HOME/.local/bin/$base"
    run chmod +x "$HOME/.local/bin/$base"
  done
fi

if [[ $DO_AGENT -eq 1 ]]; then
  # Resolve rules directory (prefer shared agent/rules)
  RULES_SRC=""
  if [[ -d $ROOT/agent/rules ]]; then
    RULES_SRC="$ROOT/agent/rules"
  elif [[ -d $ROOT/agent/claude/rules ]]; then
    RULES_SRC="$ROOT/agent/claude/rules"
  fi
  if [[ -n $RULES_SRC ]]; then
    run mkdir -p "$HOME/.claude/rules" "$HOME/.grok/rules"
    install_tree_merge "$RULES_SRC" "$HOME/.claude/rules" "agent/rules"
    install_tree_merge "$RULES_SRC" "$HOME/.grok/rules" "agent/rules-grok"
  fi

  # Resolve skills directory (prefer shared agent/skills)
  SKILLS_SRC=""
  if [[ -d $ROOT/agent/skills ]]; then
    SKILLS_SRC="$ROOT/agent/skills"
  elif [[ -d $ROOT/agent/claude/skills ]]; then
    SKILLS_SRC="$ROOT/agent/claude/skills"
  fi
  if [[ -n $SKILLS_SRC ]]; then
    run mkdir -p "$HOME/.claude/skills" "$HOME/.grok/skills"
    install_tree_merge "$SKILLS_SRC" "$HOME/.claude/skills" "agent/skills"
    install_tree_merge "$SKILLS_SRC" "$HOME/.grok/skills" "agent/skills-grok"
  fi

  # Legacy: agent/grok/skills if still present and not already merged
  if [[ -d $ROOT/agent/grok/skills && ! -d $ROOT/agent/skills ]]; then
    run mkdir -p "$HOME/.grok/skills"
    install_tree_merge "$ROOT/agent/grok/skills" "$HOME/.grok/skills" "agent/grok/skills"
  fi
fi

cat <<EOF

Done.
  Shell:  $DO_SHELL
  Bin:    $DO_BIN
  Agent:  $DO_AGENT

Next steps:
  1. Shell: review {placeholders} in ~/.bash_aliases.d (see config/local.example.env)
  2. Shell: source ~/.bashrc
  3. Agent: restart Claude Code / Grok so rules and skills reload
  4. Agent: fill {company} / {app_package} placeholders if needed

EOF
