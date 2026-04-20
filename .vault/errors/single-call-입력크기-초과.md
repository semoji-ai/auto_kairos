---
tags: [error, pipeline, single_call]
date: 2026-03-17
severity: major
pipeline-step: step_6d
agent: visual-composer
status: resolved
recurrence: 0
---

# single_call 입력 크기 초과로 JSON 출력 실패

## 증상
step_6d(motion_planning)에서 scene_specs.json(173KB)을 통째로 프롬프트에 주입 → LLM이 응답 생성 실패 또는 truncated JSON 출력.

## 원인
scene_specs.json이 97씬 × 1.7KB ≈ 173KB. `_run_single_call_step`에서 `[:80000]`으로 잘라도 절반만 전달됨. motion_plan은 전체 씬 정보가 필요하지만, visualization 상세 데이터(items, creative 등)는 불필요.

## 해결
`_run_single_call_step`에서 `motion_planning` 스텝일 때 축약 데이터만 추출:
```python
if step_name == "motion_planning":
    compact_scenes = [{
        "sceneNumber": s["sceneNumber"],
        "chapter": s["chapter"],
        "title": s["title"],
        "durationFrames": s["durationFrames"],
        "reveal": cr.get("reveal"), "emphasis": cr.get("emphasis"), "mood": cr.get("mood"),
        "hasChart": bool(...), "hasImage": bool(...), "hasMap": bool(...),
        "itemCount": len(items),
    } for s in scenes]
```
97씬 × ~200B ≈ 20KB로 축소.

## 수정 파일
- `auto_agent/orchestrator/runner.py` — `_run_single_call_step`에 motion_planning 축약 로직

## 재발 방지
- single_call 스텝에서 입력 파일이 50KB 이상이면 축약 검토
- 각 스텝이 실제로 필요한 필드만 전달하도록 프롬프트 설계
