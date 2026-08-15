#!/bin/bash
# 중단 지점부터 재개한다. 이미 끝난 단계는 건너뛴다.
# 디스크가 2GB 밑으로 내려가면 멈춘다 — 꽉 차서 한 번 중단된 적이 있다.
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
guard() {
  local free=$(df -m /System/Volumes/Data | awk 'NR==2{print $4}')
  if [ "$free" -lt 2048 ]; then echo "  ✗ 디스크 여유 ${free}MB — 중단"; return 1; fi
  find "$HOME/.codex/generated_images" -mindepth 1 -maxdepth 1 -mtime +0 -exec rm -rf {} + 2>/dev/null
  return 0
}
for ep in "$@"; do
  L="_imggen/${ep}_restyle.log"
  D=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['dir'] for k,v in m.items() if k.startswith('$ep')][0])")
  d=$(echo "$ep" | tr 'A-Z' 'a-z')
  guard || exit 1

  if [ ! -f "_imggen/${ep}_extras.json" ]; then
    echo "[$ep] 1) 무명 인물 조사 $(date +%H:%M)"
    bash _imggen/extras.sh "$ep" >> $L 2>&1
    .venv/bin/python scripts/apply_extras.py "$ep" >> $L 2>&1
    .venv/bin/python scripts/build_image_prompts.py "$D" -o "_imggen/$d" >> $L 2>&1
  fi

  echo "[$ep] 2) 재생성 $(date +%H:%M)"
  .venv/bin/python scripts/gen_scenes.py "$D" "_imggen/$d" -o "_imggen/$d/out" -j 3 >> $L 2>&1
  guard || exit 1

  echo "[$ep] 3) 등록 + 매니페스트"
  .venv/bin/python scripts/publish_regen.py "$ep" --since-hours 24 >> $L 2>&1
  .venv/bin/python auto_agent/scripts/build_manifest.py --local "$D" >> $L 2>&1

  echo "[$ep] 4) 검수 $(date +%H:%M)"
  .venv/bin/python scripts/make_review_input.py "$ep" -o "_imggen/${ep}_review_in.json" >> $L 2>&1
  .venv/bin/python scripts/review_images_gemini.py "_imggen/${ep}_review_in.json" \
      -o "_imggen/${ep}_review.json" >> $L 2>&1
  echo "[$ep] 완료 $(date +%H:%M)"
done
