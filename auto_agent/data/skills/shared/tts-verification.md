---
name: tts-verification
description: Use when verifying TTS audio output quality through hybrid automated and manual checks
---

# TTS Verification (하이브리드 검증)

Gemini 음성 인식으로 TTS 오디오를 재트랜스크립션하여 원본 나레이션과 비교.
TTS 발음 오류를 자동 감지하는 품질 게이트.

**스크립트**: `scripts/verify_tts.py`

---

## 검증 흐름

```
scene_specs.json (narration)
  + audio/scene_NNN.mp3
  → Gemini 트랜스크립션 (들리는 대로 받아적기)
  → 원본 narration과 비교
  → 유사도 + 불일치 구간 추출
  → tts_verification.json
```

## 판정 기준

| 유사도 | 판정 | 액션 |
|--------|------|------|
| >= 95% | OK | 통과 |
| 85-95% | WARN | 리뷰 권장 (false positive 가능) |
| < 85% | ERROR | TTS 재생성 필요 |

## False Positive 처리

영어→한국어 발음 변환은 동의어로 취급:
- `S&P500` = `에스앤피오백` (표기 차이, 발음 동일)
- `TIGER` = `타이거`
- `ETF` = `이티에프`
- 숫자: `500` = `오백`, `900` = `구백`

## 입출력

- **입력**: `scene_specs.json`, `audio/scene_NNN.mp3`
- **출력**: `tts_verification.json`
  ```json
  {
    "total": 52,
    "errors": [5, 35],
    "results": [
      {
        "sceneNumber": 5,
        "similarity": 0.9059,
        "mismatches": [
          {"type": "replace", "original": "500", "transcribed": "오바"}
        ],
        "narration": "...",
        "transcribed": "..."
      }
    ]
  }
  ```

## 실행

```bash
PROJECT_NAME=<slug> python3 scripts/verify_tts.py
```

## 의존성

- `google-genai` (Gemini API)
- `GOOGLE_API_KEY` 환경변수

## 파이프라인 위치

`phase_4` (에셋 생산) → `step_9` (자막 동기화) 이후, `phase_5` (조립) 이전.
gate가 아닌 advisory 단계 — ERROR 씬은 경고하지만 파이프라인은 중단하지 않음.
