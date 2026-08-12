#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  .venv/bin/python - "$ep" <<'PY' > _imggen/${ep}_fill_in.json
import json,sys,pathlib
ep=sys.argv[1]; m=json.load(open('_imggen/ep_map.json'))
D=pathlib.Path([v['dir'] for k,v in m.items() if k.startswith(ep)][0])
sc={s['sceneNumber']:s for s in json.loads((D/'scene_specs.json').read_text(encoding='utf-8'))['scenes']}
res={i['n']:i for i in json.loads(open(f'_imggen/{ep}_relck.json').read().encode().decode('utf-8'))['items']}
out=[]
for n,i in res.items():
    if i['action']!='drop': continue
    s=sc.get(n,{})
    # 앞뒤 씬을 함께 준다 — 같은 화면이 이어지면 지루해진다
    ctx=[{"n":k,"narration":(sc[k].get('narration') or '')[:150],
          "layout":sc[k].get('layout')} for k in (n-1,n+1) if k in sc]
    out.append({"n":n,"narration":s.get('narration') or '',"headline":s.get('headline'),
                "layout":s.get('layout'),"infoStructure":s.get('infoStructure'),
                "duration":s.get('durationSec'),"cast":s.get('cast'),
                "dropped_because":i.get('why',''),"neighbors":ctx})
print(json.dumps({"episode":ep,"items":out},ensure_ascii=False,indent=1))
PY
  n=$(.venv/bin/python -c "import json;print(len(json.load(open('_imggen/${ep}_fill_in.json'))['items']))")
  [ "$n" = "0" ] && { echo "[$ep] 폐기 씬 없음"; continue; }
  sed -e "s|__INPUT__|_imggen/${ep}_fill_in.json|" \
      -e "s|__OUTPUT__|_imggen/${ep}_fill.json|" _imggen/dropped_fill_prompt.txt \
    | codex --search exec --skip-git-repo-check --sandbox workspace-write - \
    >> "_imggen/${ep}_fill.log" 2>&1
  echo "[$ep] 판단 완료 ${n}씬 $(date +%H:%M)"
done
