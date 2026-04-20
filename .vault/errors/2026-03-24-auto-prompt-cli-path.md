---
tags: [error, dashboard, cli-path]
date: 2026-03-24
severity: degraded
pipeline-step: none
status: resolved
recurrence: 1
related: [[errors/아트스타일-경로-반복실패]]
---

# 대시보드 자동 프롬프트 버튼 — Claude CLI 경로 하드코딩

## 증상
에셋탭에서 "자동 프롬프트" 버튼 클릭 시 "실패" 표시.

## 원인
`app.py:858`에서 Claude CLI 경로가 하드코딩:
```python
cli_path = str(Path.home() / ".local/bin/claude")
```
실제 경로: `/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin/claude`

## 해결
`shutil.which("claude")`로 PATH에서 자동 탐색, 없을 때만 fallback.

## 추가 수정
프롬프트 포맷도 구조화 포맷(【스타일】【상황】【배경】【카메라 앵글】)으로 변경.
아트스타일 `scene_style_description` 자동 주입 추가.

## 재발 방지
- [x] shutil.which() 사용
- [ ] 다른 곳에도 CLI 경로 하드코딩 있는지 grep 확인
