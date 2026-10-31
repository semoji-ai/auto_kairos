#!/bin/bash
# 언어판 전체 재빌드.  usage: scripts/rebuild_lang.sh <EP 폴더> <lang>
# 화면 문자열 → 래스터 교체 → 형광펜 맞춤 → 공용 에셋 교체 → 타임 워프 → 자막 → 파트 렌더 → 내레이션 미리보기 → 프리미어 층 믹스 → 최종 미리보기 → 한글 검사
set -euo pipefail
cd "$(dirname "$0")/.."
EP="$(cd "$1" && pwd)"; L="$2"; CODE="$(basename "$EP")"; B="$EP/build/$L"
FROM="start"
if [ "${3:-}" = "--from" ]; then FROM="${4:-}"; elif [ -n "${3:-}" ]; then echo "알 수 없는 인자: $3 (--from start|subtitles|render)"; exit 1; fi
case "$FROM" in start|subtitles|render) ;; *) echo "--from 값 오류: '$FROM' (start|subtitles|render)"; exit 1;; esac
:   # usage: rebuild_lang.sh <EP> <lang> [--from subtitles|render] — 앞 단계 결과를 그대로 쓰고 그 단계부터
if [ "$FROM" = "start" ]; then
python3 scripts/patch_text.py "$EP" "$L"
rm -f "$B/patch_text_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/patch_text.jsx"
python3 -c "import json,sys; d=json.load(open('$B/patch_text_log.json')); print('patch_text replaced', d['replaced'], 'errors', d['errors'], 'mismatch', d['mismatch'], 'not_found', d['not_found'], 'overflow', d['overflow']); sys.exit(1 if d['errors'] or d['mismatch'] or d['not_found'] else 0)"
python3 scripts/raster_apply.py "$EP" "$L"
python3 scripts/highlights.py "$EP" "$L"
python3 scripts/swap_assets.py "$EP" "$L"
python3 scripts/format_costco.py "$EP" "$L"   # master_config costco_format 있을 때만: 코스트코 포맷(목차 제거·자막바·챕터 판)
python3 scripts/timewarp.py "$EP" "$L" --durs "$EP/tts/$L/durs.json" --keep-subs --aep "$B/${CODE}_${L}_swapped.aep"
rm -f "$B/localize_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/localize.jsx"
python3 -c "import json,sys; d=json.load(open('$B/localize_log.json')); print('localize warnings', len(d['warnings']), 'errors', d['errors']); sys.exit(1 if d['errors'] else 0)"
fi
if [ "$FROM" = "start" ] || [ "$FROM" = "subtitles" ]; then
python3 scripts/subtitles.py "$EP" "$L"
rm -f "$B/subtitles_log.json"; scripts/ae/run.sh "$PWD/scripts/ae/subtitles.jsx"
python3 -c "import json,sys; d=json.load(open('$B/subtitles_log.json')); print('subtitles errors', d['errors']); sys.exit(1 if d['errors'] else 0)"
fi
# 파트 렌더: 기본은 부분 렌더(직전 렌더 대비 바뀐 구간만 AE, 나머지는 이어 붙임). FULL=1이면 전체 렌더.
if [ "${FULL:-0}" = "1" ]; then python3 scripts/render_parts.py "$EP" "$L"; else python3 scripts/render_parts.py "$EP" "$L" --incremental; fi
python3 scripts/preview.py "$EP" "$L" --narration-only
python3 scripts/audio_mix.py "$EP" "$L"
python3 scripts/preview.py "$EP" "$L"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$EP/render/$L/${CODE}_$(echo "$L" | tr a-z A-Z)_preview.mp4"
python3 scripts/qa_hangul.py "$EP" "$L" --step 0.5 || true
# 언어별 삽입 구간(예: 중국어판 도입·결말)이 있으면 새 장면 조립·렌더 → 배경음 → 본편에 이어 붙임
if [ -f "$EP/l10n/${L}_inserts.json" ]; then
  python3 scripts/inserts.py "$EP" "$L" tts
  python3 scripts/inserts.py "$EP" "$L" plan
  python3 scripts/inserts.py "$EP" "$L" build
  python3 scripts/audio_mix.py "$EP" "$L" --bed
  python3 scripts/inserts.py "$EP" "$L" audio
  python3 scripts/inserts.py "$EP" "$L" splice
fi
# 원래 아웃트로가 없는 편: 언어별 아웃트로 클립을 끝에 붙임(master_config append_outro)
python3 scripts/append_outro.py "$EP" "$L"
echo REBUILD_DONE
