#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
# Auto Kairos v3 — 올인원 설치 스크립트
# macOS / Linux / WSL
#
# 1) 시스템 의존성 (Python, Node, ffmpeg)
# 2) pip install auto-kairos
# 3) 워크스페이스 초기화 + v2 업그레이드
# 4) .env 설정 (API 키 + Supabase)
# 5) Supabase 프로젝트 동기화
# ─────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'

info()    { printf "${CYAN}▸${NC} %s\n" "$1"; }
success() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
warn()    { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }
fail()    { printf "${RED}❌ %s${NC}\n" "$1" >&2; exit 1; }
ask()     { printf "${BOLD}? %s${NC} " "$1"; }

header() {
  printf "\n${BOLD}╔═══════════════════════════════════════════════════╗${NC}\n"
  printf "${BOLD}║  Auto Kairos v3 — AI Video Production Pipeline     ║${NC}\n"
  printf "${BOLD}╚═══════════════════════════════════════════════════╝${NC}\n\n"
}

# ── OS/패키지매니저 감지 ──
detect_os() {
  local uname_s uname_r
  uname_s="$(uname -s)"
  uname_r="$(uname -r 2>/dev/null | tr '[:upper:]' '[:lower:]')" || uname_r=""
  if [[ "$uname_r" == *microsoft* ]]; then printf 'WSL'
  elif [ "$uname_s" = 'Darwin' ]; then printf 'macOS'
  else printf 'Linux'; fi
}

detect_platform() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    echo "wsl"
  else
    echo "linux"
  fi
}
PLATFORM=$(detect_platform)

detect_pm() {
  if command -v brew >/dev/null 2>&1; then printf 'brew'
  elif command -v apt-get >/dev/null 2>&1; then printf 'apt'
  elif command -v dnf >/dev/null 2>&1; then printf 'dnf'
  elif command -v pacman >/dev/null 2>&1; then printf 'pacman'
  else printf 'none'; fi
}

# ═══════════════════════════════════════
# Step 1: 시스템 의존성
# ═══════════════════════════════════════

check_python() {
  local py_cmd
  py_cmd=$(command -v python3 || command -v python)
  if [ -z "$py_cmd" ]; then
    echo "ERROR: Python 3.11+ 필요. https://python.org 에서 설치하세요."
    exit 1
  fi
  local version
  version=$($py_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  local major minor
  major=$(echo "$version" | cut -d. -f1)
  minor=$(echo "$version" | cut -d. -f2)
  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
    echo "ERROR: Python $version 감지. Python 3.11+ 필요."
    exit 1
  fi
  echo "✓ Python $version"
}

ensure_python() {
  check_python
  if command -v python3 >/dev/null 2>&1; then
    local ver
    ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    info "Python $ver ✓"
    return 0
  fi
  info "Python 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install python@3.12 ;;
    apt)    sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv ;;
    dnf)    sudo dnf install -y python3 python3-pip ;;
    pacman) sudo pacman -S --noconfirm python python-pip ;;
    *)      fail "Python을 수동 설치하세요: https://python.org" ;;
  esac
  success "Python 설치 완료"
}

ensure_node() {
  if command -v node &>/dev/null; then
    echo "✓ Node.js $(node --version)"
    return
  fi
  # nvm
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
    if command -v node &>/dev/null; then
      echo "✓ Node.js (via nvm) $(node --version)"
      return
    fi
  fi
  # volta
  if [ -s "$HOME/.volta/bin/node" ]; then
    export PATH="$HOME/.volta/bin:$PATH"
    echo "✓ Node.js (via volta) $(node --version)"
    return
  fi
  # ~/local/nodejs
  local node_bin
  node_bin=$(ls -d "$HOME/local/nodejs"/node-v*/bin 2>/dev/null | sort -V | tail -1)
  if [ -n "$node_bin" ] && [ -f "$node_bin/node" ]; then
    export PATH="$node_bin:$PATH"
    echo "✓ Node.js (local) $(node --version)"
    # Write to .env
    echo "NODEJS_BIN_DIR=$node_bin" >> .env
    return
  fi
  # 패키지 매니저로 설치
  info "Node.js 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install node ;;
    apt)    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs ;;
    dnf)    curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash - && sudo dnf install -y nodejs ;;
    pacman) sudo pacman -S --noconfirm nodejs npm ;;
    *)
      echo "ERROR: Node.js를 찾을 수 없습니다."
      echo "  macOS: brew install node"
      echo "  또는: https://nodejs.org"
      exit 1
      ;;
  esac
  success "Node.js 설치 완료"
}

