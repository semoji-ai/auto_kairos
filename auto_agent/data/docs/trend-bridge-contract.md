# Trend Bridge Contract

## Purpose

Stage 0 topic planning should rank not only hot keywords, but the bridge between:
- `trigger_keyword`: a live external signal
- `knowledge_anchor`: a channel-fit subject with depth
- `bridge_reason`: why the audience naturally moves from trigger to anchor

## Input Areas

Stage 0 digests should be built from bounded samples of:
- `market/trends/`
- `market/news/`
- `market/social/`
- `market/communities/`
- `insights/feedback/`
- `insights/performance/`
- `channels/{channel}/videos/`
- `channels/competitors/`

Collectors may keep their own raw file shapes. Stage 0 should consume compact digests, not recurse through the full vault at runtime.

## Trend Signal Fields

Raw trend signal notes should preserve these concepts when possible:

```yaml
source: youtube_trending | news | x | threads | community | competitor
observed_at: ISO-8601
keyword: string
summary: string
heat_score: 0-100
lifespan_hint: hours | days | weeks | evergreen
entities:
  - string
urls:
  - string
```

## Stage 4 Feedback Fields

Weekly feedback should surface bridge-learning, not only performance summary:
- `winning_bridge_patterns`
- `losing_bridge_patterns`
- `title_trigger_patterns`
- `competitor_lessons`
- `recommended_topic_directions`

## Stage 0 Candidate Fields

Each candidate should include:

```json
{
  "title": "주제 제목",
  "trigger_keyword": "실시간 화제 키워드",
  "knowledge_anchor": "깊이 있게 설명할 대상",
  "bridge_reason": "왜 이 트리거에서 이 앵커로 넘어오는지",
  "timing_window": "지금 바로 | 3일 내 | 1주 내 | evergreen",
  "angle": "차별화 각도",
  "hook": "핵심 훅",
  "topic_score": 504,
  "topic_type": "timely | evergreen"
}
```

## Scoring Guidance

Stage 0 should balance:
- `trend_heat`
- `channel_fit`
- `bridge_strength`
- `evergreen_depth`
- `competition_gap`

Purely hot keywords with no credible anchor should be downgraded.
Purely evergreen anchors with no current trigger should also be downgraded when timely planning is the goal.
