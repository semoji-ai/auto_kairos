---
name: korean-tts-rules
description: Use when preparing Korean narration text for TTS synthesis with pronunciation and pacing rules
---

# Korean TTS Rules

한국어 TTS 전처리 규칙을 정의합니다.
숫자→한국어 읽기, 영어 약어 발음, 문장 부호, 호흡 단위 구분 규칙을 포함합니다.

**참조**: TTS 모듈 (`src/tools/korean_tts_preprocessor.py`)

---

## 1. 숫자 → 한국어 읽기

```
연도:
  2024년 → 이천이십사년
  2025년 → 이천이십오년
  1990년대 → 천구백구십년대

금액:
  100만 → 백만
  1억 → 일억
  150억 → 백오십억
  1조 → 일조
  $15B → 백오십억 달러
  10만 원 → 십만 원

백분율:
  14.3% → 십사점삼 퍼센트
  0.5% → 영점오 퍼센트

일반 수치:
  1,000 → 천
  35개 → 서른다섯 개
  3가지 → 세 가지
  5명 → 다섯 명
```

---

## 2. 영어 약어 → 한국어 발음

```
AI → 에이아이
API → 에이피아이
GPU → 지피유
CEO → 씨이오
LLM → 엘엘엠
GPT → 지피티
RAG → 래그
SaaS → 사스
IoT → 아이오티
UI → 유아이
UX → 유엑스
B2B → 비투비
```

---

## 3. 영어 단어 → 발음 표기

일반적으로 영어 단어는 그대로 유지 (TTS가 처리).
단, TTS가 자주 틀리는 단어만 발음 표기:

```
Anthropic → 앤쓰로픽
OpenAI → 오픈에이아이
Perplexity → 퍼플렉시티
Gemini → 제미나이
Claude → 클로드
agent → 에이전트 (이미 한국어화)
```

---

## 4. 문장 부호 → 정규화

```
— (em dash) → , (쉼표로 대체 + 쉼)
... (말줄임) → . (마침표로 대체)
; (세미콜론) → , (쉼표로 대체)
```

---

## 5. 된소리화/연음 보정

문맥에 따라 TTS가 잘못 읽을 수 있는 단어:
```
"할 것입니다" → 자연스러움 확인
"값이" → "갑시" (연음)
특수한 경우만 주석 처리
```

---

## 6. 호흡 단위 구분

긴 문장에 쉼표를 삽입하여 TTS 호흡 단위 확보:

```
변환 전: "AI 에이전트 시장은 2025년 기준으로 전년 대비 60% 성장하여 150억 달러를 돌파했습니다"
변환 후: "에이아이 에이전트 시장은, 이천이십오년 기준으로, 전년 대비 육십 퍼센트 성장하여, 백오십억 달러를 돌파했습니다"
```

---

## 7. 출력 포맷

각 씬에 `narration_tts` 필드 추가:

```json
{
  "sceneNumber": 5,
  "narration": "2025년 AI 에이전트 시장은 150억 달러를 넘어섰습니다.",
  "narration_tts": "이천이십오년 에이아이 에이전트 시장은 백오십억 달러를 넘어섰습니다.",
  "tts_changes": [
    {"original": "2025년", "converted": "이천이십오년", "rule": "year"},
    {"original": "AI", "converted": "에이아이", "rule": "abbreviation"},
    {"original": "150억", "converted": "백오십억", "rule": "korean_number"}
  ]
}
```

---

## 주의사항

- 원본 `narration` 필드는 그대로 유지 (새 `narration_tts` 필드에 전처리 결과)
- 변환 내역을 `tts_changes` 배열에 기록 (디버깅용)
- 고유명사는 최대한 원형 유지 (인물명, 기관명)
- narration이 없는 씬은 건너뛰기
