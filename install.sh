#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
# Auto Kairos — 설치 스크립트 (macOS / Linux / WSL)
# ─────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

info()    { printf "${CYAN}▸${NC} %s\n" "$1"; }
success() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
warn()    { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }
fail()    { printf "${RED}❌ %s${NC}\n" "$1" >&2; exit 1; }

header() {
  printf "\n${BOLD}╔══════════════════════════════════════════════╗${NC}\n"
  printf "${BOLD}║  Auto Kairos v3 — AI Video Production Pipeline ║${NC}\n"
  printf "${BOLD}╚══════════════════════════════════════════════╝${NC}\n\n"
}

# ── OS 감지 ──
detect_os() {
  local uname_s uname_r
  uname_s="$(uname -s)"
  uname_r="$(uname -r 2>/dev/null | tr '[:upper:]' '[:lower:]')" || uname_r=""
  if [[ "$uname_r" == *microsoft* ]]; then printf 'WSL'
  elif [ "$uname_s" = 'Darwin' ]; then printf 'macOS'
  else printf 'Linux'; fi
}

# ── 패키지 매니저 감지 ──
detect_pm() {
  if command -v brew >/dev/null 2>&1; then printf 'brew'
  elif command -v apt-get >/dev/null 2>&1; then printf 'apt'
  elif command -v dnf >/dev/null 2>&1; then printf 'dnf'
  elif command -v pacman >/dev/null 2>&1; then printf 'pacman'
  else printf 'none'; fi
}

# ── Python 확인/설치 ──
ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    local ver
    ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    info "Python $ver 감지됨"
    # 3.10+ 필요
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
      return 0
    fi
    warn "Python 3.10 이상이 필요합니다 (현재 $ver)"
  fi

  info "Python 3.10+ 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install python@3.12 ;;
    apt)    sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv ;;
    dnf)    sudo dnf install -y python3 python3-pip ;;
    pacman) sudo pacman -S --noconfirm python python-pip ;;
    *)      fail "Python을 수동으로 설치해주세요: https://python.org" ;;
  esac
  success "Python 설치 완료"
}

# ── Node.js 확인/설치 ──
ensure_node() {
  if command -v node >/dev/null 2>&1; then
    local ver
    ver="$(node -v)"
    info "Node.js $ver 감지됨"
    return 0
  fi

  info "Node.js 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install node ;;
    apt)    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs ;;
    dnf)    curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash - && sudo dnf install -y nodejs ;;
    pacman) sudo pacman -S --noconfirm nodejs npm ;;
    *)      fail "Node.js를 수동으로 설치해주세요: https://nodejs.org" ;;
  esac
  success "Node.js 설치 완료"
}

# ── ffmpeg 확인/설치 ──
ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1; then
    info "ffmpeg 감지됨"
    return 0
  fi

  info "ffmpeg 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install ffmpeg ;;
    apt)    sudo apt-get install -y ffmpeg ;;
    dnf)    sudo dnf install -y ffmpeg ;;
    pacman) sudo pacman -S --noconfirm ffmpeg ;;
    *)      warn "ffmpeg를 수동으로 설치해주세요: https://ffmpeg.org" ;;
  esac
  success "ffmpeg 설치 완료"
}

# ── auto-kairos 패키지 설치 ──
install_package() {
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  info "auto-kairos 패키지 설치 중..."
  pip3 install -e "${SCRIPT_DIR}[all]" --quiet 2>/dev/null || \
  pip3 install -e "${SCRIPT_DIR}[all]"
  success "auto-kairos 패키지 설치 완료"
}

# ── 워크스페이스 초기화 안내 ──
print_completion() {
  printf "\n"
  success "Auto Kairos v3 설치 완료!"
  printf "\n"
  printf "${BOLD}다음 단계:${NC}\n"
  printf "\n"
  printf "  ${CYAN}# 새 워크스페이스 만들기${NC}\n"
  printf "  auto-kairos init ~/my-video-project\n"
  printf "\n"
  printf "  ${CYAN}# 기존 v2 워크스페이스 업그레이드${NC}\n"
  printf "  auto-kairos init ~/my-video-project --upgrade\n"
  printf "\n"
  printf "  ${CYAN}# 워크스페이스에서 Claude Code 실행${NC}\n"
  printf "  cd ~/my-video-project\n"
  printf "  claude\n"
  printf "\n"
  printf "  ${CYAN}# 대시보드 실행${NC}\n"
  printf "  cd ~/my-video-project && auto-kairos dashboard\n"
  printf "\n"
}

# ── 메인 ──
main() {
  header

  local os
  os="$(detect_os)"
  info "OS: $os"
  info "패키지 매니저: $(detect_pm)"
  printf "\n"

  ensure_python
  ensure_node
  ensure_ffmpeg
  printf "\n"

  install_package
  print_completion
}

main "$@"
