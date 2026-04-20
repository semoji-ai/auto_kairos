# Director Agent Phase 2 — 설계 문서

> 날짜: 2026-03-24
> 상태: 설계 확정, 구현 대기

## 요약

Python runner.py의 for loop 기반 파이프라인을 **Director LLM Agent가 직접 이끌어가는 구조**로 전환한다.
pipeline.json은 Director가 참고하는 가이드맵이며, 흐름 제어권은 LLM에게 있다.
아트스타일 프리셋이 파이프라인 전체 행동을 결정하고, 볼트가 사용자 선호도를 축적한다.

## 배경

### 현재 구조의 한계
- runner.py가 모든 판단을 if/else로 수행 — 유연성 없음
- 각 에이전트는 자기 스텝만 알고 전체 맥락 모름
- 품질 판단이 "파일 존재 여부"/"JSON 파싱 성공" 수준
- 스텝 간 맥락이 파일로만 전달 — 컨텍스트 소멸
- 새 스텝 추가 = Python 코드 수정 필요

### Phase 2 목표
- Director LLM이 순서/품질/스킵/재시도를 판단
- 아트스타일별 규칙이 프리셋으로 분리되어 N개 확장 가능
- 사용자 피드백이 볼트에 축적되어 Director의 판단이 진화
- 기존 실행 인프라(subprocess, 파일 I/O)는 도구로 래핑하여 재활용

## 아키텍처

### 전체 구조

```
하네스 (전체 틀)
  ├── 시스템 프롬프트: Director의 역할/방향/금지조항
  ├── 도구 정의: 할 수 있는 것의 범위
  ├── 가드레일: preflight 검증, 프리셋 강제
  ├── 컨텍스트 주입: 프리셋 + 볼트 + pipeline.json
  └── 실행 인프라: 기존 runner.py 함수들을 도구로 래핑

Director LLM
  └── 하네스 안에서 판단하고 도구를 호출하며 파이프라인을 이끌어감
```

### 현재 → Phase 2 비교

```
현재:
  runner.py (Python for loop)
    → step_1 실행
    → step_2 실행
    → if failed: retry
    → ...고정된 순서

Phase 2:
  Director Agent (LLM)
    → "리서치부터 하자" → run_step("step_1")
    → 결과 확인 → "좋다, 원고 쓰자" → run_step("step_2")
    → 결과 확인 → "문체가 약하네" → retry_step("step_2", "이로미즘 톤 강화")
    → "1분이라 팩트체크 스킵" → skip_step("step_3")
    → ...LLM의 판단이 곧 흐름
```

## 아트스타일 프리셋

### 확장된 구조

기존 이미지 생성 규칙만 있던 아트스타일 JSON을 파이프라인 전체 프리셋으로 확장.

```json
{
  "id": "quirky_cartoon",
  "name": "Quirky Cartoon",
  "channel": "이로미즘",

  "image": {
    "staging": "cinematic",
    "reference_image": "artstyle/styles/quirky_cartoon_base.jpg",
    "scene_style_description": "Loose quirky hand-drawn cartoon...",
    "style": { "art_style": "...", "linework": "...", "color_palette": "..." },
    "critical_requirements": [],
    "prompt_language": "ko"
  },

  "voice": {
    "voice_id": "9Sj8ugvpK1DmcAXyvi3a",
    "voice_settings": {
      "stability": 1.0,
      "similarity_boost": 0.6,
      "style": 0.9,
      "speed": 1.1
    }
  },

  "creative": {
    "cinematic_max_ratio": 0.4,
    "headline_frequency": "20-30%",
    "mood_palette": ["dramatic", "suspense", "contemplative"],
    "preferred_layouts": ["cinematic", "before_after", "rank_list", "timeline"]
  },

  "scenes": {
    "density": "moderate",
    "min_duration_sec": 4,
    "max_duration_sec": 15,
    "prefer_split_on": ["전환어", "감정 전환", "시각적 전환"]
  },

  "guidelines": "이로미즘은 시네마틱 내러티브 중심. 극적 전개와 여백을 중시한다. 텍스트보다 이미지가 강한 임팩트를 줄 때 cinematic 사용. 통계/비교는 before_after나 rank_list로."
}
```

