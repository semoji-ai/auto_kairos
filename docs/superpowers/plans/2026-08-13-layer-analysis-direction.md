# 레이어 분리 판단 연출 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 씬 레이어 분리 판단을 사물 분류에서 연출 의도 기반으로 바꾼다 — 씬 이미지를 만든 `image_prompt` 를 분석에 전달하고, 요소마다 무엇을 할지(`intent`)를 요구해 불필요한 분리를 막는다.

**Architecture:** `analyze_scene_layers` 의 프롬프트와 입력 파라미터를 확장하고, 요소 스키마에 `name_en`·`intent` 를 추가한다. 라우터가 씬의 `image_prompt`·앞뒤 씬·프로젝트 브리핑을 조립해 넘긴다. 새로 얻은 `intent` 는 요소 사이드카에 저장되어 모션 플랜의 힌트가 되고, 패널 모달에 표시된다.

**Tech Stack:** Python 3.11 stdlib, 기존 `llm.run_orchestrator`(codex 멀티모달), JSON Schema, pytest, ES5 브라우저 JS.

## Global Constraints

- `MAX_ELEMENTS = 4` 는 **상한이지 목표가 아니다.** 요소 1개(인물+배경 2레이어)가 가장 흔한 정답이고, 4개는 예외적이다.
- **인물은 항상 분리한다** — 움직일 것이 없어 보여도 까딱임(`bob`)의 근거가 있다.
- 원고 전문을 분석 프롬프트에 넣지 않는다. 프로젝트 브리핑(`vault.read_context`, 600자 요약)으로 대신한다.
- 모션 어휘는 실제 구현된 것만 쓴다: 레이어 `slide_in` `fade_in` `pop` `drift` `bob` `shake` `zoom_emphasis` `exit_fade`, 카메라 `none` `slow_zoom_in` `slow_zoom_out` `pan_left` `pan_right`.
- 현재 모션 규칙(캐릭터만 모션, 사물 모션 금지)은 이 계획에서 바꾸지 않는다.
- 한국어 주석·문서·UI 문구에 일본어 가나와 한자를 쓰지 않는다.
- 새 의존성을 추가하지 않는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/schemas/layer_elements.schema.json` | 분석 결과 계약. `name_en`·`intent` 추가 |
| `backend/motion.py` | 모션 어휘의 단일 출처. `PRESET_GUIDE` 를 공개해 분석이 같은 목록을 쓰게 함 + 사이드카 `intent` 를 모션 프롬프트에 포함 |
| `backend/imagegen.py` | 분석 프롬프트 재작성, 파라미터 확장, 사이드카에 `name_en`·`intent` 저장 |
| `backend/router.py` | 씬 맥락(이미지 프롬프트·앞뒤 씬·브리핑) 조립 |
| `cep/com.autokairos.pd/js/storyboard.js` | 모달에 `intent` 표시, 상한 문구 수정 |
| `tests/test_layer_analysis.py` (신규) | 프롬프트 조립·스키마·사이드카 검증 |

---

### Task 1: 스키마 + 모션 어휘 공개

**Files:**
- Modify: `backend/schemas/layer_elements.schema.json`
- Modify: `backend/motion.py:12-21`
- Test: `tests/test_layer_analysis.py` (신규)

**Interfaces:**
- Produces:
  - `motion.PRESET_GUIDE: str` — 레이어 모션 8종 설명(기존 `_PRESET_GUIDE` 의 공개 이름)
  - `motion.CAMERA_GUIDE: str` — 카메라 5종 설명
  - 스키마의 요소 필수 필드: `name`, `name_en`, `location`, `kind`, `reason`, `intent`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_analysis.py`:

