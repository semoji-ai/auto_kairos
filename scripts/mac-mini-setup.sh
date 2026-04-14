#!/bin/bash
# ============================================================
# Mac Mini 초기 셋업 스크립트
# MacBook의 auto_kairos + 터미널 환경을 그대로 복제
#
# 사용법:
#   1. Mac Mini에서 이 레포를 클론
#   2. bash scripts/mac-mini-setup.sh
# ============================================================

set -e

echo "🖥  Mac Mini 셋업 시작"
echo "================================"

# ── 1. Homebrew ──
echo ""
echo "📦 1/7 Homebrew 설치"
if ! command -v brew &>/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Apple Silicon Mac Mini
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv bash)"
    fi
else
    echo "  이미 설치됨"
fi

# ── 2. Homebrew 패키지 ──
echo ""
echo "📦 2/7 Homebrew 패키지 설치"
BREW_PACKAGES=(
    python@3.12
    ffmpeg
    tmux
    yt-dlp
    deno
)
for pkg in "${BREW_PACKAGES[@]}"; do
    if brew list "$pkg" &>/dev/null; then
        echo "  ✓ $pkg (이미 설치)"
    else
        echo "  설치 중: $pkg"
        brew install "$pkg"
    fi
done

# ── 3. Node.js (수동 설치 — MacBook과 동일 방식) ──
echo ""
echo "📦 3/7 Node.js v22 설치"
NODE_VERSION="22.14.0"
NODE_DIR="$HOME/local/nodejs"

if [[ -f "$NODE_DIR/node-v${NODE_VERSION}-darwin-arm64/bin/node" ]] || [[ -f "$NODE_DIR/node-v${NODE_VERSION}-darwin-x64/bin/node" ]]; then
    echo "  이미 설치됨"
else
    mkdir -p "$NODE_DIR"
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        NODE_ARCH="darwin-arm64"
    else
        NODE_ARCH="darwin-x64"
    fi
    echo "  다운로드 중: node-v${NODE_VERSION}-${NODE_ARCH}"
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-${NODE_ARCH}.tar.xz" | tar -xJ -C "$NODE_DIR"
    echo "  ✓ 설치 완료"
fi

# Node PATH 설정
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    NODE_BIN="$NODE_DIR/node-v${NODE_VERSION}-darwin-arm64/bin"
else
    NODE_BIN="$NODE_DIR/node-v${NODE_VERSION}-darwin-x64/bin"
fi
export PATH="$NODE_BIN:$PATH"

# ── 4. Claude CLI + Global npm 패키지 ──
echo ""
echo "📦 4/7 Claude CLI + npm 글로벌 패키지"
NPM_GLOBALS=(
    "@anthropic-ai/claude-code"
)
for pkg in "${NPM_GLOBALS[@]}"; do
    if npm list -g "$pkg" &>/dev/null 2>&1; then
        echo "  ✓ $pkg (이미 설치)"
    else
        echo "  설치 중: $pkg"
        npm install -g "$pkg"
    fi
done

# ── 5. Python 패키지 + auto_kairos ──
echo ""
echo "📦 5/7 Python 패키지 + auto_kairos 설치"
PIP="$(brew --prefix python@3.12)/bin/python3.12 -m pip"

# auto_kairos 프로젝트 설치 (editable)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "  auto_kairos 설치 (editable)..."
$PIP install --break-system-packages -e "$PROJECT_DIR" 2>&1 | tail -3

# fontagent / chartagent 에이전트 의존성 설치 (없으면 자동 클론)
FONTAGENT_DIR="$HOME/Projects/fontagent"
CHARTAGENT_DIR="$HOME/Projects/chartagent"
FONTAGENT_REPO="https://github.com/semoji-ai/fontagent.git"
CHARTAGENT_REPO="https://github.com/semoji-ai/chartagent.git"

if [ -d "$FONTAGENT_DIR" ]; then
    echo "  fontagent 이미 존재 — 설치 (editable)..."
else
    echo "  fontagent 클론 중..."
    git clone "$FONTAGENT_REPO" "$FONTAGENT_DIR"
fi
if [ -d "$FONTAGENT_DIR" ]; then
    $PIP install --break-system-packages -e "$FONTAGENT_DIR" 2>&1 | tail -2
fi

if [ -d "$CHARTAGENT_DIR" ]; then
    echo "  chartagent 이미 존재 — 설치 (editable)..."
else
    echo "  chartagent 클론 중..."
    git clone "$CHARTAGENT_REPO" "$CHARTAGENT_DIR"
fi
if [ -d "$CHARTAGENT_DIR" ]; then
    $PIP install --break-system-packages -e "$CHARTAGENT_DIR/src" 2>&1 | tail -2
fi

# 추가 패키지 (Phase 1a 의존성)
echo "  YouTube API 패키지..."
$PIP install --break-system-packages google-api-python-client google-auth-oauthlib 2>&1 | tail -1

# ── 6. 셸 설정 ──
echo ""
echo "📦 6/7 셸 설정"
PROFILE="$HOME/.bash_profile"
BASHRC="$HOME/.bashrc"

# .bash_profile
if ! grep -q "nodejs" "$PROFILE" 2>/dev/null; then
    cat >> "$PROFILE" << 'PROFILE_EOF'

# Node.js
export PATH="$HOME/local/nodejs/node-v22.14.0-darwin-arm64/bin:$HOME/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"

# Homebrew
if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv bash)"
else
    eval "$(/usr/local/bin/brew shellenv bash)"
fi
PROFILE_EOF
    echo "  ✓ .bash_profile 업데이트"
else
    echo "  .bash_profile 이미 설정됨"
fi

# ── 7. .env 파일 ──
echo ""
echo "📦 7/7 .env 파일 확인"
ENV_FILE="$PROJECT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "  ⚠️  .env 파일이 이미 있습니다."
    echo "  KAIROS_VAULT_DIR을 NAS 마운트 경로로 변경해야 합니다:"
    grep "KAIROS_VAULT_DIR" "$ENV_FILE"
else
    echo "  .env.example을 복사합니다..."
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
    echo "  ⚠️  .env 파일을 편집하여 API 키를 입력하세요:"
    echo "     nano $ENV_FILE"
fi

# ── Git hooks 활성화 ──
echo ""
echo "🪝 Git hooks 활성화"
git -C "$PROJECT_DIR" config core.hooksPath .githooks
echo "  post-merge hook 활성화 완료 (git pull 후 자동 폰트 설치)"

# ── 폰트 설치 ──
echo ""
echo "🔤 폰트 설치"
bash "$PROJECT_DIR/scripts/setup_fonts.sh"

# ── 완료 ──
echo ""
echo "================================"
echo "✅ Mac Mini 셋업 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. .env 파일 편집 (API 키 + NAS 볼트 경로)"
echo "     nano $PROJECT_DIR/.env"
echo ""
echo "  2. KAIROS_VAULT_DIR을 NAS 마운트 경로로 변경"
echo "     예: KAIROS_VAULT_DIR=/Volumes/NAS/kairos-vault"
echo ""
echo "  3. Claude CLI 로그인"
echo "     claude login"
echo ""
echo "  4. 수집 테스트"
echo "     auto-agent collect --youtube"
echo ""
echo "  5. cron 등록 (인텔리전스 루프)"
echo "     auto-agent cron setup"
