#!/bin/bash
# video/public 의 미디어(폰트·이미지·오디오·키트 PNG 등 약 197MB)는 저장소에 넣지 않는다.
# 렌더·Studio 전에 NAS 백업에서 로컬로 받아 온다(이미 있는 파일은 건너뜀).
#   bash motion/video/scripts/fetch_public.sh
#   SEMOJI_NAS=/다른/경로 bash motion/video/scripts/fetch_public.sh
# 원본의 public/pirates 는 저장소에서 public/explainer_demo 로 이름이 바뀌었다.
set -euo pipefail
NAS="${SEMOJI_NAS:-/Volumes/jleavens/007_AI_Projects/semoji-motion_backup_20261007}"
SRC="$NAS/video/public"
DST="$(cd "$(dirname "$0")/.." && pwd)/public"
[ -d "$SRC" ] || { echo "NAS 원본이 없습니다: $SRC (SEMOJI_NAS 로 지정)" >&2; exit 1; }
rsync -a --ignore-existing --exclude .DS_Store --exclude 'pirates/' "$SRC/" "$DST/"
rsync -a --ignore-existing --exclude .DS_Store "$SRC/pirates/" "$DST/explainer_demo/"
echo "public 미디어 동기화 완료: $DST ($(du -sh "$DST" | cut -f1))"
