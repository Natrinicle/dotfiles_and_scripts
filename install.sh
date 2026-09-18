#!/usr/bin/env bash
# Install environment and/or agent toolkits into the current user's home.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.dotfiles_and_scripts_backup_$(date +%Y%m%d%H%M%S)}"
DRY_RUN=0
FORCE=0
DO_SHELL=0
DO_AGENT=0
DO_BIN=0
SKIPPED=0
INSTALLED=0
LINKED=0

usage() {
	cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --all           Install shell + bin + agent packs (default if no target flags)
  --shell         Install bashrc / bash_aliases / bash_aliases.d
  --bin           Install bin/* -> ~/.local/bin
  --agent         Install shared agent/rules + agent/skills into Claude; link Grok
  --force         Overwrite existing files (backs up first). Default is skip.
  --dry-run       Print actions only
  --backup-dir D  Backup directory (default: timestamped under \$HOME)
  -h, --help      Show this help

Existing destinations are left alone unless --force. Identical files are
skipped even with --force. Pack stubs will not replace a longer live skill.

Shell installs:
  shell/bashrc          -> ~/.bashrc
  shell/bash_aliases    -> ~/.bash_aliases
  shell/bash_aliases.d  -> ~/.bash_aliases.d/  (merge; does not delete extras)
  bin/*                 -> ~/.local/bin/

Agent installs (single shared trees):
  agent/rules/*         -> ~/.claude/rules/
  agent/skills/*        -> ~/.claude/skills/
  ~/.grok/rules         -> symlink to ~/.claude/rules  (if missing)
  ~/.grok/skills/<name> -> symlink to ~/.claude/skills/<name>

Does not install examples/ unless you copy them yourself.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--all)
		DO_SHELL=1
		DO_BIN=1
		DO_AGENT=1
		shift
		;;
	--shell)
		DO_SHELL=1
		shift
		;;
	--bin)
		DO_BIN=1
		shift
		;;
	--agent)
		DO_AGENT=1
		shift
		;;
	--force)
		FORCE=1
		shift
		;;
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--backup-dir)
		BACKUP_DIR=$2
		shift 2
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "Unknown option: $1" >&2
		usage
		exit 1
		;;
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
	if [[ -e $src || -L $src ]]; then
		run mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
		run cp -a "$src" "$BACKUP_DIR/$rel"
	fi
}

# Copy src -> dest. Never replaces a symlink with a regular file unless --force.
# Identical content is always skipped. Existing different files skip unless --force.
install_file() {
	local src=$1 dest=$2 brel=$3
	local dest_dir
	dest_dir=$(dirname "$dest")

	if [[ -L $dest ]]; then
		if [[ $FORCE -eq 0 ]]; then
			echo "skip symlink: $dest -> $(readlink "$dest")"
			SKIPPED=$((SKIPPED + 1))
			return 0
		fi
		backup_path "$dest" "$brel"
		run rm -f "$dest"
	elif [[ -e $dest ]]; then
		if [[ -f $src && -f $dest ]] && cmp -s "$src" "$dest"; then
			return 0
		fi
		if [[ $FORCE -eq 0 ]]; then
			echo "skip existing: $dest"
			SKIPPED=$((SKIPPED + 1))
			return 0
		fi
		backup_path "$dest" "$brel"
	fi

	run mkdir -p "$dest_dir"
	run cp -a "$src" "$dest"
	INSTALLED=$((INSTALLED + 1))
}

install_tree_merge() {
	local from=$1 to=$2 bsub=$3
	[[ -d $from ]] || return 0
	run mkdir -p "$to"
	local f base
	while IFS= read -r -d '' f; do
		base=${f#"$from"/}
		install_file "$f" "$to/$base" "$bsub/$base"
	done < <(find "$from" -type f -print0)
}

# Point dest at target. Skip if already the correct symlink. Do not replace a
# real directory with a symlink unless --force.
ensure_symlink() {
	local dest=$1 target=$2 brel=$3
	local resolved_dest resolved_target

	if [[ -L $dest ]]; then
		resolved_dest=$(readlink -f "$dest" || true)
		resolved_target=$(readlink -f "$target" || true)
		if [[ -n $resolved_dest && $resolved_dest == "$resolved_target" ]]; then
			return 0
		fi
		if [[ $FORCE -eq 0 ]]; then
			echo "skip grok link (exists): $dest -> $(readlink "$dest")"
			SKIPPED=$((SKIPPED + 1))
			return 0
		fi
		backup_path "$dest" "$brel"
		run rm -f "$dest"
	elif [[ -e $dest ]]; then
		if [[ $FORCE -eq 0 ]]; then
			echo "skip grok path (not a symlink): $dest"
			SKIPPED=$((SKIPPED + 1))
			return 0
		fi
		backup_path "$dest" "$brel"
		run rm -rf "$dest"
	fi

	run mkdir -p "$(dirname "$dest")"
	run ln -sfn "$target" "$dest"
	LINKED=$((LINKED + 1))
}

echo "Backup directory (used only with --force): $BACKUP_DIR"
if [[ $FORCE -eq 0 ]]; then
	echo "Overwrite: off (pass --force to replace existing files)"
fi

if [[ $DO_SHELL -eq 1 ]]; then
	if [[ -f $ROOT/shell/bashrc ]]; then
		install_file "$ROOT/shell/bashrc" "$HOME/.bashrc" "shell/bashrc"
	fi
	if [[ -f $ROOT/shell/bash_aliases ]]; then
		install_file "$ROOT/shell/bash_aliases" "$HOME/.bash_aliases" "shell/bash_aliases"
	fi
	if [[ -d $ROOT/shell/bash_aliases.d ]]; then
		run mkdir -p "$HOME/.bash_aliases.d"
		for f in "$ROOT/shell/bash_aliases.d"/*; do
			[[ -f $f ]] || continue
			base=$(basename "$f")
			install_file "$f" "$HOME/.bash_aliases.d/$base" "shell/bash_aliases.d/$base"
		done
	fi
fi

if [[ $DO_BIN -eq 1 ]]; then
	run mkdir -p "$HOME/.local/bin"
	for f in "$ROOT/bin"/*; do
		[[ -f $f ]] || continue
		base=$(basename "$f")
		dest="$HOME/.local/bin/$base"
		existed=0
		[[ -e $dest ]] && existed=1
		install_file "$f" "$dest" "bin/$base"
		if [[ $existed -eq 0 || $FORCE -eq 1 ]]; then
			if [[ $DRY_RUN -eq 1 ]]; then
				echo "DRY: chmod +x $dest"
			elif [[ -f $dest ]]; then
				chmod +x "$dest"
			fi
		fi
	done
fi

if [[ $DO_AGENT -eq 1 ]]; then
	RULES_SRC=""
	if [[ -d $ROOT/agent/rules ]]; then
		RULES_SRC="$ROOT/agent/rules"
	elif [[ -d $ROOT/agent/claude/rules ]]; then
		RULES_SRC="$ROOT/agent/claude/rules"
	fi
	if [[ -n $RULES_SRC ]]; then
		run mkdir -p "$HOME/.claude/rules"
		install_tree_merge "$RULES_SRC" "$HOME/.claude/rules" "agent/rules"
		ensure_symlink "$HOME/.grok/rules" "$HOME/.claude/rules" "agent/rules-grok"
	fi

	SKILLS_SRC=""
	if [[ -d $ROOT/agent/skills ]]; then
		SKILLS_SRC="$ROOT/agent/skills"
	elif [[ -d $ROOT/agent/claude/skills ]]; then
		SKILLS_SRC="$ROOT/agent/claude/skills"
	fi
	if [[ -n $SKILLS_SRC ]]; then
		run mkdir -p "$HOME/.claude/skills" "$HOME/.grok/skills"
		local_name=""
		for d in "$SKILLS_SRC"/*; do
			[[ -d $d ]] || continue
			local_name=$(basename "$d")
			bundled="$HOME/.grok/bundled/skills/$local_name"
			dest_skill="$HOME/.claude/skills/$local_name"
			if [[ ! -e $dest_skill && -d $bundled && $FORCE -eq 0 ]]; then
				echo "skip bundled shadow: $local_name (pack stub would hide ~/.grok/bundled/skills/$local_name)"
				SKIPPED=$((SKIPPED + 1))
				continue
			fi
			install_tree_merge "$d" "$dest_skill" "agent/skills/$local_name"
			ensure_symlink "$HOME/.grok/skills/$local_name" "$dest_skill" "agent/skills-grok/$local_name"
		done
	fi

	if [[ -d $ROOT/agent/grok/skills && ! -d $ROOT/agent/skills ]]; then
		run mkdir -p "$HOME/.grok/skills"
		install_tree_merge "$ROOT/agent/grok/skills" "$HOME/.grok/skills" "agent/grok/skills"
	fi
fi

cat <<EOF

Done.
  Shell:     $DO_SHELL
  Bin:       $DO_BIN
  Agent:     $DO_AGENT
  Installed: $INSTALLED
  Linked:    $LINKED
  Skipped:   $SKIPPED

Next steps:
  1. Shell: review {placeholders} in ~/.bash_aliases.d (see config/local.example.env)
  2. Shell: source ~/.bashrc
  3. Agent: restart Claude Code / Grok so rules and skills reload
  4. Agent: fill {company} / {app_package} placeholders if needed
  5. Replacing a live skill with a pack stub requires --force

EOF
