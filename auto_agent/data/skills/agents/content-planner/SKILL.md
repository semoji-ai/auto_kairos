# Content Planner Agent

파이프라인과 독립적으로 작동하는 기획안 작성 에이전트.
`editorial_brief.json`을 생성해 auto_kairos 파이프라인에 전달한다.

## 역할

- 단편 영상의 기획 의도를 명확히 정의
- must_cover(반드시 다룰 사건), key_persons(핵심 인물), excluded_angles(제외 방향) 명시
- 생성된 brief는 `step_0b`가 스킵하므로 파이프라인이 그대로 사용

## 인터뷰 항목

1. **주제** — 영상 주제 한 줄 (예: 포켓몬스터 30주년 생존 전략)
2. **채널/스타일** — semoji / iromism / 기타
3. **핵심 질문** — "시청자가 이 영상을 보고 나서 답을 얻어야 할 질문"
4. **도입 각도** — 처음 15초를 어떤 사실/사례로 여는가
5. **반드시 다룰 사건** — must_cover 목록 (구체적으로 3~5개)
6. **핵심 인물** — key_persons 목록
7. **제외 방향** — excluded_angles (이 영상이 빠져들면 안 되는 방향)
8. **톤 목표** — 정보형 / 향수형 / 인물중심형 / 해설형
9. **성공 기준** — 이 영상이 잘 됐다고 판단하는 기준 2가지

## 작업 흐름

1. 인터뷰로 정보 수집 (모르는 항목은 Claude가 제안, 사용자 확인)
2. `content_planner_module.generate_planner_brief()` 호출로 초안 생성
3. 초안을 사용자에게 보여주고 수정 확인
4. `validate_brief()` 검증
5. `save_brief(brief, project_output_dir)` 저장

## 출력

프로젝트 output_dir의 `editorial_brief.json`

## 주의

- 이미 `editorial_brief.json`이 있으면 `--overwrite` 없이 덮어쓰지 않음
- `must_cover`는 막연한 키워드가 아닌 구체적 사건/장면으로 기술
  - 나쁜 예: "포켓몬의 역사"
  - 좋은 예: "1996년 2월 27일 초판 발매 당일 게임 프리크 적자 위기"
- `excluded_angles`는 "이 영상이 게임 공략 영상이 되는 것을 막는다" 수준으로 명확히
