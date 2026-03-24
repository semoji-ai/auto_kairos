---
tags: [error, remotion, mapScene]
date: 2026-03-17
severity: major
pipeline-step: step_6, build_manifest
agent: visual-composer
status: resolved
recurrence: 0
---

# mapScene 좌표 [lat,lng] vs [lng,lat] 불일치

## 증상
맵씬이 이란(호르무즈 해협)을 표시해야 하는데, 발트해/폴란드 지역을 표시함.

## 원인
1. 1턴 프롬프트에서 `center: [위도, 경도]`로 지시 → LLM이 `[26.5, 56.3]` (lat, lng) 출력
2. MapLibre는 `[lng, lat]` 순서를 기대
3. build_manifest.py에서 좌표 변환 없이 그대로 전달 → MapLibre가 lng=26.5, lat=56.3으로 해석 → 유럽

추가로:
- markers도 `{lat, lng}` 필드 → Remotion은 `{coordinates: [lng, lat]}` 기대
- mapType 필드 누락 → MapSceneRenderer switch문에서 빈 화면
- camera.keyframes 누락 → `data.camera.keyframes` 접근 시 TypeError

## 해결
`build_manifest.py`에서 mapScene 변환 로직 추가:
1. `center: [lat, lng]` → `[lng, lat]` swap
2. `markers: {lat, lng}` → `{coordinates: [lng, lat]}` 변환
3. `mapType` 없으면 `"location_reveal"` 기본값
4. `camera` 없으면 center/zoom에서 기본 keyframes 자동 생성

Remotion 컴포넌트 4개(LocationReveal, RouteAnimation, FlyThrough, TerritoryOverlay)에 defensive null 체크 추가.

## 수정 파일
- `auto_agent/scripts/build_manifest.py` — mapScene 좌표 변환 + mapType/camera 기본값
- `auto_agent/remotion_template/src/map/LocationReveal.tsx` — `data.camera?.keyframes ?? []`
- `auto_agent/remotion_template/src/map/RouteAnimation.tsx` — 동일
- `auto_agent/remotion_template/src/map/FlyThrough.tsx` — 동일
- `auto_agent/remotion_template/src/map/TerritoryOverlay.tsx` — 동일

## 재발 방지
- 프롬프트에서 mapScene 생성 시 `center: [위도, 경도]` 형식 유지 (LLM에게 자연스러운 순서)
- build_manifest.py가 항상 [lat,lng] → [lng,lat] 변환 담당
- markers는 반드시 `{lat, lng}` → `{coordinates: [lng, lat]}` 변환
