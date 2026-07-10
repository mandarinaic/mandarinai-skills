#!/bin/bash
# Symlink every skill in skills/ into the directories that Claude Code,
# Codex CLI, and Gemini CLI scan. Symlinks mean `git pull` updates all CLIs at once.
#
# Usage: ./scripts/install.sh
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_DIR/skills"

# Claude Code reads ~/.claude/skills; Codex and Gemini CLI both read ~/.agents/skills.
TARGETS=("$HOME/.claude/skills" "$HOME/.agents/skills")

for target in "${TARGETS[@]}"; do
    mkdir -p "$target"
    for skill in "$SKILLS_DIR"/*/; do
        name="$(basename "$skill")"
        ln -sfn "${skill%/}" "$target/$name"
        echo "linked $target/$name -> ${skill%/}"
    done
done

echo "Done. Restart your CLI sessions to pick up new skills."
