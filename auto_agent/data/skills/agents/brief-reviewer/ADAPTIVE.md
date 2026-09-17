# 기획안 검수 — 근거에 따른 제한적 수정

입력 editorial_brief.v{N}.json을 평가하고 지정된 brief_review_feedback.v{N}.json을 저장하세요.
핵심 질문, 사용자 필수 내용, 제외 범위와 채널 문체가 판단 기준입니다.

## 품질 게이트

- coherence_spine.spine_question이 명확한 하나의 질문인가?
- layer_map의 각 막, hidden_truth/human_truth/present_connection의 spine_link,
  must_cover의 연결이 같은 질문을 설명하는가?
- 근거 없는 사실을 확정하지 않았는가? 미확인 출처는 needs_research로 남기는가?
- 사용자 의도와 필수 에피소드를 보존했는가?

spine 게이트가 실패하면 점수에 관계없이 REVISE입니다.
기획 구체성 40점(서사 15, 인물의 구체성 15, 반전 10), 실행 가능성 30점
(must_cover 10, 근거 앵커 10, 도입과 본론 역할 구분 10), 채널 DNA 30점
(3단 서사 7, 이면의 진실 7, 현재 연결 6, coherence_spine 정합도 10)의 기존 배점을 유지합니다.
체크박스 채우기, 추상 플레이스홀더, 출처 없이 available로 선언한 앵커는 통과 근거가 아닙니다.

## 수정과 종료

먼저 한 번 평가합니다. 통과했으면 즉시 끝냅니다.
REVISE/FAIL이면 입력에 이미 있는 근거로 해결할 수 있는 구체적 결함만 한 차례 묶어서 수정할 수 있습니다.
새로운 조사·사용자 결정이 필요하면 재작성하지 말고 해당 필요 사항을 보고합니다.
수정할 경우 사용 중인 버전을 덮어쓰지 말고 사용하지 않은 다음 버전으로 저장합니다.
한 번의 최종 평가로 개선과 게이트 통과가 확인된 경우에만 editorial_brief.json 선택 상태를 새 버전으로 갱신합니다.
품질 하락이나 미해결 결함은 그대로 기록하고 종료합니다. 점수 상승을 위한 반복 재채점은 하지 않습니다.

## 피드백 계약

version, reviewed_at, round, score_total, score_breakdown, verdict,
previous_score, score_delta, field_feedback, antipatterns_detected,
revision_instructions, next_action 필드를 유지합니다.
score_breakdown.spine_blocking에는 failed_gates와 reasons를 기록합니다.
PASS는 90점 이상이면서 모든 게이트를 통과할 때만 가능합니다.
75~89점은 REVISE, 75점 미만은 FAIL입니다. 게이트 실패는 항상 REVISE입니다.
추가로 reviewed_brief_path, stop_reason, unresolved_issues를 기록해 실제 평가한 버전과 종료 사유를 남깁니다.
요청받은 피드백 경로에 최종 결과를 기록하고, 마지막 응답은 경로와 핵심 결함만 보고하세요.
