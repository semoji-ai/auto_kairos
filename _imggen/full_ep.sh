#!/bin/bash
# 한 편을 연출 완성까지 돌린다.
# 순서가 중요하다 — TTS는 시작 시점에 읽은 scene_specs를 끝에 다시 쓴다.
# 뒤에 두면 그 사이의 모든 수정이 날아간다(EP02·EP07에서 실제로 겪음).
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
for key in "$@"; do
  D=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['dir'] for k,v in m.items() if k.startswith('$key')][0])")
  SLUG=$(.venv/bin/python -c "
import json;m=json.load(open('_imggen/ep_map.json'))
print([v['slug'] for k,v in m.items() if k.startswith('$key')][0])")
  L="_imggen/${key}_full.log"
  echo "[$key] 시작 $(date +%H:%M)"

  # 1) 나레이션 전처리 + TTS — scene_specs를 덮어쓰므로 가장 먼저
  .venv/bin/python - <<PY >> $L 2>&1
import json,pathlib,sys
sys.path.insert(0,'.')
import auto_agent.tools.korean_tts_preprocessor as M
pp=[getattr(M,n) for n in dir(M) if isinstance(getattr(M,n),type) and hasattr(getattr(M,n),'process_text')][0]()
D=pathlib.Path('$D'); d=json.loads((D/'scene_specs.json').read_text(encoding='utf-8'))
for s in d.get('scenes',d):
    t=s.get('narration') or ''
    if t.strip(): s['narration_tts']=pp.process_text(t)[0]
(D/'scene_specs.json').write_text(json.dumps(d,ensure_ascii=False,indent=1),encoding='utf-8')
PY
  PROJECT_OUTPUT_DIR="$PWD/$D" PROJECT_DIR="$PWD/$D" PROJECT_NAME="$SLUG" \
    .venv/bin/python -u -m auto_agent.scripts.generate_tts >> $L 2>&1
  echo "[$key] TTS $(ls $D/audio/*.mp3 2>/dev/null | wc -l)개 $(date +%H:%M)"

  # 2) 자료 조사 — 선별해서 전 씬에서 고른다
  .venv/bin/python scripts/select_asset_candidates.py "$D" -o "_imggen/${key}_candidates.json" >> $L 2>&1
  if [ ! -f "_imggen/${key}_search_assets.json" ]; then
    codex --search exec --skip-git-repo-check --sandbox workspace-write "
_imggen/${key}_candidates.json 의 각 씬에 쓸 **실제 사진·문서·사료**를 찾으세요.
현재 source가 generate여도 상관없습니다. 실물이 있으면 실물을 씁니다.

씬마다: 1) 이미지 파일 직접 URL(.jpg/.png, 페이지 아님) 2) 저작권자
3) 라이선스(public_domain/cc_by/cc_by_sa/kogl_type1/press_quote/permission_required)
4) 확인일 2026-08-08 과 확인한 페이지 URL

**직접 열어 확인한 것만 found:true 입니다.**
페이지 대표 이미지가 실제 사진이 아니라 인용구 그래픽이나 로고인 경우가 많습니다.
못 찾았으면 found:false와 이유를 적으세요. 지어내지 마세요.
국사편찬위원회, 국가기록원, 공유마당, 위키미디어 커먼즈, 공공누리를 우선 찾으세요.

5) relevance — **이 자료가 이 씬의 나레이션과 어떻게 직접 이어지는지 한 문장.**

   진짜 사진인 것만으로는 부족합니다. 그 씬의 나레이션을 들은 사람이 이 자료를
   보고 「이게 방금 그 이야기구나」 하고 바로 알아야 합니다.
   「같은 시대라서」「분위기가 맞아서」는 이유가 아닙니다 — 그 정도면 없는 편이
   낫습니다. 시청자가 다른 사건으로 잘못 기억하기 때문입니다.

   실제로 이렇게 틀렸습니다. 셋 다 사진 자체는 진짜였습니다.
     · 부산으로 사업 거점을 옮긴 이야기에 1945년 귀환선 사진 → 한국전쟁 피란으로 읽힘
     · 1940년대 동업 이야기에 2005년 GS 출범식 사진 → 시대가 건너뜀
     · 1931년 개업 이야기에 노년 초상 → 젊은 창업자로 안 보임

   **한 문장으로 못 적겠으면 found:false 입니다.** 개수보다 정확도입니다.

결과를 _imggen/${key}_search_assets.json 에 저장:
{\"scenes\":[{\"n\":5,\"found\":true,\"image_url\":\"\",\"page_url\":\"\",\"holder\":\"\",\"license\":\"\",\"checked\":\"2026-08-08\",\"desc\":\"\",\"relevance\":\"\"}]}
" >> $L 2>&1
  fi
  echo "[$key] 자료조사 $(date +%H:%M)"

  # 2-1) 관련성 관문 — 근거를 못 적은 자료는 여기서 걸린다
  .venv/bin/python scripts/check_asset_relevance.py "$D" \
      --ledger "_imggen/${key}_search_assets.json" --judge \
      -o "_imggen/${key}_relevance.json" >> $L 2>&1 \
    || echo "[$key] ⚠ 관련성 미달 자료 있음 — ${key}_relevance.json 확인"

  # 3) 실물 우선 확정 → 4) 배지·레이아웃 → 5) 채점표 채우기
  .venv/bin/python scripts/enforce_real_first.py "$D" --ledger "_imggen/${key}_search_assets.json" >> $L 2>&1
  .venv/bin/python scripts/apply_direction_fixes.py "$D" >> $L 2>&1
  .venv/bin/python scripts/rubric_autofill.py "$D" >> $L 2>&1
  echo "[$key] 연출 보정 완료 $(date +%H:%M)"

  bash _imggen/score_ep.sh "$key" >> $L 2>&1
  .venv/bin/python -c "
import json
d=json.load(open('_imggen/${key}_score.json'))
print(f\"[$key] 채점 {d['total']}점 {'통과' if d.get('pass') else '미달'}\")" 2>/dev/null || echo "[$key] 채점 실패"
done
