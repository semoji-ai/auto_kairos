# Claude·Codex 통합 실행 및 적응형 검수

2026-09-15 구현. 기본 프로필은 `balanced`입니다. 실영상의 품질 향상·토큰 절감률은 아직 측정하지 않았습니다.
이 변경은 모델 선택, 불필요한 반복 중단, 산출물 검증과 측정 기반을 제공합니다.

## 실행

```bash
auto-agent run --project PROJECT --provider codex --execution-profile balanced --dry-run
auto-agent run --project PROJECT --provider codex --execution-profile balanced
auto-agent run --project PROJECT --provider claude --execution-profile quality
auto-agent run --project PROJECT --provider codex --model gpt-6-astra
auto-agent run --project PROJECT --execution-profile legacy
```

`--dry-run`은 단계별 엔진·모델과 legacy 스킵 여부를 출력하며 실행·요약·알림을 수행하지 않습니다.
새 프로필은 Claude CLI 또는 Codex CLI를 사용합니다. 모델 접근 실패는 실패로 기록하며 다른 엔진에 자동 재전송하지 않습니다.
모델 ID의 공개 여부와 현재 로그인 계정의 사용 권한은 별개입니다.

| 프로필 | Claude | Codex | 프롬프트·메모리 |
|---|---|---|---|
| balanced (기본) | claude-opus-5 | gpt-5.6-sol | 목표 중심 초고·기획 검수, 산출물 참조 메모리 |
| quality | claude-fable-5-1 | gpt-6-astra | 동일 계약, 높은 추론 노력 |
| legacy | 기존 agent/step 모델 | 기존 codex_model 또는 Sol | 기존 스킬·Haiku 요약 및 기존 SDK 경로 |

프로필 표는 성능 순위나 비용 우위를 실험으로 입증한 결과가 아닙니다.
balanced와 quality 모두 기존 타임아웃과 턴 상한을 유지합니다. Codex CLI에는 Claude의 max-turns와 동일한 상한을 적용하지 않으며 외부 타임아웃을 적용합니다.
기존 버전에 존재하던 SDK 단일 호출, 잘못된 JSON 재사용 등의 오류까지 legacy 모드에서 복원하지는 않습니다.

## 작업별 조합

프로젝트 config에 다음 execution 객체를 넣으면 단계별로 엔진을 조합할 수 있습니다.

```json
{
  "execution": {
    "provider": "claude",
    "profile": "balanced",
    "agents": {
      "script-director": {"provider": "claude", "model": "claude-opus-5"},
      "script-reviewer": {"provider": "codex", "model": "gpt-6-astra", "reasoning_effort": "high"},
      "targeted-researcher": {"provider": "codex", "model": "gpt-5.6-sol"}
    }
  }
}
```

옵션 우선순위: step.execution > execution.agents[에이전트] > 프로젝트 execution (CLI 옵션이 여기에 합쳐짐).
provider가 없으면 AUTO_AGENT_PROVIDER, 기존 research_provider/환경 변수(리서치 두 에이전트만), agents.json, claude 순입니다.
현대 프로필의 모델은 execution.model 또는 execution.models[provider], AUTO_AGENT_CLAUDE_MODEL/AUTO_AGENT_CODEX_MODEL, 프로필 기본값 순입니다.
따라서 기존 agents.json의 Opus 4/Sonnet 지정은 현대 프로필에서 교체됩니다. 특정 모델 고정은 execution에 선언하세요.
모든 provider에 하나의 model을 지정하면 혼합 엔진과 충돌할 수 있으므로 혼합 구성에서는 models 또는 에이전트별 model을 사용하세요.
AUTO_AGENT_EXECUTION_PROFILE은 프로젝트에 프로필이 없을 때 사용합니다. Stage 0/4와 독립 기획 모듈은 환경 설정을 사용합니다.

## 통합 범위

