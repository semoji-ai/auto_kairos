#!/bin/bash
# 화풍 재정비 — 무명 인물 조사 → 프롬프트 재빌드 → 전 컷 재생성 → 등록 → 검수
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  L="_imggen/${ep}_restyle.log"
  D=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['dir'] for k,v in m.items() if k.startswith('$ep')][0])")
  d=$(echo "$ep" | tr 'A-Z' 'a-z')

  echo "[$ep] 1) 무명 인물 조사 $(date +%H:%M)"
  bash _imggen/extras.sh "$ep" >> $L 2>&1
  .venv/bin/python scripts/apply_extras.py "$ep" >> $L 2>&1

  echo "[$ep] 2) 프롬프트 재빌드"
  .venv/bin/python scripts/build_image_prompts.py "$D" -o "_imggen/$d" >> $L 2>&1

  echo "[$ep] 3) 전 컷 재생성 $(date +%H:%M)"
  .venv/bin/python scripts/gen_scenes.py "$D" "_imggen/$d" -o "_imggen/$d/out" -j 3 >> $L 2>&1

  echo "[$ep] 4) 등록 + 매니페스트"
  .venv/bin/python scripts/publish_regen.py "$ep" >> $L 2>&1
  .venv/bin/python auto_agent/scripts/build_manifest.py --local "$D" >> $L 2>&1

  echo "[$ep] 5) 검수 $(date +%H:%M)"
  .venv/bin/python scripts/make_review_input.py "$ep" -o "_imggen/${ep}_review_in.json" >> $L 2>&1
  .venv/bin/python scripts/review_images_gemini.py "_imggen/${ep}_review_in.json" \
      -o "_imggen/${ep}_review.json" >> $L 2>&1
  echo "[$ep] 완료 $(date +%H:%M)"
done
