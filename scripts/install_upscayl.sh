#!/usr/bin/env bash
# Upscayl(Real-ESRGAN 계열) 로컬 업스케일러 설치.
#
# API 키가 필요 없고 로컬에서 돈다. `auto_agent/tools/upscale.py` 와
# 어도비 패널의 「⤢ 업스케일」이 이것을 쓴다.
#
# **바이너리와 모델이 서로 다른 저장소에 있다.** upscayl-ncnn 릴리스에는
# 실행 파일만 들어 있어, 그것만 받으면 모델이 없다고 실패한다.
#
#   바이너리  upscayl/upscayl-ncnn  릴리스 zip
#   모델      upscayl/upscayl       resources/models (.bin + .param 한 쌍)
#
# 경로는 `upscale.py` 가 보는 곳에 맞춘다 — 바꾸려면 UPSCAYL_BIN·UPSCAYL_MODELS.
set -euo pipefail

DEST="${UPSCAYL_HOME:-$HOME/.local/share/upscayl}"
REL="${UPSCAYL_RELEASE:-20251207-174704}"

case "$(uname -s)" in
  Darwin) PLAT=macos ;;
  Linux)  PLAT=linux ;;
  *)      echo "지원하지 않는 OS: $(uname -s)"; exit 1 ;;
esac

mkdir -p "$DEST/bin" "$DEST/models"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "· 바이너리 내려받는 중 ($PLAT, $REL)"
curl -fsSL -o "$TMP/upscayl.zip" \
  "https://github.com/upscayl/upscayl-ncnn/releases/download/$REL/upscayl-bin-$REL-$PLAT.zip"
unzip -oq "$TMP/upscayl.zip" -d "$TMP/x"
find "$TMP/x" -name upscayl-bin -type f -exec cp {} "$DEST/bin/upscayl-bin" \;
chmod +x "$DEST/bin/upscayl-bin"

# upscale.py 가 콘텐츠 종류로 고르는 셋. 다른 모델을 쓰려면 여기에 더한다.
#   illustration=digital-art-4x · photo=upscayl-standard-4x · photo_detail=remacri-4x
for m in digital-art-4x upscayl-standard-4x remacri-4x; do
  for ext in bin param; do
    if [ ! -f "$DEST/models/$m.$ext" ]; then
      echo "· 모델 $m.$ext"
      curl -fsSL -o "$DEST/models/$m.$ext" \
        "https://raw.githubusercontent.com/upscayl/upscayl/main/resources/models/$m.$ext"
    fi
  done
done

echo
echo "설치 위치: $DEST"
"$DEST/bin/upscayl-bin" -h 2>&1 | head -2 || true
echo
echo "확인:  python3 -c \"from auto_agent.tools import upscale; print(upscale.upscayl_available(), upscale.available_models())\""
