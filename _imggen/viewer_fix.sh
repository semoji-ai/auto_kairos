#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  sed -e "s|__INPUT__|_imggen/${ep}_viewer_in.json|" \
      -e "s|__REVIEW__|_imggen/${ep}_viewer.json|" \
      -e "s|__OUTPUT__|_imggen/${ep}_fixes.json|" _imggen/viewer_fix_prompt.txt \
    | codex exec --skip-git-repo-check --sandbox workspace-write - \
    >> "_imggen/${ep}_fixes.log" 2>&1
  echo "[$ep] 개선안 완료 $(date +%H:%M)"
done