```python
"""레이어 분석 — 연출 의도 기반 판단(프롬프트 조립·스키마·사이드카)."""
import json
from pathlib import Path

from backend import imagegen, motion

SCHEMA = Path(__file__).resolve().parents[1] / "backend" / "schemas" / "layer_elements.schema.json"


def test_motion_vocabulary_is_public():
    """분석과 모션 플랜이 같은 어휘 목록을 써야 한다 — 출처는 motion 한 곳."""
    assert isinstance(motion.PRESET_GUIDE, str)
    for name in ("slide_in", "fade_in", "pop", "drift", "bob", "shake",
                 "zoom_emphasis", "exit_fade"):
        assert name in motion.PRESET_GUIDE, name
    for cam in ("slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"):
        assert cam in motion.CAMERA_GUIDE, cam
    assert motion._PRESET_GUIDE is motion.PRESET_GUIDE      # 기존 사용처 보존


def test_schema_requires_intent_and_english_name():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    item = schema["properties"]["elements"]["items"]
    assert set(item["required"]) == {"name", "name_en", "location", "kind", "reason", "intent"}
    assert item["properties"]["name_en"]["type"] == "string"
    assert item["properties"]["intent"]["type"] == "string"
    assert item["additionalProperties"] is False
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py -q`
Expected: FAIL — `AttributeError: module 'backend.motion' has no attribute 'PRESET_GUIDE'`

- [ ] **Step 3: 구현**

`backend/motion.py` 의 `_PRESET_GUIDE = (` 블록을 아래로 교체한다(내용은 그대로, 공개 이름 + 카메라 어휘 추가):

```python
PRESET_GUIDE = (
    "- slide_in: 화면 밖에서 등장(direction 필수). 등장 연출.\n"
    "- fade_in: 서서히 나타남.\n"
    "- pop: 통통 튀며 등장(스케일 바운스). 강조 등장.\n"
    "- drift: 천천히 떠다님(미세 이동). 정적 씬의 생동감.\n"
    "- bob: 위아래로 살랑임. 캐릭터 idle 기본.\n"
    "- shake: 짧고 빠른 흔들림. 충격·놀람.\n"
    "- zoom_emphasis: 살짝 커졌다 복귀. 내레이션 강조 시점.\n"
    "- exit_fade: 서서히 사라짐(씬 끝 무렵).\n"
)

CAMERA_GUIDE = (
    "- slow_zoom_in / slow_zoom_out: 씬 전체를 천천히 밀거나 당김.\n"
    "- pan_left / pan_right: 씬 전체를 옆으로 흘림.\n"
    "- none: 카메라 무브 없음.\n"
)

_PRESET_GUIDE = PRESET_GUIDE        # 기존 사용처(plan_scene_motion) 보존
```

