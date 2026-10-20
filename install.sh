#!/usr/bin/env bash
# Installs the discharge-summary-structurer skill into the coding agents on this machine.
# Run from the repo root.
#   ./install.sh                 install for agents detected in your home folder
#   ./install.sh --all           install for every supported agent
#   ./install.sh claude codex    install for the named agents only
#   ./install.sh --project       install into ./.agents/skills and ./.claude/skills
#   ./install.sh --uninstall     remove from every agent folder
set -euo pipefail

NAME=discharge-summary-structurer
SRC=skills/$NAME
[ -f "$SRC/SKILL.md" ] || { echo "error: run this from the repo root ($SRC/SKILL.md not found)" >&2; exit 1; }

# agent | marker that shows it is installed | skills folder
AGENTS="
claude|$HOME/.claude|$HOME/.claude/skills
codex|$HOME/.codex|$HOME/.agents/skills
gemini|$HOME/.gemini|$HOME/.gemini/skills
cursor|$HOME/.cursor|$HOME/.cursor/skills
copilot|$HOME/.copilot|$HOME/.copilot/skills
"

install_to() {  # $1 = label, $2 = skills folder
  local dest="$2/$NAME"
  mkdir -p "$2"
  rm -rf "$dest"
  cp -R "$SRC" "$dest"
  rm -rf "$dest/scripts/__pycache__"
  [ -f "$dest/SKILL.md" ] || { echo "error: install to $dest failed" >&2; exit 1; }
  echo "  ✔ $1 → $dest"
}

mode=detect; picked=()
for a in "$@"; do
  case "$a" in
    --all) mode=all ;;
    --project) mode=project ;;
    --uninstall) mode=uninstall ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) mode=named; picked+=("$a") ;;
  esac
done

if [ "$mode" = project ]; then
  install_to "project (Codex, Cursor, Gemini, VS Code)" .agents/skills
  install_to "project (Claude Code)" .claude/skills
  exit 0
fi

count=0
while IFS='|' read -r agent marker dir; do
  [ -z "$agent" ] && continue
  case "$mode" in
    detect)    [ -d "$marker" ] || continue ;;
    named)     [[ " ${picked[*]} " == *" $agent "* ]] || continue ;;
    uninstall) [ -d "$dir/$NAME" ] && rm -rf "$dir/$NAME" && echo "  ✖ removed $dir/$NAME"; continue ;;
  esac
  install_to "$agent" "$dir"; count=$((count+1))
done <<< "$AGENTS"

[ "$mode" = uninstall ] && exit 0
[ "$count" -eq 0 ] && { echo "No agents detected. Use --all or name one: claude codex gemini cursor copilot"; exit 1; }

# the skill runs a Python script, so check for a usable interpreter
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  echo "Python found: $(python3 --version)"
elif command -v py >/dev/null 2>&1; then
  echo "Python found via the 'py' launcher: $(py --version)"
else
  echo "warning: Python 3.9+ not found. The skill needs it to run scripts/validate.py."
fi