### 프리셋 적용 수준

- **기본 규칙**: 프리셋에 정의된 값이 기본값
- **가이드라인 수준**: Director가 특정 씬에서 오버라이드 가능
  - 예: staging=cinematic이 기본이지만, 데이터 비교 씬에서는 before_after로 변경 가능
- **프리셋은 변하지 않음**: 축적된 경험은 볼트에 저장

### N개 확장

새 아트스타일 추가 = 프리셋 JSON 파일 하나 작성만.
도구는 하나를 유지하고 내부에서 프리셋 값에 따라 행동이 달라지는 어댑터 패턴.

```
Director → generate_image(scene, preset)
             └── preset.image.staging == "flat" → flat 규칙 적용
             └── preset.image.staging == "cinematic" → cinematic 규칙 적용
```

## Director Agent 도구

### 도구 목록

| 도구 | 설명 | 래핑 대상 |
|------|------|-----------|
| `get_pipeline_state()` | 현재 진행 상황 (완료/실패/대기 스텝) | pipeline_state.json |
| `get_step_info(step_id)` | 스텝 정의 (입력/출력/에이전트/스킬) | pipeline.json |
| `run_step(step_id)` | 스텝 실행 | runner._execute_step() |
| `run_steps_parallel(step_ids)` | 의존성 없는 스텝 동시 실행 | ThreadPoolExecutor |
| `review_output(file_path)` | 결과물 읽고 반환 | Read 도구 |
| `retry_step(step_id, feedback)` | 피드백 포함 재실행 | runner._execute_step() + 프롬프트 주입 |
| `skip_step(step_id, reason)` | 스킵 + 사유 기록 | state 업데이트 |
| `log_preference(note)` | 볼트에 선호도/피드백 기록 | .vault/preferences/*.md |
| `send_message(text)` | 메신저에 진행 상황 전송 | _notify() |

### 도구 설계 원칙

- 각 도구는 기존 runner.py의 함수를 래핑
- 도구 내부에서 프리셋 값을 참조하여 분기 (어댑터 패턴)
- Director는 도구 목록 외의 행동 불가 (하네스 제한)

## Preflight Validation

Director 시작 전 하네스 레벨에서 강제하는 검증.

### 검증 항목

```
1. 프리셋 완전성
   ├── image.staging 존재?
   ├── image.reference_image 파일 존재?
   ├── voice.voice_id 존재?
   ├── creative 섹션 존재?
   ├── scenes 섹션 존재?
   └── guidelines 비어있지 않은지?

2. 도구-프리셋 교차 검증
   ├── staging 값이 도구가 지원하는 모드인지?
   │   (cinematic, flat만 유효)
   └── voice_id가 유효한 ElevenLabs ID 형식인지?

3. 프로젝트 config 완전성
   ├── art_style 설정?
   ├── writing_style 설정?
   └── duration_minutes 설정?
```

### 실패 시

- 누락 항목 구체적으로 표시
- 인터랙티브 환경: 인터뷰로 보완
- 백그라운드 환경: 즉시 에러 중단

## 볼트 기반 학습

### 기록 시점

- 사용자가 이미지 재생성 요청 시
- 사용자가 씬 수정 요청 시
- 파이프라인 완료 후 사용자 피드백 시
- Director가 재시도/스킵 판단 시

### 저장 구조

```
.vault/
  preferences/
    quirky_cartoon.md     ← 아트스타일별 축적
    semoji.md
    lego.md
    general.md            ← 스타일 무관한 전반적 선호
```

### 기록 포맷

```markdown
# quirky_cartoon 선호도

## 이미지
- 밝은 톤 선호, 어두운 배경 회피 (2026-03-24, 배의_역사)
- 인물 클로즈업보다 와이드샷 선호 (2026-03-25, 자동차의역사)

## 씬 구성
- 1분 영상: 7-8씬이 적절 (2026-03-24, 배의_역사)

## creative
- headline 빈도 체감상 20% 이하가 좋다 (2026-03-25)
```

### Director의 활용

파이프라인 시작 시:
1. 프리셋 로드 → 기본 규칙
2. `.vault/preferences/{preset_id}.md` 로드 → 축적된 선호도
3. 둘을 합쳐서 Director 컨텍스트에 주입

프리셋 = 초기 규칙 (불변), 볼트 = 축적된 경험 (성장)

## 실행 흐름

```
사용자: "배의 역사 1분, 이로미즘으로 돌려줘"
  │
  ├─ 1. 프로젝트 생성
  │    config: { art_style: quirky_cartoon, writing_style: iromism, duration: 1 }
  │
  ├─ 2. 하네스 Preflight
  │    ├─ 프리셋 로드 + 완전성 검증
  │    ├─ 도구-프리셋 교차 검증
  │    ├─ 볼트 선호도 로드
  │    └─ 메신저: "시작 | 문체: iromism | 아트: quirky_cartoon | 1분"
  │
  ├─ 3. Director Agent 시작 (claude CLI 세션)
  │    컨텍스트: 프리셋 + 볼트 선호도 + pipeline.json
  │    │
  │    ├─ run_step("step_1") → 리서치
  │    ├─ review_output → "충분하다"
  │    ├─ run_step("step_2") → 원고
  │    ├─ review_output → "문체 OK"
  │    ├─ skip_step("step_3", "1분 숏폼") → 팩트체크 스킵
  │    ├─ run_step("step_5") → 씬 분할
  │    ├─ review_output → "10씬, 볼트에 7-8씬 선호 기록"
  │    │   → retry_step("step_5", "8씬 이내로")
  │    ├─ run_step("step_6") → creative direction
  │    ├─ review_output → "cinematic 비율 확인, 프리셋 가이드라인 참조"
  │    ├─ "step_7과 step_8b는 둘 다 step_6에만 의존 — 동시 실행"
  │    │   → run_steps_parallel(["step_7", "step_8b"])
  │    │     ├─ step_7: TTS 전처리 (병렬)
  │    │     └─ step_8b: 이미지 생성, 프리셋 staging 참조 (병렬)
  │    ├─ ... 자막, 렌더 ...
  │    └─ send_message("파이프라인 완료")
  │
  └─ 4. 사용자 피드백
       → Director: log_preference(...) → 볼트 축적
```

## 점진적 전환

### Phase 1 (현재)
Python runner + LLM 서브에이전트. runner.py가 모든 판단.

### Phase 2 (이 설계)
Director LLM + pipeline.json 가이드맵. LLM이 판단, 실행 인프라 재활용.

### Phase 3 (향후)
Director LLM + 도구만. pipeline.json 제거, 도구 조합으로 자유 실행.

### Phase 4 (향후)
멀티 에이전트 팀. Director + 전문 에이전트들이 자율 협업.

### 롤백

Phase 2에서 문제 발생 시 runner.py 기반으로 즉시 롤백 가능.
기존 runner.py 코드는 제거하지 않고, Director 실행 경로와 병렬로 유지.
`auto-agent run --legacy` 플래그로 기존 방식 실행 가능.

## 구현 범위

### 포함
- 확장된 아트스타일 프리셋 JSON 구조 (기존 하위 호환)
- Director Agent 시스템 프롬프트 + 도구 정의
- 도구 구현 (기존 runner.py 함수 래핑)
- Preflight 검증 강화
- 볼트 preferences 구조
- `--legacy` 플래그로 기존 방식 유지

### 제외
- pipeline.json 구조 변경 (그대로 사용)
- Remotion 렌더러 변경
- 대시보드 변경
- 멀티 에이전트 병렬 (Phase 3+)
