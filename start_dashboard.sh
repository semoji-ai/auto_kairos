#!/bin/bash
# 대시보드 시작 스크립트 — Python 3.12 venv 환경 고정
set -e
cd "$(dirname "$0")"

# venv 활성화
source .venv/bin/activate

# .env 로드
if [ -f .env ]; then
  set -a; source .env; set +a
fi

# Node.js 경로 (NODEJS_BIN_DIR가 설정된 경우 PATH에 추가)
if [ -n "$NODEJS_BIN_DIR" ]; then
  export PATH="$NODEJS_BIN_DIR:$PATH"
fi

# 기존 프로세스 정리
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 1

echo "=== Dashboard Starting ==="
PYTHON=/opt/homebrew/bin/python3.12
echo "  Python: $($PYTHON --version)"
echo "  Port: 8080"
echo ""

exec $PYTHON -m uvicorn app:app --host 0.0.0.0 --port 8080
