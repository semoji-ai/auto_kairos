#!/usr/bin/env bash
set -euo pipefail
V4_ROOT="${V4_ROOT:-$HOME/LocalProjects/auto_kairos_v4}"
DEST=".claude/skills/v4"
[ -d "$V4_ROOT/skills" ] || { echo "ERROR: V4_ROOT not found: $V4_ROOT/skills" >&2; exit 1; }
SKILLS=(
  strategy-explore fresh-research deep-research wiki-organize
  draft-write target-research review-research
  fact-check proofread vault-search vault-absorb shared
)
mkdir -p "$DEST"
for s in "${SKILLS[@]}"; do
  rsync -av --delete "$V4_ROOT/skills/$s/" "$DEST/$s/"
done
git -C "$V4_ROOT" rev-parse HEAD > "$DEST/VERSION.txt"
echo "Synced v4 skills @ $(cat "$DEST/VERSION.txt")"
