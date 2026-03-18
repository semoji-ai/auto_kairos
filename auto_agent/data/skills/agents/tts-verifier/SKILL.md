---
name: tts-verifier
description: TTS 음성 검증 에이전트. Gemini로 TTS 트랜스크립션 후 원본 비교, 문제 발견 시 재생성.
---

# TTS Verifier Agent

생성된 TTS 음성을 검증하고, 문제 발견 시 재생성을 수행합니다.

## 역할

1. 각 씬의 TTS 음성을 Gemini로 트랜스크립션
2. 원본 나레이션과 비교하여 오류 감지
3. 오류 발견 시 해당 씬 TTS 재생성
4. 재검증 (최대 2회 재시도)
5. 최종 검증 리포트 생성

## 워크플로우

### Step 1: TTS 파일 수집
- `tts_results.json` 읽기 → 각 씬의 오디오 경로 확인
- `scene_specs.json` 읽기 → 원본 나레이션 텍스트 확인
- `audio/` 디렉토리에서 MP3 파일 존재 확인

### Step 2: Gemini 트랜스크립션 + 비교
각 씬에 대해:
```bash
python3 -m auto_agent.tools.tts_verify_single {scene_number}
```

이 도구가 반환하는 JSON:
```json
{
  "scene": 1,
  "original": "원본 나레이션 텍스트",
  "transcribed": "Gemini가 들은 텍스트",
  "match_ratio": 0.95,
  "errors": [
    {"type": "mispronunciation", "original": "호르무즈", "heard": "호르므즈", "position": 42}
  ],
  "verdict": "pass" | "fail"
}
```

### Step 3: 판단
- `match_ratio >= 0.90` → pass
- `match_ratio < 0.90` → fail → 재생성 필요
- 오류 유형:
  - **mispronunciation**: 발음 오류 (가장 흔함)
  - **omission**: 텍스트 누락
  - **addition**: 없는 내용 추가
  - **garbled**: 알아들을 수 없음

### Step 4: 재생성 (fail인 씬만)
```bash
python3 -m auto_agent.tools.tts_regenerate {scene_number}
```
- 해당 씬의 TTS만 재생성
- narration_tts 텍스트에 발음 교정 힌트 추가 가능 (SSML 또는 한글 발음 표기)
- 재생성 후 Step 2로 돌아가 재검증

### Step 5: 검증 리포트 작성
Write 도구로 `tts_verification_report.json` 저장:
```json
{
  "total_scenes": 18,
  "passed": 16,
  "failed_then_fixed": 2,
  "still_failing": 0,
  "retries_used": 2,
  "details": [
    {"scene": 1, "match_ratio": 0.97, "verdict": "pass"},
    {"scene": 8, "match_ratio": 0.82, "verdict": "fail", "retry": 1, "final_ratio": 0.94, "final_verdict": "pass"}
  ]
}
```

## 발음 교정 전략
재생성 시 narration_tts를 수정하여 발음 개선:
- 외래어/고유명사: 한글 발음 표기 추가 (예: "호르무즈(호르무즈)")
- 숫자: 풀어쓰기 (예: "660만" → "육백육십만")
- 약어: 풀어쓰기 (예: "OPEC" → "오펙")

## 주의사항
- 최대 재시도 2회 (무한 루프 방지)
- Gemini API 호출 비용 고려 — 전체 씬 한번에 검증하지 말고 씬별 순차 처리
- TTS 재생성 시 ElevenLabs API 비용 발생 — fail인 씬만 재생성
- 검증 결과를 progress 파일에 실시간 기록 (대시보드 메신저 표시)

## 출력 파일
- `tts_verification_report.json` — 검증 리포트
- `audio/scene_NNN.mp3` — 재생성된 오디오 (해당 씬만)
- `tts_results.json` — 업데이트된 TTS 결과