ensure_node_modules() {
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local remotion_dir="$SCRIPT_DIR/auto_agent/remotion_template"
  if [ -d "$remotion_dir" ] && [ ! -d "$remotion_dir/node_modules" ]; then
    info "Remotion npm 의존성 설치 중..."
    (cd "$remotion_dir" && npm install --quiet) && success "Remotion npm 설치 완료"
  fi
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1; then
    info "ffmpeg ✓"; return 0
  fi
  info "ffmpeg 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install ffmpeg ;;
    apt)    sudo apt-get install -y ffmpeg ;;
    dnf)    sudo dnf install -y ffmpeg ;;
    pacman) sudo pacman -S --noconfirm ffmpeg ;;
    *)      warn "ffmpeg를 수동 설치하세요: https://ffmpeg.org" ;;
  esac
  success "ffmpeg 설치 완료"
}

# ═══════════════════════════════════════
# Step 2: auto-kairos 패키지 설치
# ═══════════════════════════════════════

install_package() {
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  info "auto-kairos 패키지 설치 중..."
  pip3 install -e "${SCRIPT_DIR}[all]" --quiet 2>/dev/null || pip3 install -e "${SCRIPT_DIR}[all]"
  success "auto-kairos $(python3 -c 'from auto_agent import __version__; print(__version__)' 2>/dev/null || echo 'v3') 설치 완료"
}

# ═══════════════════════════════════════
# Step 3: 워크스페이스 설정
# ═══════════════════════════════════════

setup_workspace() {
  local default_ws="$HOME/my-video-project"

  printf "\n${BOLD}── 워크스페이스 설정 ──${NC}\n\n"
  ask "워크스페이스 경로 (Enter로 기본값: $default_ws):"
  read -r ws_path
  ws_path="${ws_path:-$default_ws}"
  ws_path="${ws_path/#\~/$HOME}"

  WORKSPACE="$(cd "$(dirname "$ws_path")" 2>/dev/null && pwd)/$(basename "$ws_path")" || WORKSPACE="$ws_path"

  # 기존 워크스페이스 감지
  if [ -d "$WORKSPACE/output" ] || [ -f "$WORKSPACE/auto_agent.db" ]; then
    info "기존 워크스페이스 감지: $WORKSPACE"
    info "v2→v3 업그레이드 모드로 초기화합니다 (기존 데이터 보존)"
    auto-kairos init "$WORKSPACE" --upgrade 2>&1 | while IFS= read -r line; do printf "  %s\n" "$line"; done
  else
    info "새 워크스페이스 생성: $WORKSPACE"
    auto-kairos init "$WORKSPACE" 2>&1 | while IFS= read -r line; do printf "  %s\n" "$line"; done
  fi

  success "워크스페이스 준비 완료: $WORKSPACE"
}

# ═══════════════════════════════════════
# Step 4: .env 설정
# ═══════════════════════════════════════

