#!/usr/bin/env bash
# =============================================================
# Auto Kairos — 설치 스크립트
# Mac / Linux / Windows (Git Bash / WSL) 지원
# =============================================================
set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

info()  { echo -e "${GREEN}[✓]${RESET} $1"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $1"; }
error() { echo -e "${RED}[✗]${RESET} $1"; }
step()  { echo -e "\n${BOLD}── $1${RESET}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
ERRORS=0

echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Auto Kairos 설치${RESET}"
echo -e "${BOLD}════════════════════════════════════════${RESET}"

# =============================================================
step "1. 시스템 의존성 확인"
# =============================================================

# Python
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        info "Python $PY_VER"
    else
        error "Python 3.10+ 필요 (현재: $PY_VER)"
        ERRORS=$((ERRORS + 1))
    fi
else
    error "Python3 미설치"
    ERRORS=$((ERRORS + 1))
fi

# Node.js
NODE_OK=0
if command -v node &>/dev/null; then
    NODE_VER=$(node -e "console.log(process.versions.node.split('.')[0])")
    if [ "$NODE_VER" -ge 18 ]; then
        info "Node.js v$(node -e "console.log(process.versions.node)")"
        NODE_OK=1
    else
        error "Node.js 18+ 필요 (현재: v$(node -e "console.log(process.versions.node)"))"
        ERRORS=$((ERRORS + 1))
    fi
elif [ -n "$NODEJS_BIN_DIR" ] && [ -x "$NODEJS_BIN_DIR/node" ]; then
    export PATH="$NODEJS_BIN_DIR:$PATH"
    info "Node.js ($NODEJS_BIN_DIR)"
    NODE_OK=1
else
    error "Node.js 미설치"
    echo "  https://nodejs.org 에서 설치하거나 NODEJS_BIN_DIR 환경변수 설정"
    ERRORS=$((ERRORS + 1))
fi

# ffmpeg
if command -v ffmpeg &>/dev/null; then
    info "ffmpeg 설치됨"
else
    warn "ffmpeg 미설치 — 영상 렌더링에 필요"
    echo "  Mac: brew install ffmpeg"
    echo "  Windows: choco install ffmpeg"
    echo "  Linux: sudo apt install ffmpeg"
fi

# Claude Code CLI
if command -v claude &>/dev/null; then
    info "Claude Code CLI 설치됨"
else
    error "Claude Code CLI 미설치 — 파이프라인 실행에 필수"
    echo "  npm install -g @anthropic-ai/claude-code"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo ""
    error "$ERRORS개 필수 의존성이 누락되었습니다. 위 안내에 따라 설치 후 다시 실행하세요."
    exit 1
fi

# =============================================================
step "2. Python 패키지 설치"
# =============================================================

cd "$SCRIPT_DIR"

# pip install (--break-system-packages 필요 시 자동 감지)
if python3 -m pip install -e ".[all]" 2>&1 | tail -3; then
    info "Python 패키지 설치 완료"
else
    warn "일반 설치 실패, --break-system-packages 시도..."
    python3 -m pip install --break-system-packages -e ".[all]" 2>&1 | tail -3
    info "Python 패키지 설치 완료 (system-packages)"
fi

# 추가 의존성
python3 -m pip install python-multipart mutagen 2>/dev/null || \
python3 -m pip install --break-system-packages python-multipart mutagen 2>/dev/null || true

# matplotlib (whisperx 의존성)
python3 -c "import matplotlib" 2>/dev/null || {
    python3 -m pip install matplotlib 2>/dev/null || \
    python3 -m pip install --break-system-packages matplotlib 2>/dev/null || true
}

# whisperx 확인 (선택)
if python3 -c "import whisperx" 2>/dev/null; then
    info "WhisperX 설치됨"
else
    warn "WhisperX 미설치 — 자막 동기화에 필요 (선택: pip install whisperx)"
fi

# =============================================================
step "3. Node.js 패키지 설치 (Remotion)"
# =============================================================

if [ "$NODE_OK" -eq 1 ] && [ -d "$SCRIPT_DIR/remotion" ]; then
    cd "$SCRIPT_DIR/remotion"
    npm install 2>&1 | tail -3
    info "Remotion 패키지 설치 완료"

    # 에디터 번들 빌드
    if [ -f "vite.thumb.config.ts" ]; then
        npx vite build --config vite.thumb.config.ts 2>&1 | tail -2
        npx vite build --config vite.editor.config.ts 2>&1 | tail -2
        info "대시보드 번들 빌드 완료"
    fi
    cd "$SCRIPT_DIR"
else
    warn "Remotion 설치 건너뜀"
fi

# =============================================================
step "4. 환경변수 설정"
# =============================================================

if [ -f "$SCRIPT_DIR/.env" ]; then
    info ".env 파일 존재"
else
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    warn ".env 파일 생성됨 — API 키를 입력하세요: $SCRIPT_DIR/.env"
fi

# 필수 키 확인
MISSING_KEYS=0
for KEY in ELEVENLABS_API_KEY FAL_API_KEY SERPER_API_KEY; do
    VAL=$(grep "^${KEY}=" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
    if [ -z "$VAL" ] || echo "$VAL" | grep -q "YOUR_.*_HERE"; then
        warn "$KEY 미설정"
        MISSING_KEYS=$((MISSING_KEYS + 1))
    else
        info "$KEY ✓"
    fi
done

if [ "$MISSING_KEYS" -gt 0 ]; then
    warn "$MISSING_KEYS개 API 키가 미설정입니다. .env 파일을 편집하세요."
fi

# =============================================================
step "5. 데이터베이스 초기화"
# =============================================================

cd "$SCRIPT_DIR"
if [ -f "auto_agent.db" ]; then
    info "데이터베이스 존재"
else
    python3 -c "
from auto_agent.db.project_manager import ProjectManager
pm = ProjectManager()
print('DB initialized')
" 2>/dev/null && info "데이터베이스 초기화 완료" || warn "DB 초기화 실패 — 첫 실행 시 자동 생성됩니다"
fi

# =============================================================
step "6. 디렉토리 구조 생성"
# =============================================================

mkdir -p "$SCRIPT_DIR/output"
mkdir -p "$SCRIPT_DIR/remotion/public/manifests" 2>/dev/null || true
info "디렉토리 준비 완료"

# =============================================================
step "7. 폰트 설치"
# =============================================================

if [ -f "$SCRIPT_DIR/scripts/setup_fonts.sh" ]; then
    bash "$SCRIPT_DIR/scripts/setup_fonts.sh"
else
    warn "scripts/setup_fonts.sh 없음 — 폰트를 수동으로 설치하세요"
fi

# =============================================================
step "8. Git 훅 활성화"
# =============================================================

if [ -d "$SCRIPT_DIR/.githooks" ]; then
    cd "$SCRIPT_DIR"
    git config core.hooksPath .githooks 2>/dev/null && \
        info "Git 훅 활성화 완료 (.githooks/) — git pull 후 폰트 자동 설치됩니다" || \
        warn "Git 훅 활성화 실패 — git 저장소인지 확인하세요"
    cd - >/dev/null
else
    warn ".githooks/ 없음 — Git 훅을 건너뜁니다"
fi

# =============================================================
step "9. Claude Code 슬래시 스킬 설치"
# =============================================================

# 스킬 소스 디렉토리
SKILL_SRC="$SCRIPT_DIR/skills"

if [ ! -d "$SKILL_SRC" ]; then
    # skills/ 디렉토리가 없으면 생성
    mkdir -p "$SKILL_SRC"
    # 현재 설치된 스킬을 skills/에 복사 (배포용)
    for S in auto-kairos kairos-research kairos-write kairos-product; do
        if [ -f "$SKILLS_DIR/$S/SKILL.md" ]; then
            mkdir -p "$SKILL_SRC/$S"
            cp "$SKILLS_DIR/$S/SKILL.md" "$SKILL_SRC/$S/SKILL.md"
        fi
    done
fi

mkdir -p "$SKILLS_DIR"

SKILL_COUNT=0
for SKILL_NAME in auto-kairos kairos-research kairos-write kairos-product; do
    SRC="$SKILL_SRC/$SKILL_NAME/SKILL.md"
    DEST_DIR="$SKILLS_DIR/$SKILL_NAME"

    if [ -f "$SRC" ]; then
        mkdir -p "$DEST_DIR"
        cp "$SRC" "$DEST_DIR/SKILL.md"
        info "스킬 설치: /$SKILL_NAME"
        SKILL_COUNT=$((SKILL_COUNT + 1))
    fi
done

if [ "$SKILL_COUNT" -gt 0 ]; then
    info "$SKILL_COUNT개 스킬 설치 완료"
else
    warn "스킬 파일이 없습니다. Claude Code에서 직접 사용하려면 ~/.claude/skills/에 수동 설치하세요."
fi

# =============================================================
step "10. 환경변수 프로필 설정"
# =============================================================

echo ""
info "아래 환경변수를 쉘 프로필에 추가하세요:"
echo ""
echo "  export KAIROS_HOME=\"$SCRIPT_DIR\""
if [ "$NODE_OK" -eq 1 ] && [ -n "${NODEJS_BIN_DIR:-}" ]; then
    echo "  export NODE_DIR=\"$NODEJS_BIN_DIR\""
fi
echo ""

# 자동 추가 여부 확인
PROFILE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    PROFILE="$HOME/.zshrc"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PROFILE="$HOME/.bashrc"
else
    PROFILE="$HOME/.bashrc"
fi

if [ -n "$PROFILE" ]; then
    if ! grep -q "KAIROS_HOME" "$PROFILE" 2>/dev/null; then
        read -p "  $PROFILE 에 자동 추가할까요? (y/N) " REPLY
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            echo "" >> "$PROFILE"
            echo "# Auto Kairos" >> "$PROFILE"
            echo "export KAIROS_HOME=\"$SCRIPT_DIR\"" >> "$PROFILE"
            if [ -n "${NODEJS_BIN_DIR:-}" ]; then
                echo "export NODE_DIR=\"$NODEJS_BIN_DIR\"" >> "$PROFILE"
            fi
            info "$PROFILE 에 추가 완료"
        fi
    else
        info "KAIROS_HOME 이미 프로필에 설정됨"
    fi
fi

# =============================================================
step "11. 설치 검증"
# =============================================================

VERIFY_OK=0

# CLI 테스트
if python3 -m auto_agent.cli project list 2>/dev/null | head -3; then
    info "auto-agent CLI 정상 작동"
    VERIFY_OK=$((VERIFY_OK + 1))
else
    warn "auto-agent CLI 확인 실패"
fi

# 매니페스트 빌더 테스트
if python3 -c "from auto_agent.scripts.build_manifest import build_manifest; print('manifest builder OK')" 2>/dev/null; then
    info "매니페스트 빌더 정상"
    VERIFY_OK=$((VERIFY_OK + 1))
fi

# 이미지 도구 테스트
if python3 -c "from auto_agent.tools.image_generate import build_fal_input; print('image tool OK')" 2>/dev/null; then
    info "이미지 생성 도구 정상"
    VERIFY_OK=$((VERIFY_OK + 1))
fi

# =============================================================
echo ""
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  Auto Kairos 설치 완료! ($VERIFY_OK/3 검증 통과)${RESET}"
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo ""
echo "  사용법:"
echo "    auto-agent project create     프로젝트 생성"
echo "    auto-agent run --project X    파이프라인 실행"
echo "    auto-agent dashboard          대시보드 열기 (http://localhost:8080)"
echo ""
echo "  Claude Code 슬래시 스킬:"
echo "    /auto-kairos [주제]           전체 파이프라인"
echo "    /kairos-research [slug]       Stage 1 리서치"
echo "    /kairos-write [slug]          Stage 2 원고+연출"
echo "    /kairos-product [slug]        Stage 3 에셋조립"
echo ""
