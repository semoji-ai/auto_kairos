#!/usr/bin/env bash
# setup_fonts.sh — 대용량 폰트 자동 설치
#
# 전략:
#   1) FontAgent가 설치되어 있으면 FontAgent install 명령으로 다운로드
#   2) FontAgent 없으면 공식 URL에서 직접 curl 다운로드
#
# 수동 실행: bash scripts/setup_fonts.sh
# 자동 실행: .githooks/post-merge 에서 호출

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS_DIR="$REPO_ROOT/remotion/public/fonts"
TEMPLATE_FONTS_DIR="$REPO_ROOT/auto_agent/remotion_template/public/fonts"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

echo "================================================"
echo "  Auto Kairos — 폰트 설치 스크립트"
echo "================================================"

mkdir -p "$FONTS_DIR"
mkdir -p "$TEMPLATE_FONTS_DIR"

# 설치 대상: (폰트에이전트 ID, 소스 파일명, 대상 파일명)
declare -a FONT_IDS=("gongu-13288410" "gongu-13288409")
declare -a SRC_NAMES=("경기천년바탕_Regular.ttf" "경기천년바탕_Bold.ttf")
declare -a DST_NAMES=("GyeonggiMillenniumBatang-Regular.ttf" "GyeonggiMillenniumBatang-Bold.ttf")

all_ok=true

for i in "${!FONT_IDS[@]}"; do
    font_id="${FONT_IDS[$i]}"
    src_name="${SRC_NAMES[$i]}"
    dst_name="${DST_NAMES[$i]}"
    target="$FONTS_DIR/$dst_name"

    if [ -f "$target" ]; then
        echo "  [OK] $dst_name (이미 설치됨)"
        continue
    fi

    installed=false

    # ── 방법 1: FontAgent ──
    if [ -f "$VENV_PYTHON" ] && "$VENV_PYTHON" -c "import fontagent" 2>/dev/null; then
        echo "  [FontAgent] $dst_name 설치 중..."
        TEMP_DIR=$(mktemp -d)
        if "$VENV_PYTHON" -m fontagent.cli install "$font_id" --output-dir "$TEMP_DIR" >/dev/null 2>&1; then
            SRC_FILE="$TEMP_DIR/$src_name"
            if [ -f "$SRC_FILE" ]; then
                cp "$SRC_FILE" "$target"
                echo "  [OK] $dst_name (FontAgent 설치 완료)"
                installed=true
            fi
        fi
        rm -rf "$TEMP_DIR"
    fi

    # ── 방법 2: 직접 다운로드 (공유마당 공식 URL) ──
    if ! $installed; then
        declare -a DIRECT_URLS=(
            "https://gongu.copyright.or.kr/gongu/wrt/cmmn/wrtFileDownload.do?wrtSn=13288410&fileSn=2"
            "https://gongu.copyright.or.kr/gongu/wrt/cmmn/wrtFileDownload.do?wrtSn=13288409&fileSn=2"
        )
        url="${DIRECT_URLS[$i]}"
        echo "  [직접 다운로드] $dst_name ..."
        TEMP_ZIP=$(mktemp --suffix=.zip 2>/dev/null || mktemp -t tmpzip.XXXXXX)
        if command -v curl &>/dev/null && curl -fsSL "$url" -o "$TEMP_ZIP" 2>/dev/null; then
            TEMP_DIR=$(mktemp -d)
            if command -v unzip &>/dev/null && unzip -q "$TEMP_ZIP" -d "$TEMP_DIR" 2>/dev/null; then
                # zip 내부에서 ttf 파일 찾기
                TTF_FILE=$(find "$TEMP_DIR" -name "*.ttf" | grep -i "regular\|bold\|바탕" | head -1 || true)
                if [ -n "$TTF_FILE" ]; then
                    cp "$TTF_FILE" "$target"
                    echo "  [OK] $dst_name (직접 다운로드 완료)"
                    installed=true
                fi
            fi
            rm -rf "$TEMP_DIR" "$TEMP_ZIP"
        else
            rm -f "$TEMP_ZIP"
            echo "  [FAIL] $dst_name 다운로드 실패"
            echo "         FontAgent를 설치하거나 수동으로 폰트를 복사하세요:"
            echo "         $target"
            all_ok=false
        fi
    fi

    # remotion_template 동기화
    template_target="$TEMPLATE_FONTS_DIR/$dst_name"
    if [ -f "$target" ] && [ ! -f "$template_target" ]; then
        cp "$target" "$template_target"
        echo "  [SYNC] remotion_template/$dst_name 복사됨"
    fi
done

echo "================================================"
if $all_ok; then
    echo "  모든 폰트 설치 완료."
else
    echo "  일부 폰트 설치 실패."
    echo "  FontAgent 설치: pip install -e /path/to/fontagent"
fi
echo "================================================"
