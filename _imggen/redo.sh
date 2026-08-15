#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  free=$(df -m /System/Volumes/Data | awk 'NR==2{print $4}')
  [ "$free" -lt 2048 ] && { echo "  ✗ 디스크 ${free}MB — 중단"; exit 1; }
  ns=$(.venv/bin/python -c "
import json;print(','.join(str(x) for x in json.load(open('_imggen/redo_targets.json')).get('$ep',[])))")
  [ -z "$ns" ] && { echo "[$ep] 대상 없음"; continue; }
  D=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['dir'] for k,v in m.items() if k.startswith('$ep')][0])")
  d=$(echo "$ep" | tr 'A-Z' 'a-z')
  echo "[$ep] 재생성 $ns  $(date +%H:%M)"
  .venv/bin/python scripts/gen_scenes.py "$D" "_imggen/$d" -o "_imggen/$d/out" \
      --only "$ns" -j 3 >> "_imggen/${ep}_redo.log" 2>&1
  .venv/bin/python scripts/publish_regen.py "$ep" --since-hours 1 >> "_imggen/${ep}_redo.log" 2>&1
  .venv/bin/python auto_agent/scripts/build_manifest.py --local "$D" >> "_imggen/${ep}_redo.log" 2>&1
  echo "[$ep] 완료 $(date +%H:%M)"
done
