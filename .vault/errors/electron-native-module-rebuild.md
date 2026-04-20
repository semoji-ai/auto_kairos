---
date: 2026-03-17
category: electron
severity: high
resolved: true
---

# better-sqlite3 네이티브 모듈 — Electron NODE_MODULE_VERSION 불일치

## 증상
- `The module was compiled against a different Node.js version using NODE_MODULE_VERSION 127. This version requires 125.`
- DB 초기화 실패, 프로젝트 목록 빈 배열

## 원인
- better-sqlite3는 C++ 네이티브 모듈
- 시스템 Node.js(v22, MODULE_VERSION 127)와 Electron 내장 Node.js(v20, MODULE_VERSION 125)가 다름
- npm install은 시스템 Node.js용으로 빌드

## 해결
1. `npx electron-rebuild -f -w better-sqlite3`
2. vite.config.ts에서 `rollupOptions.external: ["better-sqlite3"]` (번들에 포함하면 안 됨)

## 추가: vite-plugin-electron에서 네이티브 모듈 처리
- 네이티브 모듈(.node 파일)은 rollup이 번들할 수 없음
- 반드시 external로 빼고, node_modules에서 직접 require하도록 해야 함
