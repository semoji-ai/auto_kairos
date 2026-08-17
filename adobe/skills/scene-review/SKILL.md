---
name: scene-review
description: 분석된 씬 목록을 읽고 레이아웃 적합도·연결성·전체 흐름을 권고(advisory)로 검토한다
---

# Scene Review (씬 검토 — 권고)

## 이 스킬의 임무

이미 분석이 끝난 씬 목록을 읽고, 각 씬의 연출이 내용과 흐름에 맞는지를 **검토**합니다.
프롬프트에는 씬 목록 요약(sceneNumber / layout / shot_relation / characters / location / narration)과
편집 브리프(editorial brief)가 주입됩니다.

### 절대 규칙

- 당신은 **검토만** 합니다. 씬을 새로 쓰거나 고치지 않습니다.
- 이 검토는 **권고(advisory)**입니다. 자동 수정 지시가 아니라, 운영자가 참고할 의견입니다.
- 씬 개수·번호를 바꾸지 않습니다. 평가만 덧붙입니다.

## 씬별 평가

각 씬마다 아래 세 가지를 판단합니다.

1. **layout_fit** — 레이아웃이 내용에 맞는가? `"ok"` 또는 `"warn"`
   - 수치·핵심 지표 강조 → `metric_spotlight`
   - 항목 나열 → `items_list`
   - 인용·발언 → `quote`
   - 짧은 테제·선언 한 줄 → `headline_only`
   - 서사·감정·분위기 → `cinematic`
   - 내용과 레이아웃이 어긋나면 `"warn"`, 적절하면 `"ok"`

2. **shot_relation_fit** — 컷/연속(cut/continue)이 서사 흐름에 맞는가? `"ok"` 또는 `"warn"`
   - 같은 장소·상황이 이어지는데 `cut`이면 `continue` 권장 → `"warn"`
   - 장소·시간이 바뀌었는데 `continue`면 `cut` 권장 → `"warn"`
   - 흐름에 맞으면 `"ok"`

3. **note** — 한 줄 평/권고 (왜 ok 또는 warn인지, 무엇을 권하는지)

## 전체 평가

- **flags** — 전체에서 특히 주의가 필요한 항목을, **원인 + 권고** 형태로 적습니다.
  - 예: `"씬7: 특허번호가 핵심 → metric_spotlight 권장"`
  - 예: `"씬3-4: 같은 장소 연속 → shot_relation continue 권장"`
- **overall** — 한 줄 총평.

## 출력

scene_review JSON만 출력합니다.

```json
{
  "scenes": [
    { "sceneNumber": 1, "layout_fit": "ok", "shot_relation_fit": "ok", "note": "..." }
  ],
  "flags": ["씬7: 특허번호 핵심 → metric_spotlight 권장"],
  "overall": "전반적으로 양호하나 일부 레이아웃 재검토 권장"
}
```

다시 강조: 이 결과는 **권고**이며 자동 수정 지시가 아닙니다.
