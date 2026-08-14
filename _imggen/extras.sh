#!/bin/bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for ep in "$@"; do
  .venv/bin/python - "$ep" <<'PY' > _imggen/${ep}_extras_in.json
import json,sys,pathlib
ep=sys.argv[1]; m=json.load(open('_imggen/ep_map.json'))
D=pathlib.Path([v['dir'] for k,v in m.items() if k.startswith(ep)][0])
rost={e['id']:e['name'] for e in json.load(open('_imggen/characters/roster.json'))}
out=[]
for s in json.loads((D/'scene_specs.json').read_text(encoding='utf-8'))['scenes']:
    ia=s.get('imageAsset') or {}
    if ia.get('source')!='generate': continue
    out.append({"n":s['sceneNumber'],"narration":(s.get('narration') or '')[:400],
                "prompt":(ia.get('prompt') or '')[:300],
                "cast":[rost.get(c,c) for c in (s.get('cast') or [])],
                "people_now":s.get('people') or []})
print(json.dumps({"episode":ep,"scenes":out},ensure_ascii=False,indent=1))
PY
  sed -e "s|__INPUT__|_imggen/${ep}_extras_in.json|" \
      -e "s|__OUTPUT__|_imggen/${ep}_extras.json|" _imggen/extras_prompt.txt \
    | codex exec --skip-git-repo-check --sandbox workspace-write - \
    >> "_imggen/${ep}_extras.log" 2>&1
  echo "[$ep] 무명 인물 조사 완료 $(date +%H:%M)"
done
