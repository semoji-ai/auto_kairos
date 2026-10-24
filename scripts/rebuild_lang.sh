#!/bin/bash
# 언어판 전체 재빌드.  usage: scripts/rebuild_lang.sh <EP 폴더> <lang>
# 화면 문자열 → 래스터 교체 → 형광펜 맞춤 → 공용 에셋 교체 → 타임 워프 → 자막 → 파트 렌더 → 내레이션 미리보기 → 프리미어 층 믹스 → 최종 미리보기 → 한글 검사
set -euo pipefail
cd "$(dirname "$0")/.."
EP="$(cd "$1" && pwd)"; L="$2"; CODE="$(basename "$EP")"; B="$EP/build/$L"
python3 scripts/patch_text.py "$EP" "$L"
rm -f "$B/patch_text_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/patch_text.jsx"
python3 -c "import json,sys; d=json.load(open('$B/patch_text_log.json')); print('patch_text replaced', d['replaced'], 'errors', d['errors'], 'mismatch', d['mismatch']); sys.exit(1 if d['errors'] or d['mismatch'] or d['not_found'] else 0)"
python3 scripts/raster_apply.py "$EP" "$L"
python3 scripts/highlights.py "$EP" "$L"
python3 scripts/swap_assets.py "$EP" "$L"
python3 scripts/timewarp.py "$EP" "$L" --durs "$EP/tts/$L/durs.json" --keep-subs --aep "$B/${CODE}_${L}_swapped.aep"
rm -f "$B/localize_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/localize.jsx"
python3 -c "import json,sys; d=json.load(open('$B/localize_log.json')); print('localize warnings', len(d['warnings']), 'errors', d['errors']); sys.exit(1 if d['errors'] else 0)"
python3 scripts/subtitles.py "$EP" "$L"
rm -f "$B/subtitles_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/subtitles.jsx"
python3 -c "import json,sys; d=json.load(open('$B/subtitles_log.json')); print('subtitles errors', d['errors']); sys.exit(1 if d['errors'] else 0)"
for pid in $(python3 -c "import json; print(' '.join(json.load(open('$B/warp.json'))['parts']))"); do
  read COMP DUR < <(python3 -c "import json; v=json.load(open('$B/warp.json'))['parts']['$pid']; print(v['comp'], round(v['dur_new'],3))")
  scripts/ae/render.sh "$B/${CODE}_${L}_subs.aep" "$COMP" 0 "$DUR" "$EP/render/$L/part_$pid.mp4" 29.97 "H.264 - Match Render Settings - 15 Mbps" | tail -1
done
python3 scripts/preview.py "$EP" "$L" --narration-only
python3 scripts/audio_mix.py "$EP" "$L"
python3 scripts/preview.py "$EP" "$L"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$EP/render/$L/${CODE}_$(echo "$L" | tr a-z A-Z)_preview.mp4"
python3 scripts/qa_hangul.py "$EP" "$L" --step 0.5 || true
echo REBUILD_DONE
