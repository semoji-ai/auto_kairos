#!/bin/bash
# auto_kairos PD — CEP 개발 환경 1회 설정 (macOS)
#  1) CEP 디버그 모드(미서명 익스텐션 허용) 켜기
#  2) 익스텐션을 AE가 읽는 사용자 폴더에 심볼릭 링크
# 주의: AE가 켜져 있으면 종료 후 다시 실행해야 적용됨.
set -e

echo "== 1) CEP PlayerDebugMode ON (CSXS 11, 12) =="
for v in 11 12; do
  defaults write com.adobe.CSXS.$v PlayerDebugMode 1
  echo "   com.adobe.CSXS.$v PlayerDebugMode = 1"
done

echo "== 2) 익스텐션 링크 =="
EXT_DIR="$HOME/Library/Application Support/Adobe/CEP/extensions"
mkdir -p "$EXT_DIR"
SRC="$(cd "$(dirname "$0")/.." && pwd)/cep/com.autokairos.pd"
ln -sfn "$SRC" "$EXT_DIR/com.autokairos.pd"
echo "   $SRC"
echo "   -> $EXT_DIR/com.autokairos.pd"

echo ""
echo "완료. 이제:"
echo "  1) 백엔드 실행:  cd \"$(cd "$(dirname "$0")/.." && pwd)\" && python3 -m backend.app"
echo "  2) After Effects 2026 실행"
echo "  3) 메뉴: Window > Extensions > auto_kairos PD (PoC)"