setup_env() {
  local env_file="$WORKSPACE/.env"

  printf "\n${BOLD}── API 키 설정 ──${NC}\n\n"

  if [ -f "$env_file" ]; then
    info "기존 .env 파일 감지"

    # Supabase 키 확인
    if grep -q "SUPABASE_URL=" "$env_file" && grep -q "SUPABASE_KEY=" "$env_file"; then
      local sb_url
      sb_url="$(grep '^SUPABASE_URL=' "$env_file" | cut -d= -f2-)"
      if [ -n "$sb_url" ] && [ "$sb_url" != "" ]; then
        info "Supabase 설정 확인됨: $sb_url"
        HAS_SUPABASE=true
        return 0
      fi
    fi
  else
    # .env.example → .env 복사
    if [ -f "$WORKSPACE/.env.example" ]; then
      cp "$WORKSPACE/.env.example" "$env_file"
    else
      touch "$env_file"
    fi
    info ".env 파일 생성됨"
  fi

  # Supabase 설정
  printf "\n"
  info "팀 프로젝트 공유를 위해 Supabase 설정이 필요합니다."
  ask "Supabase URL (없으면 Enter로 건너뛰기):"
  read -r sb_url

  if [ -n "$sb_url" ]; then
    ask "Supabase Anon Key:"
    read -r sb_key

    # .env에 추가/업데이트
    grep -v '^SUPABASE_URL=' "$env_file" > "$env_file.tmp" || true
    grep -v '^SUPABASE_KEY=' "$env_file.tmp" > "$env_file" || true
    rm -f "$env_file.tmp"
    printf "\n# Supabase (팀 프로젝트 공유)\nSUPABASE_URL=%s\nSUPABASE_KEY=%s\n" "$sb_url" "$sb_key" >> "$env_file"
    success "Supabase 설정 완료"
    HAS_SUPABASE=true
  else
    info "Supabase 건너뜀 (나중에 .env 파일에서 설정 가능)"
    HAS_SUPABASE=false
  fi

  # 필수 API 키 안내
  printf "\n"
  local missing_keys=()
  grep -q '^ELEVENLABS_API_KEY=.\+' "$env_file" 2>/dev/null || missing_keys+=("ELEVENLABS_API_KEY (TTS)")
  grep -q '^OPENAI_API_KEY=.\+' "$env_file" 2>/dev/null || missing_keys+=("OPENAI_API_KEY (자막)")

  if [ ${#missing_keys[@]} -gt 0 ]; then
    warn "다음 API 키가 설정되지 않았습니다 (나중에 .env 편집):"
    for k in "${missing_keys[@]}"; do
      printf "  ${DIM}  - %s${NC}\n" "$k"
    done
  fi
}

# ═══════════════════════════════════════
# Step 5: Supabase 프로젝트 동기화
# ═══════════════════════════════════════

sync_projects() {
  if [ "$HAS_SUPABASE" != "true" ]; then
    return 0
  fi

  printf "\n${BOLD}── 프로젝트 동기화 ──${NC}\n\n"

  # 로컬 프로젝트 목록
  local output_dir="$WORKSPACE/output"
  local local_projects=()
  if [ -d "$output_dir" ]; then
    while IFS= read -r d; do
      [ -d "$d" ] && local_projects+=("$(basename "$d")")
    done < <(find "$output_dir" -mindepth 1 -maxdepth 1 -type d | sort)
  fi

  if [ ${#local_projects[@]} -gt 0 ]; then
    info "로컬 프로젝트 ${#local_projects[@]}개 감지:"
    for p in "${local_projects[@]}"; do
      printf "    %s\n" "$p"
    done

    printf "\n"
    ask "로컬 프로젝트를 Supabase에 동기화하시겠습니까? (y/N):"
    read -r do_sync
    if [[ "$do_sync" =~ ^[yY] ]]; then
      export AUTO_AGENT_WORKSPACE="$WORKSPACE"
      for p in "${local_projects[@]}"; do
        info "동기화 중: $p"
        auto-kairos sync --project "$p" 2>&1 | while IFS= read -r line; do printf "    %s\n" "$line"; done || warn "동기화 실패: $p (나중에 수동 실행 가능)"
      done
      success "동기화 완료"
    fi
  fi

  # Supabase에서 pull (다른 팀원의 프로젝트)
  printf "\n"
  ask "Supabase에서 팀 프로젝트를 다운로드하시겠습니까? (y/N):"
  read -r do_pull
  if [[ "$do_pull" =~ ^[yY] ]]; then
    info "Supabase 프로젝트 목록 조회 중..."
    export AUTO_AGENT_WORKSPACE="$WORKSPACE"
    # 프로젝트 목록 가져와서 로컬에 없는 것만 pull
    python3 -c "
import sys, os
sys.path.insert(0, '$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)')
os.environ['AUTO_AGENT_WORKSPACE'] = '$WORKSPACE'
from dotenv import load_dotenv; load_dotenv('$WORKSPACE/.env')
from auto_agent.supabase_client import supabase_enabled, get_supabase, BUCKET_NAME
if not supabase_enabled():
    print('Supabase 연결 실패'); sys.exit(1)
sb = get_supabase()
resp = sb.table('projects').select('slug, name').execute()
local_dirs = set(os.listdir('$output_dir')) if os.path.isdir('$output_dir') else set()
remote_only = [p for p in resp.data if p['slug'] not in local_dirs]
if not remote_only:
    print('ALL_SYNCED')
else:
    for p in remote_only:
        print(f'{p[\"slug\"]}|{p[\"name\"]}')
" 2>/dev/null | while IFS='|' read -r slug name; do
      if [ "$slug" = "ALL_SYNCED" ]; then
        info "모든 프로젝트가 이미 로컬에 있습니다"
        break
      fi
      info "다운로드: $slug ($name)"
      auto-kairos pull --project "$slug" 2>&1 | while IFS= read -r line; do printf "    %s\n" "$line"; done || warn "다운로드 실패: $slug"
    done
    success "다운로드 완료"
  fi
}

# ═══════════════════════════════════════
# 완료
# ═══════════════════════════════════════

print_completion() {
  printf "\n"
  printf "${GREEN}${BOLD}╔═══════════════════════════════════════════════════╗${NC}\n"
  printf "${GREEN}${BOLD}║  Auto Kairos v3 설치 완료!                         ║${NC}\n"
  printf "${GREEN}${BOLD}╚═══════════════════════════════════════════════════╝${NC}\n"
  printf "\n"
  printf "${BOLD}시작하기:${NC}\n"
  printf "  cd %s\n" "$WORKSPACE"
  printf "  claude\n"
  printf "\n"
  printf "${BOLD}유용한 명령어:${NC}\n"
  printf "  auto-kairos dashboard          # 웹 대시보드\n"
  printf "  auto-kairos project list       # 프로젝트 목록\n"
  printf "  auto-kairos sync --project X   # Supabase 동기화\n"
  printf "  auto-kairos pull --project X   # Supabase에서 다운로드\n"
  printf "\n"
  printf "${DIM}업데이트: cd auto_kairos && git pull && pip install -e .[all]${NC}\n"
  printf "${DIM}워크스페이스 업데이트: auto-kairos init %s --upgrade${NC}\n" "$WORKSPACE"
  printf "\n"
}

# ═══════════════════════════════════════
# 메인
# ═══════════════════════════════════════

main() {
  header
  HAS_SUPABASE=false
  WORKSPACE=""

  local os
  os="$(detect_os)"
  info "OS: $os | 패키지매니저: $(detect_pm)"
  printf "\n"

  # Step 1: 시스템 의존성
  printf "${BOLD}── 시스템 의존성 확인 ──${NC}\n\n"
  ensure_python
  ensure_node
  ensure_node_modules
  ensure_ffmpeg

  # Step 2: 패키지 설치
  printf "\n${BOLD}── 패키지 설치 ──${NC}\n\n"
  install_package

  # Step 3: 워크스페이스
  setup_workspace

  # Step 4: .env
  setup_env

  # Step 5: 동기화
  sync_projects

  # 완료
  print_completion
}

main "$@"
