---
tags: [error, env, config, 반복발생]
date: 2026-03-16
severity: blocking
pipeline-step: startup
agent: none
status: resolved
recurrence: 3
---

# 환경변수 미로드로 서비스 시작 실패

## 증상
대시보드/파이프라인이 SUPABASE_URL, ANTHROPIC_API_KEY 등을 찾지 못해 시작 실패.
- `OSError: SUPABASE_URL 및 SUPABASE_KEY 환경변수를 설정하세요`
- CLI에서 `auto-agent run` 실행 시 API 키 없음 에러

## 원인
1. `.env` 파일이 자동 로드되지 않음 (python-dotenv 미설치 또는 로드 위치 문제)
2. subprocess로 실행할 때 부모 환경변수가 전달 안 됨
3. bash에서 `source .env`가 export 없이 실행됨

## 해결
- `export $(grep -v '^#' .env | xargs)` 로 명시적 export
- runner.py에서 워크스페이스 .env 자동 로드 로직 추가

## 재발 방지
- [x] runner.py 시작 시 .env 자동 로드
- [x] ANTHROPIC_API_KEY를 선택사항으로 변경 (Claude Code 구독제 기본)
- [ ] 서버 시작 스크립트에 .env 로드 포함

## 관련 패턴
- [[서버-시작-실패-패턴]]