`backend/schemas/layer_elements.schema.json` 을 아래로 교체한다:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["elements"],
  "properties": {
    "elements": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "name_en", "location", "kind", "reason", "intent"],
        "properties": {
          "name": { "type": "string" },
          "name_en": { "type": "string" },
          "location": { "type": "string" },
          "kind": { "type": "string", "enum": ["character", "object"] },
          "reason": { "type": "string" },
          "intent": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py tests/test_motion.py -q`
Expected: PASS — `test_motion.py` 가 `_PRESET_GUIDE` 를 참조하고 있어도 별칭으로 통과해야 한다

- [ ] **Step 5: 커밋**

```bash
git add backend/motion.py backend/schemas/layer_elements.schema.json tests/test_layer_analysis.py
git commit -m "feat(layers): 요소 스키마에 name_en·intent 추가 + 모션 어휘 공개"
```

---

### Task 2: 분석 프롬프트를 연출 기반으로 재작성

**Files:**
- Modify: `backend/imagegen.py` — `analyze_scene_layers` (약 273-305행)
- Test: `tests/test_layer_analysis.py` (추가)

**Interfaces:**
- Consumes: `motion.PRESET_GUIDE`, `motion.CAMERA_GUIDE`
- Produces:
  - `build_layer_analysis_prompt(*, narration: str = "", context: str = "", image_prompt: str = "", neighbors: str = "", briefing: str = "") -> str`
  - `analyze_scene_layers(proj_dir, scene_image, *, narration="", context="", image_prompt="", neighbors="", briefing="", on_line=None) -> dict`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_analysis.py` 에 이어붙인다:

```python
def test_prompt_carries_direction_inputs():
    """씬 이미지를 만든 프롬프트가 연출 의도의 원본 — 반드시 전달돼야 한다."""
    p = imagegen.build_layer_analysis_prompt(
        narration="당시 전기차는 느리다는 이미지가 강했다.",
        context="제목: 속도 / 요약: 이미지를 깨는 순간",
        image_prompt="어두운 도로 위를 강하게 가속하며 출발하는 빨간 전기 스포츠카, 속도감 있는 빛의 궤적",
        neighbors="앞 씬(continue): 창업 — 2003년 설립\n뒤 씬(cut): 위기 — 파산 직전",
        briefing="테슬라 창업 서사. 인물 중심, 담백한 톤.")
    assert "빛의 궤적" in p                      # image_prompt 본문
    assert "당시 전기차는" in p                  # narration
    assert "앞 씬(continue)" in p                # 앞뒤 씬
    assert "담백한 톤" in p                      # 브리핑
    for name in ("slide_in", "bob", "zoom_emphasis", "exit_fade"):
        assert name in p, name                   # 실행 가능한 모션 어휘
    assert "slow_zoom_in" in p                   # 카메라 어휘


def test_prompt_demands_minimality_and_intent():
    """연출로 물으면 없는 움직임을 지어내기 쉽다 — 최소성과 intent를 프롬프트가 강제해야 한다."""
    p = imagegen.build_layer_analysis_prompt()
    assert "인물 1장 + 배경 1장" in p            # 최소 구성 반례
    assert "intent" in p
    assert "배경에 남긴다" in p                  # intent를 못 대면 분리하지 않는다
    assert "name_en" in p                        # 영어 이름 요구
    assert str(imagegen.MAX_ELEMENTS) in p       # 상한 명시


def test_prompt_handles_empty_inputs():
    p = imagegen.build_layer_analysis_prompt()
    assert "(없음)" in p and len(p) > 200


def test_analyze_passes_new_context_through(tmp_path, monkeypatch):
    seen = {}

    def _fake(prompt, proj_dir, **kw):
        seen["prompt"] = prompt
        (tmp_path / ".layer_analysis.json").write_text(json.dumps({"elements": [
            {"name": "차량", "name_en": "red sports car", "location": "중앙",
             "kind": "object", "reason": "가속을 표현", "intent": "slide_in 좌→우"}]}),
            encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(imagegen.llm, "run_orchestrator", _fake)
    res = imagegen.analyze_scene_layers(tmp_path, str(tmp_path / "s.png"),
                                        image_prompt="빛의 궤적", briefing="브리핑")
    assert "빛의 궤적" in seen["prompt"] and "브리핑" in seen["prompt"]
    assert res["elements"][0]["intent"] == "slide_in 좌→우"
    assert res["elements"][0]["name_en"] == "red sports car"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py -q`
Expected: FAIL — `AttributeError: module 'backend.imagegen' has no attribute 'build_layer_analysis_prompt'`

- [ ] **Step 3: 구현**

`backend/imagegen.py` 의 `analyze_scene_layers` 전체를 아래로 교체한다:

```python
def build_layer_analysis_prompt(*, narration: str = "", context: str = "",
                                image_prompt: str = "", neighbors: str = "",
                                briefing: str = "") -> str:
    """레이어 분석 프롬프트 — 사물 분류가 아니라 '이 장면을 어떻게 움직일 것인가'에서 역산한다.

    씬 이미지는 image_prompt로 생성됐고 그 프롬프트는 나레이션을 표현하려고 쓰였다.
    즉 연출 의도가 거기 이미 적혀 있으므로, 그것을 판단의 출발점으로 삼는다."""
    from backend import motion
    return (
        "너는 모션그래픽 연출가다. 첨부한 씬 이미지를 레이어로 분리하려 한다.\n"
        "분류가 목적이 아니다 — **이 장면을 효과적으로 연출하려면 무엇이 따로 떨어져 있어야 하는가**를 판단해라.\n\n"
        f"## 이 그림을 만든 연출 의도(이미지 생성 프롬프트)\n{image_prompt or '(없음)'}\n\n"
        f"## 내레이션\n{narration or '(없음)'}\n\n"
        f"## 씬 맥락\n{context or '(없음)'}\n\n"
        f"## 앞뒤 씬\n{neighbors or '(없음)'}\n\n"
        f"## 프로젝트 브리핑\n{briefing or '(없음)'}\n\n"
        "## 판단 순서\n"
        "1) 이 씬의 연출 의도는 무엇인가 — 위 이미지 생성 프롬프트가 노린 것.\n"
        "2) 그 의도를 살리려면 무엇이 움직이거나 깊이(앞뒤)를 가져야 하는가.\n"
        "3) 그 움직임을 만들려면 어떤 요소가 따로 떨어져 있어야 하는가. 그것만 목록에 넣는다.\n\n"
        f"## 사용 가능한 레이어 모션\n{motion.PRESET_GUIDE}\n"
        f"## 사용 가능한 카메라\n{motion.CAMERA_GUIDE}\n"
        "여기 없는 동작은 구현할 수 없다. 목록 안에서만 연출을 구상해라.\n\n"
        "## 최소성(중요)\n"
        f"요소는 최대 {MAX_ELEMENTS}개지만 그것은 상한이지 목표가 아니다. "
        "연출에 필요한 최소로 나눈다. **인물 한 명이 말하는 씬은 인물 1장 + 배경 1장이면 충분하다.** "
        "더 쪼개도 연출이 나아지지 않으면 쪼개지 않는다. 요소 1~2개가 가장 흔한 정답이다.\n"
        "각 요소에 intent(그 레이어로 무엇을 할 것인가)를 쓸 수 없다면 분리 근거가 없는 것이므로 "
        "목록에서 빼고 배경에 남긴다.\n\n"
        "## 항상 지키는 규칙\n"
        "- 인물(사람·캐릭터·생명체)은 움직일 것이 없어 보여도 각각 분리한다 — 까딱임(bob)으로 화면이 죽지 않게 한다. "
        "다른 것에 가려져 일부만 보여도 포함한다.\n"
        "- 인물을 앞에서 가리는 전경은 분리해야 앞뒤 겹침이 유지된다.\n"
        "- 정적인 배경·장식은 분리하지 않고 배경에 남긴다.\n"
        "- 앞 씬과 이어지는 샷(continue)이면 레이어 구성을 앞 씬과 맞춰 연결이 끊기지 않게 한다.\n"
        "- 요소는 '가장 뒤'에서 '가장 앞' 순서로 나열한다(뒤→앞). 가리는 사물은 가려지는 인물보다 앞에 온다.\n\n"
        "## 각 요소에 쓸 것\n"
        "- name: 짧은 한국어 이름\n"
        "- name_en: 짧은 영어 이름(레이어 분리 모델 프롬프트에 쓴다)\n"
        "- location: 화면 내 위치\n"
        "- kind: 'character' 또는 'object'\n"
        "- reason: 왜 이것이 따로 떨어져야 하는가 — 연출 관점으로 한 줄\n"
        "- intent: 이 레이어로 무엇을 할 것인가 — 위 모션 어휘로. 예: 'slide_in 좌→우 후 drift로 가속 지속'"
    )


def analyze_scene_layers(proj_dir: Path, scene_image: str, *,
                         narration: str = "", context: str = "", image_prompt: str = "",
                         neighbors: str = "", briefing: str = "", on_line=None) -> dict:
    """씬 이미지+연출 맥락을 분석해 '연출에 필요한' 레이어만 선별.
    {elements:[{name,name_en,location,kind,reason,intent}], dropped:[...]} 또는 error."""
    prompt = build_layer_analysis_prompt(narration=narration, context=context,
                                         image_prompt=image_prompt, neighbors=neighbors,
                                         briefing=briefing)
    out_json = proj_dir / ".layer_analysis.json"
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_LAYER_SCHEMA),
                               output_last=str(out_json), images=[scene_image], on_line=on_line)
    if res.get("returncode") != 0 or not out_json.is_file():
        return {"error": "분석 실패", "elements": [], "dropped": []}
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "분석 결과 파싱 실패", "elements": [], "dropped": []}
    return {**apply_element_budget(data.get("elements", []))}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py tests/test_imagegen.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py tests/test_layer_analysis.py
git commit -m "feat(layers): 분석을 연출 의도 기반으로 — image_prompt·모션 어휘·최소성"
```

---

### Task 3: 라우터가 연출 맥락을 조립

**Files:**
- Modify: `backend/router.py` — `/api/scenes/analyze-layers` 핸들러(약 494-514행)
- Test: `tests/test_layer_analysis.py` (추가)

**Interfaces:**
- Consumes: `imagegen.analyze_scene_layers(..., image_prompt=, neighbors=, briefing=)`
- Produces: `router._neighbor_context(scenes_list: list, scene_number) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_analysis.py` 에 이어붙인다:

```python
def test_neighbor_context_builds_both_sides():
    from backend import router
    ss = [{"sceneNumber": 1, "title": "창업", "narration": "2003년 설립됐다."},
          {"sceneNumber": 2, "title": "속도", "narration": "로드스터가 등장했다.",
           "shot_relation": "continue"},
          {"sceneNumber": 3, "title": "위기", "narration": "파산 직전까지 갔다.",
           "shot_relation": "cut"}]
    ctx = router._neighbor_context(ss, 2)
    assert "창업" in ctx and "위기" in ctx
    assert "continue" in ctx                      # 이 씬이 앞 씬과 이어지는지
    assert router._neighbor_context(ss, 1).startswith("앞 씬: (없음)")
    assert "뒤 씬: (없음)" in router._neighbor_context(ss, 3)
    assert router._neighbor_context([], 1)        # 빈 목록도 문자열 반환


def test_analyze_endpoint_passes_direction_context(tmp_path, monkeypatch):
    import backend.router as r
    from backend.jobs import JobRegistry
    proj = tmp_path / "p"
    (proj / "storyboard").mkdir(parents=True)
    (proj / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a", "title": "속도", "narration": "빠르다.",
         "visual_summary": "가속 순간", "image_prompt": "빛의 궤적이 있는 빨간 스포츠카",
         "imageRef": "storyboard/sb_a.png"},
        {"sceneNumber": 2, "sceneId": "b", "title": "위기", "narration": "위험했다."}]}),
        encoding="utf-8")
    seen = {}

    def _fake(proj_dir, scene_image, **kw):
        seen.update(kw)
        return {"elements": [], "dropped": []}

    monkeypatch.setattr(r.imagegen, "analyze_scene_layers", _fake)
    monkeypatch.setattr(r.vault, "read_context", lambda d: "프로젝트 브리핑 요약")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = r.handle_request("POST", "/api/scenes/analyze-layers", {},
                               {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200
    assert seen["image_prompt"] == "빛의 궤적이 있는 빨간 스포츠카"
    assert "위기" in seen["neighbors"]
    assert seen["briefing"] == "프로젝트 브리핑 요약"
    assert "속도" in seen["context"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py -q`
Expected: FAIL — `AttributeError: module 'backend.router' has no attribute '_neighbor_context'`

- [ ] **Step 3: 구현**

`backend/router.py` 의 `_codex_status` 함수 아래에 추가한다:

```python
def _neighbor_context(scenes_list: list, scene_number) -> str:
    """앞뒤 씬 한 줄 요약 + 이 씬의 shot_relation.
    이어지는 샷(continue)이면 레이어 구성을 앞 씬과 맞춰야 연결이 끊기지 않는다."""
    def _line(s):
        if not s:
            return "(없음)"
        nar = (s.get("narration") or "").strip().replace("\n", " ")[:60]
        return f"{s.get('title', '') or '(제목 없음)'} — {nar}"

    idx = next((i for i, s in enumerate(scenes_list)
                if s.get("sceneNumber") == scene_number), None)
    if idx is None:
        return "앞 씬: (없음)\n뒤 씬: (없음)"
    prev = scenes_list[idx - 1] if idx > 0 else None
    nxt = scenes_list[idx + 1] if idx + 1 < len(scenes_list) else None
    rel = (scenes_list[idx].get("shot_relation") or "").strip()
    head = f"앞 씬: {_line(prev)}"
    if rel:
        head += f"  (이 씬은 앞 씬과 {rel})"
    return head + f"\n뒤 씬: {_line(nxt)}"
```

`/api/scenes/analyze-layers` 핸들러에서 `ctx_str` 을 만들고 호출하는 두 줄을 아래로 교체한다:

```python
        ctx_str = f"제목: {sc.get('title', '')} / 요약: {sc.get('visual_summary', '')}"
        res = imagegen.analyze_scene_layers(
            proj_dir, str(proj_dir / sc["_image"]),
            narration=sc.get("narration", "") or "", context=ctx_str,
            image_prompt=sc.get("image_prompt", "") or "",
            neighbors=_neighbor_context(data.get("scenes", []), b.get("sceneNumber")),
            briefing=vault.read_context(proj_dir),
            on_line=lambda ln: jobs.append_log(jid, ln))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py tests/test_router.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_layer_analysis.py
git commit -m "feat(layers): 분석에 image_prompt·앞뒤 씬·프로젝트 브리핑 전달"
```

---

### Task 4: intent를 사이드카·모션 플랜·패널로

**Files:**
- Modify: `backend/imagegen.py` — `split_scene_to_elements` 의 `specs.append`(약 709행)
- Modify: `backend/motion.py` — `plan_scene_motion`(약 58-95행)
- Modify: `cep/com.autokairos.pd/js/storyboard.js` — `_renderLayerPane`, `_enforceLayerCap`
- Test: `tests/test_layer_analysis.py`, `tests/test_panel_structure.py` (추가)

**Interfaces:**
- Consumes: `imagegen.load_element_specs(out_base, sid) -> list`
- Produces: 사이드카 요소에 `name_en`·`intent` 키 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_analysis.py` 에 이어붙인다:

```python
def test_specs_sidecar_keeps_intent(tmp_path, monkeypatch):
    """분리 시점의 연출 의도가 남아야 모션 플랜이 이어받을 수 있다."""
    monkeypatch.setattr(imagegen, "_run_fal_image",
                        lambda proj_dir, out, prompt, images=None, post=None:
                            (Path(out).write_bytes(b"\x89PNG"),
                             {"status": "completed", "path": str(out)})[1])
    monkeypatch.setattr(imagegen, "load_style", lambda: "STYLE")
    monkeypatch.setattr(imagegen, "_scene_size", lambda p: None)
    monkeypatch.setattr(imagegen, "chroma_key", lambda a, b, key=None: {"transparent_ratio": 0.5})
    monkeypatch.setattr(imagegen, "position_score", lambda a, b: 0.9)
    monkeypatch.setattr(imagegen, "flatten_colors", lambda p: True)
    from PIL import Image
    Image.new("RGB", (8, 8)).save(tmp_path / "s.png")

    imagegen.split_scene_to_elements(tmp_path, str(tmp_path / "s.png"), "ab", [
        {"name": "차량", "name_en": "red car", "location": "중앙", "kind": "object",
         "reason": "가속 표현", "intent": "slide_in 좌→우"}])
    specs = imagegen.load_element_specs(tmp_path / "layers", "ab")
    assert specs[0]["intent"] == "slide_in 좌→우"
    assert specs[0]["name_en"] == "red car"


def test_motion_prompt_includes_intent(tmp_path, monkeypatch):
    from backend import motion as m
    seen = {}

    def _fake(prompt, proj_dir, **kw):
        seen["prompt"] = prompt
        return {"returncode": 1}

    (tmp_path / "layers").mkdir()
    (tmp_path / "layers" / "ab__0_인물_char.png").write_bytes(b"\x89PNG")
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "ab", "narration": "말한다."}]}), encoding="utf-8")
    (tmp_path / "layers" / "ab__kinds.json").write_text(
        json.dumps({"ab__0_인물_char": "character"}), encoding="utf-8")
    imagegen.write_element_specs(tmp_path / "layers", "ab", [
        {"layer": "ab__0_인물_char", "index": 0, "name": "인물", "name_en": "person",
         "location": "좌측", "kind": "character", "intent": "bob으로 생동감"}])
    monkeypatch.setattr(m.llm, "run_orchestrator", _fake)
    m.plan_scene_motion(tmp_path, 1)
    assert "bob으로 생동감" in seen["prompt"]
