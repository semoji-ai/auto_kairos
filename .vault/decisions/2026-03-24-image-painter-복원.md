---
tags: [decision, image-generation, pipeline]
date: 2026-03-24
status: implemented
related: [[errors/2026-03-24-image-batch-no-output]]
---

# image-painter LLM 에이전트 방식으로 복원

## 배경
image_batch 모듈(Python 코드 → FAL 배치)이 이미지 0개 생성하는 문제 발생.
모듈 방식은 프롬프트를 기계적으로 조립 → 영어 번역 → FAL 전송하는 구조로,
LLM의 씬별 창의적 판단이 없었음.

## 결정
- `step_8b`: image_batch module → image-painter agent로 복원
- `step_8b_legacy` 제거 (skip=true 상태에서 버그 유발)
- `_translate_to_english()` 비활성화 — 한국어 프롬프트 그대로 사용

## 비교

| | image_batch (제거) | image-painter (복원) |
|---|---|---|
| 프롬프트 | Python 기계 조립 → 영어 번역 | LLM이 한국어 구조화 직접 작성 |
| 씬별 판단 | 없음 | 있음 (concept 해석) |
| 속도 | 빠름 (배치) | 느림 (순차, 병렬 가능) |
| 비용 | 저렴 | LLM 토큰 사용 |

## 후속
- [ ] image-painter에 기존 이미지 스킵 로직 추가 (완료)
- [ ] 파이프라인에서 병렬 에이전트 실행 검토
- [ ] viz-background 제거 (완료)
