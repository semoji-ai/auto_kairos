---
tags: [error, pipeline, image-generation]
date: 2026-03-24
severity: blocking
pipeline-step: step_8b
status: resolved
recurrence: 1
related: [[decisions/2026-03-24-image-painter-복원]]
---

# image_batch 모듈이 이미지 0개 생성하고 완료 처리

## 증상
step_8b가 14.9초에 완료 표시되나 images/ 디렉토리에 파일 없음.
`[single_call 1턴]`으로 실행됨 — module 타입인데 single_call로 처리된 것으로 추정.

## 원인
정확한 원인 미확인. art_style.json이 프로젝트 디렉토리에 누락되었을 가능성.
image_batch_module.py:72에서 art_style.json 없으면 스킵 처리.

## 해결
image_batch 모듈 방식을 제거하고, image-painter LLM 에이전트 방식으로 복원.
→ [[decisions/2026-03-24-image-painter-복원]]

## 재발 방지
- [x] image-painter 에이전트로 전환 (LLM이 씬별 판단)
- [x] art_style.json 복사 로직 확인 필요