- 일반 agent 실행은 use_sdk 분기 전에 provider를 결정합니다. balanced/quality에서는 CLI로 실행합니다.
- 챕터 병렬 연출·단일 JSON 응답 단계도 공통 실행기를 사용합니다.
- main 통합 시 챕터 정적 지침의 Claude 시스템 프롬프트 캐시를 유지했습니다. Codex에는 동일 지침을 stdin으로 전달하고 Claude 캐시 워밍은 호출하지 않습니다.
- Stage 0/4와 Adobe 오케스트레이터는 공통 모델 resolver를 사용하며 기존 스트리밍·세션 어댑터를 유지합니다.
- 독립 auto 기획 생성·검수도 현대 프로필에서는 공통 CLI를 사용합니다.
- v4 bridge 및 기존 이미지·TTS·Remotion 조립 계약은 유지합니다. legacy_only 단계는 자동 활성화하지 않습니다.
- 이 작업은 저장소의 모든 독립 보조 모듈을 전환한 것은 아닙니다. legacy SDK, generate_planner_brief, 별도의 web_agent/이미지 생성·직접 codex 호출 등은 기존 경로가 남아 있습니다.

## 반복과 검증

- 기존 스킬을 보존하고 초고·기획 리뷰에 ADAPTIVE.md를 선택 로드합니다.
- 초고의 고정 작성 순서와 질문 최소 개수를 없앴습니다. 챕터 구분·질문 ID 대응·사실 근거 계약은 유지합니다.
- 기획 리뷰의 자체 수정은 근거가 있는 결함에 한 번만 허용합니다. 검수 전용 CLI 호출은 수정 없이 평가만 합니다.
- Adobe 기획·원고와 독립 기획 루프는 통과, 개선 정체, 수정 지시 부재에서 멈춥니다. 종료는 PASS와 다릅니다.
- 독립 기획 재작성은 이전 기획과 피드백을 입력받고 평가한 후보를 보존합니다.
- Stage 0 Codex 탐색은 후보가 그대로면 중단합니다. Claude 탐색 프롬프트도 고정 횟수 대신 최대 횟수를 지시합니다.
- 새 메모리는 LLM 요약 호출 없이 산출물 경로를 기록합니다. 이 기록으로 원본 근거를 대체하지 않습니다.
- 깨진 JSON·빈 산출물, 챕터 씬 번호 누락/중복을 실패로 처리합니다. 챕터 실패 시 기존 scene_specs를 보존합니다.
- 리뷰 서비스 실패 후 휴리스틱 점수만으로 PASS를 만들지 않습니다.

## 측정과 채택

공통 CLI 실행은 프로젝트 `.execution/<run_id>.json`에 provider, model, profile, reasoning_effort,
prompt_chars, duration_sec, returncode와 토큰 usage를 기록합니다. 실패한 시도도 기록하므로 재시도 비용을 포함할 수 있습니다.
prompt_chars는 문자 수이며 토큰 수가 아닙니다. Codex의 cost_known=false는 달러 청구 비용을 모른다는 뜻입니다.
Adobe의 기존 세션 어댑터 호출은 이 실행 기록에 포함되지 않습니다.

기록을 읽기만 하는 집계 명령:

```bash
python3 -m auto_agent.scripts.summarize_execution /path/to/project
```

병렬 실행의 duration 합계는 작업자 시간 합계이며 사용자가 기다린 전체 시간과 다릅니다.

검증에는 별도 프로젝트 복사본으로 동일한 자료·브리프를 사용하세요.

1. legacy 모델 + legacy 스킬을 기준으로 보존합니다.
2. execution.model을 같은 최신 모델에 고정하여 legacy 스킬과 현대 스킬의 효과를 분리합니다.
3. 같은 입력으로 balanced와 quality를 비교합니다.
4. 전체 실행 토큰(실패·수정 포함), 시간, 사실 오류, 누락, 서사 중복, 렌더링 유효성을 비교합니다.
5. 블라인드 품질 검수에서 좋아진 조합만 운영 기본값으로 채택합니다. 단순 자기 점수 상승은 품질 향상의 증거가 아닙니다.

## 모델 근거

- [Claude Opus 5](https://platform.claude.com/docs/en/models/opus-5/overview)
- [Claude Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/overview)
- [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Codex 비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode)
