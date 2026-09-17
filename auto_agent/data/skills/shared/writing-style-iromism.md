---
name: writing-style-iromism
description: (대체됨) 구성/문체/연출로 3분할되었습니다. narrative-iromism · voice-iromism · direction-iromism를 사용하세요.
---

# (대체됨) writing-style-iromism

이 파일은 셋으로 나뉘었습니다. 문체를 처음부터 강제하면 작가가 형식을 맞추느라
내용이 밀리는 문제가 있어, 단계별로 나눠 주도록 바꿨습니다.

| 파일 | 내용 | 적용 단계 |
|---|---|---|
| `narrative-iromism.md` | 구성·서사 — 후킹, 서사 구조, 전환, 클로징, 페이싱 | 초고부터 (`step_2_draft`) |
| `voice-iromism.md` | 문체 — 시그니처 빈도, 톤·어미, 인용, 강조 마커 | 윤문부터 (`step_2_polish`) |
| `direction-iromism.md` | 연출 — layout·씬분할 규칙 | 씬분할부터 (`step_2`) |

파이프라인 스텝은 `style/narrative` · `style/voice` · `style/direction`으로 선언하고,
runner가 활성 `writing_style`에 맞는 변종으로 해석합니다
(`_resolve_style_skills`).
