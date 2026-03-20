#!/bin/bash
# 파이프라인 시작 스크립트 — Python 3.12 venv 환경 고정
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

if [ -z "$1" ]; then
  echo "Usage: ./start_pipeline.sh <project_slug_or_uuid> [--from step_N]"
  exit 1
fi

exec python -m auto_agent.cli bg start --project "$@"