```

`tests/test_panel_structure.py` 에 이어붙인다:

```python
def test_layer_modal_shows_intent():
    """왜 나뉘는지를 연출 언어로 보여준다. 상한은 목표가 아니므로 문구도 바꾼다."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "e.intent" in js
    assert "개 선택 (최대 " in js
    assert "선택 (배경 1장이 자동으로 더해집니다)" not in js
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_analysis.py tests/test_panel_structure.py -q`
Expected: FAIL — `KeyError: 'intent'` 및 `AssertionError`

- [ ] **Step 3: 구현**

`backend/imagegen.py` 의 `specs.append(...)` 블록(약 709행)을 교체한다:

```python
        specs.append({"layer": stem, "index": i, "name": el.get("name", ""),
                      "name_en": el.get("name_en", ""),
                      "location": el.get("location", ""), "kind": el.get("kind", "object"),
                      "intent": el.get("intent", "")})
```

`backend/motion.py` 의 `plan_scene_motion` 에서 `dur = _scene_duration(proj_dir, s)` 바로 아래에 추가한다:

```python
    # 분리 시점의 연출 의도 — 있으면 모션이 그것과 어긋나지 않게 한다
    from backend import imagegen
    intents = []
    for spec in imagegen.load_element_specs(proj_dir / "layers", sid):
        if spec.get("layer") in chars and (spec.get("intent") or "").strip():
            intents.append(f"- {spec['layer']}: {spec['intent']}")
    intent_block = ("\n## 분리 시점의 연출 의도(참고)\n" + "\n".join(intents) + "\n") if intents else ""
```

그리고 같은 함수의 프롬프트 문자열에서 `f"## 사용 가능한 모션 프리셋\n{_PRESET_GUIDE}\n"` 앞에 `intent_block` 을 끼워 넣는다:

```python
        f"## 레이어(이 이름을 정확히 그대로 사용)\n" + "\n".join(f"- {e}" for e in chars) + "\n"
        + intent_block + "\n"
        f"## 사용 가능한 모션 프리셋\n{_PRESET_GUIDE}\n"
```

`cep/com.autokairos.pd/js/storyboard.js` 의 `_renderLayerPane` 안 `row()` 헬퍼에서, `reason` 을 보여주는 줄 뒤에 `intent` 줄을 추가한다:

```javascript
      + (e.reason ? '<br><span style="font-size:10px;color:#9aa0a6">' + _esc(e.reason) + '</span>' : '')
      + (e.intent ? '<br><span style="font-size:10px;color:#7ab0ff">▸ ' + _esc(e.intent) + '</span>' : '')
```

같은 파일 `_enforceLayerCap` 의 안내 문구를 교체한다:

```javascript
  if (note) note.textContent = on + "개 선택 (최대 " + MAX_LAYER_ELEMENTS + " — 배경 1장이 자동으로 더해집니다)";
```

- [ ] **Step 4: 테스트 통과 확인**

Run:
```bash
python3 -m pytest tests/test_layer_analysis.py tests/test_panel_structure.py tests/test_motion.py tests/test_layer_edit.py -q
node --check cep/com.autokairos.pd/js/storyboard.js
```
Expected: PASS + 문법 오류 없음

- [ ] **Step 5: 전체 회귀**

Run:
```bash
python3 -m pytest tests/ -q \
  --ignore=tests/test_research_web_smoke.py \
  --ignore=tests/test_research_web_agent.py \
  --ignore=tests/test_research_news.py \
  --ignore=tests/test_research_lanes_basic.py
```
Expected: PASS — 직전 기준선은 652 passed. 실패가 나면 그 테스트가 옛 스키마(`name`·`location`·`kind`·`reason` 만)로 요소 dict를 만들고 있는지 확인하고, `name_en`·`intent` 를 채워 넣는다.

- [ ] **Step 6: 커밋**

```bash
git add backend/imagegen.py backend/motion.py cep/com.autokairos.pd/js/storyboard.js tests/test_layer_analysis.py tests/test_panel_structure.py
git commit -m "feat(layers): intent를 사이드카·모션 플랜·패널로 전달"
```

---

## 사람이 직접 확인해야 하는 것

테스트가 보장하는 것은 "맥락이 실제로 전달된다"까지다. **판단이 나아졌는지는 자동 검증할 수 없다.**

1. 인물이 한 명 말하는 씬에서 요소가 1개(인물)만 나오는지 — 최소성이 작동하는지.
2. `image_prompt` 에 연출 의도가 뚜렷한 씬(예: `projects/tesla` 씬 2의 "속도감 있는 빛의 궤적")에서 이전보다 나은 분리가 나오는지. 같은 씬을 이전 프롬프트와 새 프롬프트로 각각 분석해 비교한다(분석 LLM 호출 2회).
3. `intent` 가 실제로 실행 가능한 모션 어휘로 나오는지, 아니면 목록 밖 동작을 지어내는지.
