---
tags: [error, image, pipeline, null-safety]
date: 2026-03-17
severity: major
pipeline-step: image_asset_sourcing
agent: image-generator
status: resolved
recurrence: 1
---

# imageAsset=None으로 generate_images.py 크래시

## 증상
- step_8b(image_asset_sourcing) 시작 즉시 크래시
- `AttributeError: 'NoneType' object has no attribute 'get'`
- generate_images.py:629 step_0_preflight에서 발생

## 원인
scene_specs.json에서 일부 씬의 `imageAsset`이 `null`(None)로 설정됨.
`s.get("imageAsset", {}).get("source")` 패턴은 키가 존재하지만 값이 None일 때 기본값 `{}`가 적용되지 않음.

## 해결
`(s.get("imageAsset") or {}).get("source")` 패턴으로 변경 — None도 빈 dict로 폴백.

## 재발 방지
- [x] `or {}` 패턴 적용 (generate_images.py:629-630)
- [ ] scene_specs 생성 시 imageAsset 필드를 None 대신 빈 dict `{}` 또는 키 자체를 생략하도록 에이전트 스킬에 규칙 추가

## 관련 패턴
- [[이미지-생성-경로-버그]]
