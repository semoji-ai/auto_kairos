#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  .venv/bin/python - "$ep" <<'PY' > _imggen/${ep}_relck_in.json
import json,sys,pathlib
ep=sys.argv[1]; m=json.load(open('_imggen/ep_map.json'))
D=pathlib.Path([v['dir'] for k,v in m.items() if k.startswith(ep)][0])
sc={s['sceneNumber']:s for s in json.loads((D/'scene_specs.json').read_text(encoding='utf-8'))['scenes']}
led=json.load(open(f'_imggen/{ep}_ledger.json')); es=led.get('scenes',led)
out=[{"n":e['n'],"narration":(sc.get(e['n'],{}).get('narration') or '')[:500],
      "headline":sc.get(e['n'],{}).get('headline'),
      "current_desc":e.get('desc',''),"current_url":e.get('page_url') or e.get('image_url')}
     for e in es if e.get('found') and not (e.get('relevance') or '').strip()]
print(json.dumps({"episode":ep,"items":out},ensure_ascii=False,indent=1))
PY
  n=$(.venv/bin/python -c "import json;print(len(json.load(open('_imggen/${ep}_relck_in.json'))['items']))")
  [ "$n" = "0" ] && { echo "[$ep] 공란 없음"; continue; }
  sed -e "s|__INPUT__|_imggen/${ep}_relck_in.json|" \
      -e "s|__OUTPUT__|_imggen/${ep}_relck.json|" _imggen/relevance_recheck_prompt.txt \
    | codex --search exec --skip-git-repo-check --sandbox workspace-write - \
    >> "_imggen/${ep}_relck.log" 2>&1
  echo "[$ep] 재조사 완료 ${n}건 $(date +%H:%M)"
done
