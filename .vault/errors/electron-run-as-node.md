---
date: 2026-03-17
category: electron
severity: critical
resolved: true
---

# ELECTRON_RUN_AS_NODE=1 → Electron API 미로드

## 증상
- `require('electron')`이 바이너리 경로 문자열을 반환
- `process.type`이 `undefined` (정상: `"browser"`)
- `electron.app.whenReady()` → `TypeError: Cannot read properties of undefined`
- Electron 바이너리는 실행되지만 메인 프로세스 API 없음

## 원인
VS Code가 Electron 기반이라 내부적으로 `ELECTRON_RUN_AS_NODE=1`을 설정함.
VS Code 터미널(통합 터미널)에서 이 변수가 자식 프로세스에 상속됨.
이 변수가 있으면 Electron이 Node.js 호환 모드로 실행되어 API를 로드하지 않음.

## 해결
1. `vite.config.ts`에서 `delete process.env.ELECTRON_RUN_AS_NODE`
2. `package.json` dev 스크립트에서 `unset ELECTRON_RUN_AS_NODE && vite`
3. 또는 외부 터미널(Terminal.app)에서 실행

## 교훈
- VS Code 통합 터미널에서 Electron 개발 시 항상 이 변수를 해제할 것
- Electron이 "실행은 되지만 API가 없는" 증상이면 이 환경변수부터 확인
