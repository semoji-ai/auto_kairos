#!/usr/bin/env bash
# 어도비 패널(CEP)이 옛 코드를 물고 있을 때 캐시만 비운다.
#
# **`?v=` 캐시버스터만으로는 부족하다.** 그것은 `index.html` 이 새로 읽힐 때
# 효과가 있는데, CEP 는 `index.html` 자체도 캐시한다. 고쳐도 반영이 안 되고
# 고친 사람은 반영된 줄 안다 — 후보 띠를 넣고도 안 보여 한참 찾았다.
#
# 설정·쿠키·로컬스토리지는 남기고 `Cache`·`Code Cache`·`GPUCache` 만 치운다.
# 지우지 않고 `/tmp` 로 옮기므로 되돌릴 수 있다.
#
#   ⚠️ 애프터이펙트·프리미어를 **닫고** 실행할 것. 열려 있으면 다시 만들어진다.
set -euo pipefail

BASE="$HOME/Library/Caches/CSXS/cep_cache"
[ -d "$BASE" ] || { echo "CEP 캐시 폴더가 없습니다: $BASE"; exit 0; }

if pgrep -x "After Effects" >/dev/null 2>&1 || pgrep -f "Adobe Premiere Pro" >/dev/null 2>&1; then
  echo "⚠️  애프터이펙트/프리미어가 실행 중입니다. 닫고 다시 실행하세요."
  echo "    (열린 채로 비우면 곧바로 다시 만들어져 소용이 없습니다)"
  exit 1
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
BK="${TMPDIR:-/tmp}/cep_cache_backup_$STAMP"
mkdir -p "$BK"
n=0

for d in "$BASE"/*autokairos*; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  for sub in "Cache" "Code Cache" "GPUCache"; do
    if [ -d "$d/$sub" ]; then
      mkdir -p "$BK/$name"
      mv "$d/$sub" "$BK/$name/"
      n=$((n + 1))
    fi
  done
  echo "· $name"
done

if [ "$n" -eq 0 ]; then
  echo "비울 캐시가 없습니다."
else
  echo
  echo "캐시 $n개를 치웠습니다 → $BK"
  echo "패널을 다시 열면 새 코드를 읽습니다."
fi
