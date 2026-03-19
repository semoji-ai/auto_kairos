#!/bin/bash
# 대시보드 시작 스크립트 — Python 3.12 venv 환경 고정
set -e
cd /Users/hannah/Projects/auto_kairos_v3

# venv 활성화
source .venv/bin/activate

# .env 로드
set -a; source .env 2>/dev/null; set +a

# Node.js 경로
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"

# 기존 프로세스 정리
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 1

echo "=== Dashboard Starting ==="
echo "  Python: $(python --version)"
echo "  Port: 8080"
echo ""

exec python -m uvicorn app:app --host 0.0.0.0 --port 8080
