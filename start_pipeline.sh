#!/bin/bash
# 파이프라인 시작 스크립트 — Python 3.12 venv 환경 고정
set -e
cd /Users/hannah/Projects/auto_kairos_v3

# venv 활성화
source .venv/bin/activate

# .env 로드
set -a; source .env 2>/dev/null; set +a

# Node.js 경로
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"

if [ -z "$1" ]; then
  echo "Usage: ./start_pipeline.sh <project_slug_or_uuid> [--from step_N]"
  exit 1
fi

exec python -m auto_agent.cli bg start --project "$@"
