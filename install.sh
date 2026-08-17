#!/usr/bin/env bash
# auto_kairos 설치 — 클론 직후 한 번 돌린다. 여러 번 돌려도 안전하다.
#
#   ./install.sh
#
# 이후 `git pull` 할 때는 .githooks/post-merge 가 바뀐 것만 알아서 챙긴다.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
G="\033[32m"; Y="\033[33m"; R="\033[31m"; N="\033[0m"
ok()   { echo -e "  ${G}[✓]${N} $1"; }
warn() { echo -e "  ${Y}[!]${N} $1"; }
bad()  { echo -e "  ${R}[✗]${N} $1"; }

echo ""; echo "  auto_kairos 설치"; echo ""

# ── 1. 파이썬 ─────────────────────────────────────────
if [ ! -d "$ROOT/.venv" ]; then
    python3 -m venv "$ROOT/.venv" && ok "가상환경 생성"
fi
PY="$ROOT/.venv/bin/python"; PIP="$ROOT/.venv/bin/pip"
"$PIP" install -q --upgrade pip
"$PIP" install -q -e "$ROOT[all]" && ok "파이프라인 패키지"
[ -f "$ROOT/adobe/requirements.txt" ] && \
    "$PIP" install -q -r "$ROOT/adobe/requirements.txt" && ok "adobe 패키지"

# ── 2. 서브모듈 ───────────────────────────────────────
git -C "$ROOT" submodule update --init --recursive --quiet 2>/dev/null && ok "서브모듈"

# ── 3. git 훅 ─────────────────────────────────────────
git -C "$ROOT" config core.hooksPath .githooks && ok "git 훅 (pull 시 자동 갱신)"

# ── 4. Node / Remotion ────────────────────────────────
if command -v npm >/dev/null 2>&1; then
    (cd "$ROOT/remotion" && npm install --silent >/dev/null 2>&1) && ok "Remotion 패키지"
else
    warn "npm이 없습니다 — Remotion 렌더를 쓰려면 Node를 설치하세요"
fi

# ── 5. CEP 패널 (After Effects) ───────────────────────
CEP_DIR="$HOME/Library/Application Support/Adobe/CEP/extensions"
if [ -d "$ROOT/adobe/cep/com.autokairos.pd" ]; then
    mkdir -p "$CEP_DIR"
    ln -sfn "$ROOT/adobe/cep/com.autokairos.pd" "$CEP_DIR/com.autokairos.pd" \
        && ok "CEP 패널 연결 (AE를 껐다 켜세요)"
fi

# ── 6. 공유 규격 ──────────────────────────────────────
"$PY" "$ROOT/scripts/spec_sync.py" --push >/dev/null 2>&1 && ok "공유 규격 동기화"

# ── 7. 환경 변수 확인 ─────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
    [ -f "$ROOT/.env.example" ] && cp "$ROOT/.env.example" "$ROOT/.env" && \
        warn ".env를 만들었습니다 — 키를 채우세요"
fi
MISSING=""
for k in OPENAI_API_KEY ELEVENLABS_API_KEY RECRAFT_API_KEY GOOGLE_API_KEY; do
    grep -q "^$k=..*" "$ROOT/.env" 2>/dev/null || MISSING="$MISSING $k"
done
# FAL은 두 이름 중 하나면 된다
grep -qE "^FAL_(API_)?KEY=..*" "$ROOT/.env" 2>/dev/null || MISSING="$MISSING FAL_KEY"
[ -n "$MISSING" ] && warn "키 없음 —$MISSING" || ok "API 키"

# ── 8. 프로젝트 폴더 ──────────────────────────────────
if [ -e "$ROOT/output" ]; then
    ok "프로젝트 폴더 ($(readlink "$ROOT/output" 2>/dev/null || echo "$ROOT/output"))"
else
    warn "output/ 이 없습니다 — NAS를 마운트했는지 확인하세요"
fi

echo ""
echo "  다음"
echo "    대시보드   .venv/bin/python -m uvicorn app:app --port 8080"
echo "    adobe 패널  cd adobe && ../.venv/bin/python -m uvicorn backend.app:app"
echo "    AE 연동    AK_PROJECTS_ROOT 를 프로젝트 폴더로 설정"
echo ""
