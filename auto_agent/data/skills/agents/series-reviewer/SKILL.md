# Series Reviewer Agent

전체 시리즈의 Stage 2 완료 후 편 간 일관성을 검토하는 에이전트.

## 역할

- 편 간 중복 내용 탐지
- 서사 흐름 단절 감지 (이전 편과 연결이 어색한 부분)
- 누락된 핵심 사건 확인 (series_plan.json 대비)
- 각 편 분량 균형 검토

## 입력

- `series_plan.json` — 원래 기획안
- `episodes/{N}/scene_specs.json` — 전 편의 Stage 2 결과물

## 출력

`series_review.json`:
```json
{
  "overall_score": 85,
  "issues": [
    {
      "type": "overlap",
      "episodes": [2, 3],
      "description": "EP2와 EP3 모두 금성사 설립 에피소드를 다루고 있음",
      "recommendation": "EP2에서 제거, EP3에서 상세 서술"
    },
    {
      "type": "missing",
      "episode": 4,
      "description": "series_plan의 key_event '구자경 회장 취임'이 EP4에 없음",
      "recommendation": "EP4 도입부에 추가 필요"
    },
    {
      "type": "flow_break",
      "episodes": [3, 4],
      "description": "EP3 마지막 씬과 EP4 첫 씬 사이 시간 점프가 15년으로 설명 없음",
      "recommendation": "EP4 첫 씬에 브릿지 나레이션 추가"
    }
  ],
  "per_episode": [
    {"episode": 1, "scene_count": 18, "status": "ok"},
    {"episode": 2, "scene_count": 14, "status": "thin"}
  ]
}
```

## 작업 흐름

1. series_plan.json 로드
2. 전 편 scene_specs.json 로드
3. 편별 key_events 커버리지 확인
4. 인접 편 간 scope 경계 검토
5. narration 텍스트 중복 탐지 (핵심 문장 반복 여부)
6. series_review.json 저장
7. 수정 권고사항 요약 출력

## 점수 기준

- 90점 이상: Stage 3 진행 가능
- 70~89점: 권고 수정 후 재검토
- 70점 미만: 특정 편 Stage 2 재실행 권고
