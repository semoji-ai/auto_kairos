#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
run() {
  ep=$1; shift
  D=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['dir'] for k,v in m.items() if k.startswith('$ep')][0])")
  for n in "$@"; do
    PROJECT_DIR="$D" .venv/bin/python auto_agent/scripts/generate_tts.py --scene $n \
      >> "_imggen/${ep}_tts.log" 2>&1 && echo "  $ep 씬 $n ✓" || echo "  $ep 씬 $n ✗"
  done
  echo "[$ep] 완료 $(date +%H:%M)"
}
run EP05 5
run EP09 8
run EP11 1 6 12 14 30 33 42
run EP12 4 9 10 12 14 15 16 17 27 28 33 56 57 58
