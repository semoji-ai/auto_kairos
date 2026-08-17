# SEMOJI 기능 이식 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 모션 프리셋을 레이어 종류별로 개방하고(신규 `stamp`·`wiggle` 포함), 씬 `source`를 출처 자막으로 렌더하며, 패널에 도구 구역(SRT 가져오기·널 끼우기·프리셋 수동 적용)을 만든다.

**Architecture:** 모션 플랜의 허용 목록을 전역 `{bob, fade_in}`에서 종류별(인물/사물/배경)로 바꾸고 LLM 프롬프트를 그에 맞춘다. 출처 자막은 `build_scene.jsx`의 `buildSceneGroup`이 씬 접두사 레이어로 그려 재빌드에 안전하다. 도구는 새 `jsx/tools.jsx` + 백엔드 SRT 파서(`backend/srt.py`)로, 파싱은 pytest 검증을 위해 백엔드에 둔다.

**Tech Stack:** Python 3.11 stdlib(백엔드), pytest, ExtendScript(.jsx, ES5), CEP 패널 순수 ES5.

## Global Constraints

- 백엔드는 Python 3.11 **stdlib만** 쓴다. 새 서드파티 의존성을 넣지 않는다.
- jsx와 패널 JS는 **순수 ES5**다. `let`·`const`·화살표 함수·템플릿 리터럴·`class` 금지. `var`와 `function`만.
- 한국어 문자열·주석에 **일본어 가나와 한자를 쓰지 않는다.** 순수 한글과 영어만 쓴다.
- 인물 레이어에 오퍼시티 키프레임을 만들지 않는다(기존 규칙). 인물 허용 프리셋은 `bob`·`zoom_emphasis`뿐이다.
- 사물 허용 프리셋: `slide_in` `fade_in` `pop` `drift` `shake` `zoom_emphasis` `exit_fade` `stamp` `wiggle`. 배경은 모션 없음.
- 출처 자막 레이어는 **가이드 널에 페어런팅하지 않는다**(카메라 줌에 딸려가면 안 된다). 이름은 `S{번호}_출처`·`S{번호}_출처판`으로 접두사를 갖는다.
- SRT 파서는 마지막 큐가 자기 종료 시각을 갖게 한다(SEMOJI의 길이 0 결함을 고친다).
- 테스트에서 외부 API·LLM을 실제로 호출하지 않는다.
- jsx는 저장소 관례대로 정적 문자열 검사로 테스트한다.

## 파일 구조

| 파일 | 책임 | 상태 |
|---|---|---|
| `backend/motion.py` | 종류별 허용 목록·프롬프트·필터 | 수정 |
| `backend/schemas/motion_plan.schema.json` | enum에 `stamp`·`wiggle` | 수정 |
| `backend/manifest.py` | 씬 엔트리에 `source` | 수정 |
| `backend/srt.py` | SRT 파싱 | **신규** |
| `backend/router.py` | `POST /api/tools/srt-parse` | 수정 |
| `cep/com.autokairos.pd/jsx/build_scene.jsx` | `stamp`·`wiggle` 분기, 출처 자막 | 수정 |
| `cep/com.autokairos.pd/jsx/tools.jsx` | `akImportSrt`·`akInsertNull`·`akApplyPreset` | **신규** |
| `cep/com.autokairos.pd/js/storyboard.js` + `index.html` | 도구 구역 UI | 수정 |

---

### Task 1: 종류별 허용 목록 + 신규 프리셋 enum

**Files:**
- Modify: `backend/motion.py` (PRESET_GUIDE 13-22, `plan_scene_motion`의 프롬프트·필터 96-140)
- Modify: `backend/schemas/motion_plan.schema.json` (`type` enum)
- Test: `tests/test_motion_kinds.py` (신규)

**Interfaces:**
- Consumes: `imagegen.load_element_specs(out_base, sid) -> list`(항목에 `layer`·`kind`), 사이드카 `layers/{sid}__kinds.json`(`{stem: "character"|"object"}`)
- Produces: `motion.ALLOWED_BY_KIND = {"character": {...}, "object": {...}}`, `motion.layer_kinds(proj_dir, sid, elements) -> dict`(stem→`"character"|"object"`), `motion.filter_plan_moves(plan, kinds) -> dict`

**배경:** `plan_scene_motion`은 지금 캐릭터만 대상으로 LLM을 부르고 출력 필터가
`allowed = {"bob", "fade_in"}` 전역이다. 이것을 인물+사물 대상으로 넓히고 종류별
필터로 바꾼다. `_clamp_plan`·스키마 검증·`motion_path`는 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_motion_kinds.py`를 만든다.

```python
import json
from pathlib import Path

from backend import motion

SID = "abc123"


def _proj(tmp_path: Path, kinds: dict):
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    specs = []
    for i, (stem, kind) in enumerate(kinds.items()):
        (lay / (stem + ".png")).write_bytes(b"png")
        specs.append({"layer": stem, "index": i, "name": stem, "name_en": stem,
                      "location": "", "kind": kind, "intent": ""})
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_allowed_by_kind_contents():
    assert motion.ALLOWED_BY_KIND["character"] == {"bob", "zoom_emphasis"}
    assert "stamp" in motion.ALLOWED_BY_KIND["object"]
    assert "wiggle" in motion.ALLOWED_BY_KIND["object"]
    assert "bob" not in motion.ALLOWED_BY_KIND["object"]


def test_layer_kinds_from_sidecar(tmp_path):
    proj = _proj(tmp_path, {f"{SID}__0_kid": "character", f"{SID}__1_car": "object"})
    kinds = motion.layer_kinds(proj, SID, [f"{SID}__0_kid", f"{SID}__1_car"])
    assert kinds[f"{SID}__0_kid"] == "character"
    assert kinds[f"{SID}__1_car"] == "object"


def test_layer_kinds_char_suffix_fallback(tmp_path):
    """사이드카 없는 구버전 — _char 접미사로 인물을 가른다."""
    (tmp_path / "layers").mkdir(parents=True)
    kinds = motion.layer_kinds(tmp_path, SID, [f"{SID}__0_kid_char", f"{SID}__1_car"])
    assert kinds[f"{SID}__0_kid_char"] == "character"
    assert kinds[f"{SID}__1_car"] == "object"


def _plan(layer, types):
    return {"layers": [{"layer": layer,
                        "moves": [{"type": t, "start": 0, "duration": 1,
                                   "direction": None, "amount": None} for t in types]}],
            "camera": {"type": "none", "amount": None}}


def test_filter_keeps_char_bob_drops_slide(tmp_path):
    plan = _plan("kid", ["bob", "slide_in", "zoom_emphasis"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    got = [m["type"] for m in out["layers"][0]["moves"]]
    assert got == ["bob", "zoom_emphasis"]


def test_filter_keeps_object_stamp_wiggle_drops_bob(tmp_path):
    plan = _plan("car", ["stamp", "wiggle", "bob"])
    out = motion.filter_plan_moves(plan, {"car": "object"})
    got = [m["type"] for m in out["layers"][0]["moves"]]
    assert got == ["stamp", "wiggle"]


def test_filter_drops_unknown_layer_entirely(tmp_path):
    plan = _plan("ghost", ["bob"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    assert out["layers"] == []


def test_filter_drops_layer_with_no_surviving_moves(tmp_path):
    plan = _plan("kid", ["slide_in"])
    out = motion.filter_plan_moves(plan, {"kid": "character"})
    assert out["layers"] == []


def test_schema_has_new_presets():
    schema = json.loads(
        (Path("backend/schemas/motion_plan.schema.json")).read_text(encoding="utf-8"))
    enum = schema["properties"]["layers"]["items"]["properties"]["moves"]["items"][
        "properties"]["type"]["enum"]
    assert "stamp" in enum and "wiggle" in enum


def test_preset_guide_mentions_new_presets():
    assert "stamp" in motion.PRESET_GUIDE
    assert "wiggle" in motion.PRESET_GUIDE
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python3 -m pytest tests/test_motion_kinds.py -v`
Expected: FAIL — `ALLOWED_BY_KIND`·`layer_kinds`·`filter_plan_moves`가 없다.

- [ ] **Step 3: 스키마 enum을 넓힌다**

`backend/schemas/motion_plan.schema.json`의 `type` enum을 바꾼다.

```json
"enum": ["slide_in", "fade_in", "pop", "drift", "bob", "shake", "zoom_emphasis", "exit_fade", "stamp", "wiggle"]
```

- [ ] **Step 4: `motion.py`에 종류별 목록·헬퍼를 넣는다**

`PRESET_GUIDE`에 두 줄을 더한다(`exit_fade` 줄 다음).

```python
    "- stamp: 도장처럼 크게서 작아지며 쾅 등장(5프레임). 사물 강조 등장.\n"
    "- wiggle: 잔잔히 흔들림(익스프레션). 긴장·불안·강조 유지.\n"
```

`CAMERA_GUIDE` 아래에 넣는다.

```python
# 레이어 종류별 허용 프리셋 — 인물은 오퍼시티 키프레임 금지 규칙 때문에 fade류가 없다.
# 배경은 목록 자체가 없다(카메라가 담당).
ALLOWED_BY_KIND = {
    "character": {"bob", "zoom_emphasis"},
    "object": {"slide_in", "fade_in", "pop", "drift", "shake",
               "zoom_emphasis", "exit_fade", "stamp", "wiggle"},
}


def layer_kinds(proj_dir: Path, sid: str, elements: list) -> dict:
    """{stem: "character"|"object"} — 사이드카 우선, 없으면 _char 접미사."""
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(Path(proj_dir) / "layers", sid)}
    out = {}
    for stem in elements or []:
        sp = specs.get(stem) or {}
        kind = sp.get("kind")
        if kind not in ("character", "object"):
            kind = "character" if "_char" in stem else "object"
        out[stem] = kind
    return out


def filter_plan_moves(plan: dict, kinds: dict) -> dict:
    """LLM 플랜을 종류별 허용 목록으로 거른다. 모르는 레이어·빈 레이어는 버린다."""
    filtered = []
    for L in plan.get("layers", []):
        kind = kinds.get(L.get("layer"))
        if not kind:
            continue
        allowed = ALLOWED_BY_KIND.get(kind) or set()
        mvs = [m for m in L.get("moves", []) if m.get("type") in allowed]
        if mvs:
            filtered.append({"layer": L["layer"], "moves": mvs})
    plan["layers"] = filtered
    return plan
```

- [ ] **Step 5: `plan_scene_motion`이 사물까지 다루게 한다**

`plan_scene_motion` 안에서 바꾼다.

(a) 캐릭터만 남기던 부분을 종류 지도로 바꾼다. 기존:

```python
    if kinds:
        chars = [e for e in elements if kinds.get(e) == "character"]
    else:   # 사이드카 없는 구버전 분리 — 이름으로 LLM이 판단(프롬프트에서 인물만 지시)
        chars = elements
    if not chars:
        return {"error": "캐릭터 레이어 없음 — 현재 모션 규칙은 캐릭터(bob)만"}
```

교체:

```python
    kind_map = layer_kinds(proj_dir, sid, elements)
    chars = [e for e in elements if kind_map.get(e) == "character"]
    objs = [e for e in elements if kind_map.get(e) == "object"]
    if not chars and not objs:
        return {"error": "모션을 줄 요소 레이어 없음"}
```

(b) 프롬프트를 바꾼다. 기존 `prompt = (...)` 전체를 교체:

```python
    def _lines(names):
        return "\n".join(f"- {e}" for e in names) or "- (없음)"
    prompt = (
        "너는 모션그래픽 연출가다. 아래 씬의 레이어에 프리셋 모션을 설계해라.\n\n"
        f"## 내레이션(씬 길이 {dur:.1f}초)\n{s.get('narration', '') or '(없음)'}\n\n"
        f"## 인물 레이어(이 이름을 정확히 그대로 사용)\n{_lines(chars)}\n"
        f"## 사물 레이어(이 이름을 정확히 그대로 사용)\n{_lines(objs)}\n"
        + intent_block + "\n"
        f"## 사용 가능한 모션 프리셋\n{_PRESET_GUIDE}\n"
        "## 연출 원칙(엄수)\n"
        "1) 인물에는 bob(까딱임 idle)과 zoom_emphasis만 쓴다. 인물 기본은 bob 1개.\n"
        "2) 사물 기본은 모션 없음이다. 내레이션이 그 사물을 언급하거나 연출상 필요할 때만 준다 — "
        "등장(slide_in/pop/stamp)은 씬 앞부분, 강조(zoom_emphasis/shake/wiggle)는 해당 시점, "
        "퇴장(exit_fade)은 씬 끝.\n"
        "3) 배경 레이어에는 모션을 주지 않는다.\n"
        "4) 모든 start+duration은 씬 길이 이내.\n"
        "5) camera는 씬 분위기에 맞게 none/slow_zoom_in/slow_zoom_out/pan_left/pan_right 중 선택."
    )
```

(c) 결정적 필터를 바꾼다. 기존:

```python
    valid = set(chars)
    allowed = {"bob", "fade_in"}
    filtered = []
    for L in plan.get("layers", []):
        if L.get("layer") not in valid:
            continue
        mvs = [m for m in L.get("moves", []) if m.get("type") in allowed]
        if mvs:
            filtered.append({"layer": L["layer"], "moves": mvs})
    plan["layers"] = filtered
```

교체:

```python
    plan = filter_plan_moves(plan, kind_map)
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `python3 -m pytest tests/test_motion_kinds.py -v && python3 -m pytest tests/ -q`
Expected: 신규 10건 PASS, 전체 통과. `plan_scene_motion`의 옛 동작("캐릭터만",
`bob/fade_in`)을 단언하던 기존 테스트가 있으면 새 규칙을 단언하도록 갱신한다 —
검증을 약화시키지 않는다.

- [ ] **Step 7: 커밋한다**

```bash
git add backend/motion.py backend/schemas/motion_plan.schema.json tests/test_motion_kinds.py
git commit -m "feat(motion): 레이어 종류별 프리셋 개방 + stamp/wiggle enum"
```

---

### Task 2: jsx `stamp`·`wiggle` + 출처 자막

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/build_scene.jsx` (`applyMoves`의 분기, `buildSceneGroup`)
- Modify: `backend/manifest.py` (`build_manifest`의 `out_scenes.append`)
- Test: `tests/test_semoji_jsx.py` (신규), `tests/test_manifest_flat.py`(추가)

**Interfaces:**
- Consumes: 매니페스트 씬 엔트리(Task 1과 무관), `buildSceneGroup`의 지역 변수 `pf`·`t0`·`t1`·`guide`, `TK.colors`·`TK.fonts`·`TK.type`
- Produces: 매니페스트 씬 엔트리에 `source`(str, 비어 있지 않을 때만), jsx `addSourceCaption(comp, s, W, H)` 함수

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_semoji_jsx.py`를 만든다.

```python
from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
JSX = PANEL / "jsx" / "build_scene.jsx"


def _src():
    return JSX.read_text(encoding="utf-8")


def test_stamp_branch():
    src = _src()
    assert 'mv.type === "stamp"' in src
    # 5프레임 내리찍기 — 스케일 시작 배율은 amount(기본 300)
    assert "300" in src


def test_wiggle_branch():
    src = _src()
    assert 'mv.type === "wiggle"' in src
    assert "wiggle(" in src


def test_source_caption_function():
    src = _src()
    assert "function addSourceCaption" in src
    assert '"출처"' in src and '"출처판"' in src


def test_source_caption_not_parented_to_guide():
    """출처 자막은 카메라 줌에 딸려가면 안 된다 — 가이드 미페어런팅.
    addSourceCaption 함수 본문에 guide/parent 참조가 없어야 한다."""
    src = _src()
    body = src.split("function addSourceCaption")[1].split("\n    function ")[0]
    assert "parent = guide" not in body
    assert ".parent =" not in body or "textL.parent = plate" in body


def test_source_caption_called_in_build():
    src = _src()
    assert "addSourceCaption(comp, s" in src


def test_es5_only():
    src = _src()
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src
```

`tests/test_manifest_flat.py` 끝에 붙인다.

```python
def test_source_field_passed(tmp_path):
    proj = _project(tmp_path)
    data = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
    data["scenes"][0]["source"] = "자료: 국토부 2025"
    data["scenes"][1]["source"] = "   "          # 공백뿐 — 실리면 안 된다
    (proj / "scenes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    assert mf["scenes"][0]["source"] == "자료: 국토부 2025"
    assert "source" not in mf["scenes"][1]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python3 -m pytest tests/test_semoji_jsx.py tests/test_manifest_flat.py -v`
Expected: FAIL — stamp/wiggle 분기·`addSourceCaption`·`source` 필드가 없다.

- [ ] **Step 3: 매니페스트에 `source`를 싣는다**

`backend/manifest.py`의 `out_scenes.append({...})` 안, `"prefix": prefix,` 다음에 넣는다.

```python
            **({"source": str(s.get("source")).strip()}
               if s.get("source") and str(s.get("source")).strip() else {}),
```

- [ ] **Step 4: jsx에 stamp·wiggle 분기를 넣는다**

`applyMoves`의 `shake` 분기 다음(`} else if (mv.type === "shake") { ... }` 뒤)에 넣는다.

```javascript
                } else if (mv.type === "stamp") {
                    // 도장 — 크게서 제 크기로 5프레임 내리찍기. SEMOJI 도장효과의 타격부.
                    // 잔상 복제본은 결정적 재빌드와 충돌해 생략(설계 문서 결정 2).
                    var m0 = (amt && amt > 100) ? amt : 300;
                    var hit = t0 + 5 / 30.0;
                    var sst = il.property("Scale");
                    sst.setValueAtTime(t0, [S[0] * m0 / 100, S[1] * m0 / 100]);
                    sst.setValueAtTime(hit, [S[0], S[1]]);
                    var ost = il.property("Opacity");
                    ost.setValueAtTime(t0, 0);
                    ost.setValueAtTime(hit, 100);
                    try {
                        var ezs = new KeyframeEase(0, 33.34);
                        sst.setTemporalEaseAtKey(sst.nearestKeyIndex(hit), [ezs, ezs], [ezs, ezs]);
                    } catch (eSt) { }
                } else if (mv.type === "wiggle") {
                    // 위글 — 익스프레션이라 레이어 수명 전체에 걸린다(구간 제어는 범위 밖).
                    var wa = amt || 8;
                    try { il.property("Position").expression = "wiggle(1, " + wa + ")"; } catch (eWg) { }
```

- [ ] **Step 5: 출처 자막 함수를 넣는다**

`buildSceneGroup` 함수 **앞**에 넣는다.

```javascript
    // 출처 자막 — 우하단 검정 판(60%) + 흰 텍스트. SEMOJI 출처자막 구조.
    // 판 폭은 텍스트 폭 + 50px을 따라간다(익스프레션). 가이드에 페어런팅하지 않는다 —
    // 카메라 줌이 출처 표기까지 키우면 안 된다. 접두사 덕에 재빌드 시 함께 지워진다.
    function addSourceCaption(comp, s, W, H) {
        var pf = s.prefix || "S00_";
        var t0 = s.start || 0;
        var t1 = t0 + (s.duration || 5);
        var mx = W * 0.03;                                // 우측 여백 3%

        var plate = comp.layers.addShape();
        plate.name = pf + "출처판";
        var grp = plate.property("Contents").addProperty("ADBE Vector Group");
        var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
        var fillP = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fillP.property("Color").setValue([0, 0, 0]);
        plate.property("Opacity").setValue(60);
        plate.inPoint = t0; plate.outPoint = t1;

        var textL = comp.layers.addText(String(s.source));
        textL.name = pf + "출처";
        var tp = textL.property("Source Text");
        var doc = tp.value;
        doc.fontSize = 24;
        doc.fillColor = [1, 1, 1];
        try { if (TK.fonts && TK.fonts.subtitle) { doc.font = TK.fonts.subtitle; } } catch (eF) { }
        try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (eJ) { }
        tp.setValue(doc);
        textL.inPoint = t0; textL.outPoint = t1;

        // 판 크기 — 텍스트 폭을 따라가는 익스프레션(SEMOJI 그대로)
        try {
            rect.property("Size").expression =
                'var t = thisComp.layer("' + textL.name + '");\n' +
                'var w = t.sourceRectAtTime(time, false).width;\n' +
                '[w + 50, 50]';
        } catch (eX) { }

        // 텍스트 앵커 중앙 → 판 중앙과 겹치게 우하단 배치
        try {
            var tb = textL.sourceRectAtTime(t0, false);
            textL.property("Anchor Point").setValue([tb.left + tb.width / 2, tb.top + tb.height / 2]);
        } catch (eA) { }
        var px = W - mx;                                   // 판 중심 x — 우측 여백만큼 안쪽
        var py = H - mx;
        plate.property("Position").setValue([px, py]);
        textL.property("Position").setValue([px, py]);
        textL.parent = plate;                              // 판이 움직이면 텍스트가 따라간다
        return plate;
    }
```

- [ ] **Step 6: `buildSceneGroup`에서 부른다**

`buildSceneGroup` 안, 오디오 처리 **앞**에 넣는다.

```javascript
        if (s.source) {
            try { addSourceCaption(comp, s, W, H); }
            catch (eSrc) { log.push(pf + "출처 자막 실패 " + eSrc.toString()); }
        }
```

- [ ] **Step 7: 검증한다**

Run: `python3 -m pytest tests/test_semoji_jsx.py tests/test_manifest_flat.py -v && python3 -m pytest tests/ -q`
Expected: 모두 PASS

Run: `grep -nE "=>|\blet\b|\bconst\b" cep/com.autokairos.pd/jsx/build_scene.jsx`
Expected: 출력 없음

- [ ] **Step 8: 커밋한다**

```bash
git add cep/com.autokairos.pd/jsx/build_scene.jsx backend/manifest.py tests/test_semoji_jsx.py tests/test_manifest_flat.py
git commit -m "feat(jsx): stamp/wiggle 프리셋 + 출처 자막 렌더"
```

---

### Task 3: SRT 파서와 엔드포인트

**Files:**
- Create: `backend/srt.py`
- Modify: `backend/router.py` (`POST /api/tools/srt-parse` 추가, import에 `srt`)
- Test: `tests/test_srt.py` (신규)

**Interfaces:**
- Consumes: `router.handle_request` 관례(`(status, dict)` 반환)
- Produces: `srt.parse_srt(text: str) -> list` — `[{"start": float, "end": float, "text": str}]`, `POST /api/tools/srt-parse` 본문 `{"srt": str}` → 200 `{"cues": [...]}` 또는 422 `{"error"}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_srt.py`를 만든다.

```python
from backend import srt

BASIC = """1
00:00:01,000 --> 00:00:03,500
첫 자막

2
00:00:04,000 --> 00:00:06,000
둘째 자막
"""


def test_two_cues():
    cues = srt.parse_srt(BASIC)
    assert len(cues) == 2
    assert cues[0] == {"start": 1.0, "end": 3.5, "text": "첫 자막"}
    assert cues[1]["start"] == 4.0


def test_last_cue_has_real_end():
    """SEMOJI 결함 수정 — 마지막 큐 길이가 0이 아니다."""
    cues = srt.parse_srt(BASIC)
    assert cues[-1]["end"] == 6.0
    assert cues[-1]["end"] > cues[-1]["start"]


def test_dot_millis_accepted():
    cues = srt.parse_srt("1\n00:00:01.250 --> 00:00:02.750\n마침표\n")
    assert cues[0]["start"] == 1.25 and cues[0]["end"] == 2.75


def test_multiline_text_joined():
    cues = srt.parse_srt("1\n00:00:01,000 --> 00:00:02,000\n윗줄\n아랫줄\n")
    assert cues[0]["text"] == "윗줄\n아랫줄"


def test_broken_block_skipped():
    text = BASIC + "\nX\n망가진 타임코드\n텍스트\n\n3\n00:00:07,000 --> 00:00:08,000\n셋째\n"
    cues = srt.parse_srt(text)
    assert [c["text"] for c in cues] == ["첫 자막", "둘째 자막", "셋째"]


def test_no_index_line_ok():
    cues = srt.parse_srt("00:00:01,000 --> 00:00:02,000\n번호 없음\n")
    assert cues[0]["text"] == "번호 없음"


def test_bom_and_crlf():
    text = "﻿1\r\n00:00:01,000 --> 00:00:02,000\r\n윈도 파일\r\n"
    cues = srt.parse_srt(text)
    assert cues[0]["text"] == "윈도 파일"


def test_end_before_start_skipped():
    cues = srt.parse_srt("1\n00:00:05,000 --> 00:00:04,000\n역행\n")
    assert cues == []


def test_empty_input():
    assert srt.parse_srt("") == []
    assert srt.parse_srt("   \n\n") == []


def test_endpoint_ok(tmp_path):
    from backend import jobs as jobs_mod
    from backend import router
    status, res = router.handle_request(
        "POST", "/api/tools/srt-parse", {}, {"srt": BASIC},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 200
    assert len(res["cues"]) == 2


def test_endpoint_no_cues(tmp_path):
    from backend import jobs as jobs_mod
    from backend import router
    status, res = router.handle_request(
        "POST", "/api/tools/srt-parse", {}, {"srt": "쓸모없는 내용"},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 422
    assert "error" in res
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python3 -m pytest tests/test_srt.py -v`
Expected: FAIL — `backend.srt`가 없다.

- [ ] **Step 3: `backend/srt.py`를 만든다**

```python
"""SRT 자막 파싱 — 패널 도구의 'SRT 가져오기'용.

SEMOJI TOOL의 파서는 시작 타임코드만 읽어 마지막 자막 길이가 0이 되는 결함이
있었다. 여기서는 종료 타임코드를 읽어 각 큐가 자기 종료 시각을 갖는다.
깨진 블록은 건너뛰고 나머지를 살린다.
"""
from __future__ import annotations

import re

_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


def _sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(text: str) -> list:
    """[{"start": float, "end": float, "text": str}] — 시작 시각 오름차순.

    번호 줄은 있어도 없어도 된다. end <= start 인 블록은 버린다."""
    if not text:
        return []
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        ti = None
        for i, ln in enumerate(lines):
            m = _TIME.search(ln)
            if m:
                ti = (i, m)
                break
        if ti is None:
            continue
        i, m = ti
        start = _sec(m.group(1), m.group(2), m.group(3), m.group(4))
        end = _sec(m.group(5), m.group(6), m.group(7), m.group(8))
        body = "\n".join(lines[i + 1:]).strip()
        if not body or end <= start:
            continue
        cues.append({"start": start, "end": end, "text": body})
    cues.sort(key=lambda c: c["start"])
    return cues
```

- [ ] **Step 4: 엔드포인트를 추가한다**

`backend/router.py` 상단 import에 `srt`를 더하고, `/api/layers/vectorize` 블록
다음에 넣는다.

```python
    if method == "POST" and p == "/api/tools/srt-parse":
        b = body or {}
        cues = srt.parse_srt(b.get("srt") or "")
        if not cues:
            return 422, {"error": "유효한 자막 큐 없음"}
        return 200, {"cues": cues}
```

- [ ] **Step 5: 검증한다**

Run: `python3 -m pytest tests/test_srt.py -v && python3 -m pytest tests/ -q`
Expected: 신규 11건 PASS, 전체 통과.

- [ ] **Step 6: 커밋한다**

```bash
git add backend/srt.py backend/router.py tests/test_srt.py
git commit -m "feat(tools): SRT 파서 + /api/tools/srt-parse (마지막 큐 길이 0 결함 수정)"
```

---

### Task 4: 도구 구역 UI + `tools.jsx`

**Files:**
- Create: `cep/com.autokairos.pd/jsx/tools.jsx`
- Modify: `cep/com.autokairos.pd/index.html` (도구 구역 마크업)
- Modify: `cep/com.autokairos.pd/js/storyboard.js` (바인딩·호출)
- Test: `tests/test_semoji_jsx.py` (Task 2 파일에 추가)

**Interfaces:**
- Consumes: `POST /api/tools/srt-parse`(Task 3), 패널 헬퍼 `readLocal(path)`·`evalScript(code)`·`$(id)`, `BACKEND`, 매니페스트가 쓰는 토큰 파일 경로는 jsx 인자로 받음
- Produces: jsx 전역 함수 `akImportSrt(cuesJson, tokensPath)`, `akInsertNull()`, `akApplyPreset(type, amount)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_semoji_jsx.py` 끝에 붙인다.

```python
TOOLS = PANEL / "jsx" / "tools.jsx"


def test_tools_jsx_exists_and_functions():
    src = TOOLS.read_text(encoding="utf-8")
    for fn in ("function akImportSrt", "function akInsertNull", "function akApplyPreset"):
        assert fn in src


def test_tools_srt_single_text_layer():
    """SRT도 1레이어 + Source Text 키프레임 — 줄별 레이어 금지(577레이어 사태의 교훈)."""
    src = TOOLS.read_text(encoding="utf-8")
    assert '"가져온자막"' in src
    assert "setValueAtTime" in src
    # 큐마다 addText를 부르는 구조가 아니어야 한다
    assert src.count("layers.addText") == 1


def test_tools_insert_null_preserves_parent():
    src = TOOLS.read_text(encoding="utf-8")
    body = src.split("function akInsertNull")[1].split("\nfunction ")[0]
    assert "parent" in body and "addNull" in body and "moveAfter" in body


def test_tools_es5_only():
    src = TOOLS.read_text(encoding="utf-8")
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src


def test_panel_tools_section():
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'id="toolsSection"' in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "akImportSrt" in js and "akInsertNull" in js and "akApplyPreset" in js
    assert "/api/tools/srt-parse" in js
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python3 -m pytest tests/test_semoji_jsx.py -v`
Expected: FAIL — `tools.jsx`와 도구 구역이 없다.

- [ ] **Step 3: `tools.jsx`를 만든다**

`cep/com.autokairos.pd/jsx/tools.jsx`:

```javascript
// auto_kairos — 패널 '도구' 구역의 AE 보조 기능. 빌드 파이프라인과 무관하게
// 현재 AE 상태(선택 레이어·Final 컴프)에 작용한다. SEMOJI TOOL 1.57 이식.
// json2.jsx와 함께 로드된다(패널이 이어붙여 evalScript).

var AK_SRT_LAYER = "가져온자막";

function akToolsFindComp(name) {
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === name) { return it; }
    }
    return null;
}

// SRT 큐를 Final의 텍스트 레이어 1장에 Source Text 키프레임으로 넣는다.
// 줄별 레이어를 만들지 않는다 — 수백 줄이어도 레이어는 1개(말자막과 같은 방식).
function akImportSrt(cuesJson, tokensPath) {
    try {
        var cues = (typeof JSON === "object" && JSON.parse) ? JSON.parse(cuesJson) : eval("(" + cuesJson + ")");
        if (!cues || !cues.length) { return "ERROR: 넣을 자막이 없습니다"; }
        var comp = akToolsFindComp("Final");
        if (!comp) { return "ERROR: Final 컴프 없음 — 먼저 컴프를 빌드하세요"; }

        var size = 54, fontName = "";
        try {
            if (tokensPath) {
                var tf = new File(tokensPath);
                if (tf.exists) {
                    tf.open("r"); var raw = tf.read(); tf.close();
                    var tk = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
                    if (tk.type && tk.type.subtitle) { size = tk.type.subtitle; }
                    if (tk.fonts && tk.fonts.subtitle) { fontName = tk.fonts.subtitle; }
                }
            }
        } catch (eTk) { }

        app.beginUndoGroup("auto_kairos SRT 가져오기");
        for (var i = comp.numLayers; i >= 1; i--) {          // 같은 이름은 지우고 다시
            if (comp.layer(i).name === AK_SRT_LAYER) { comp.layer(i).remove(); }
        }
        var tl = comp.layers.addText("");
        tl.name = AK_SRT_LAYER;
        var prop = tl.property("Source Text");
        var doc = prop.value;
        doc.fontSize = size;
        doc.fillColor = [1, 1, 1];
        try { doc.applyStroke = true; doc.strokeColor = [0, 0, 0]; doc.strokeWidth = Math.max(4, size / 12); doc.strokeOverFill = false; } catch (e2) { }
        try { if (fontName) { doc.font = fontName; } } catch (e3) { }
        try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e4) { }
        tl.property("Anchor Point").setValue([0, 0]);
        tl.property("Position").setValue([comp.width / 2, comp.height * 0.86]);   // 말자막(0.92)보다 한 줄 위

        var made = 0, maxEnd = 0;
        for (var q = 0; q < cues.length; q++) {
            var c = cues[q];
            if (!c.text || c.start == null || c.end == null) { continue; }
            doc.text = String(c.text);
            prop.setValueAtTime(c.start, doc);
            made++;
            var nextStart = (q + 1 < cues.length) ? cues[q + 1].start : null;
            if (nextStart === null || nextStart > c.end + 0.02) {
                doc.text = "";
                prop.setValueAtTime(c.end, doc);
            }
            if (c.end > maxEnd) { maxEnd = c.end; }
        }
        if (maxEnd > comp.duration) { comp.duration = maxEnd; }
        tl.startTime = 0; tl.inPoint = 0; tl.outPoint = comp.duration;
        app.endUndoGroup();
        return "OK: 자막 " + made + "줄 → 레이어 1개(" + AK_SRT_LAYER + ")";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}

// 선택 레이어와 그 부모 사이에 널을 끼운다 — 계층 보존. SEMOJI NULL추가 이식.
function akInsertNull() {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        app.beginUndoGroup("auto_kairos 널 끼우기");
        var lay = sel[0];
        var prevParent = lay.parent;
        lay.parent = null;
        var pos = lay.property("Position").value;
        var nl = comp.layers.addNull();
        nl.name = lay.name + "_널";
        nl.property("Position").setValue(pos);
        nl.moveAfter(lay);
        lay.parent = nl;
        if (prevParent) { nl.parent = prevParent; }
        app.endUndoGroup();
        return "OK: " + nl.name;
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}

// 선택 레이어들에 프리셋을 건다 — 시작은 각 레이어의 inPoint, 기준값은 현재 값.
// 매니페스트 좌표·씬 시각이 없는 수동 단순판이라 build_scene.jsx의 applyMoves와 별개다.
function akApplyPreset(type, amount) {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        var amt = (amount != null && amount !== "") ? parseFloat(amount) : null;
        app.beginUndoGroup("auto_kairos 프리셋: " + type);
        var done = 0;
        for (var i = 0; i < sel.length; i++) {
            var il = sel[i];
            var t0 = il.inPoint;
            var P = il.property("Position").value;
            var S = il.property("Scale").value;
            try {
                if (type === "slide_in") {
                    var off = amt || comp.width * 0.18;
                    var pp = il.property("Position");
                    pp.setValueAtTime(t0, [P[0] - off, P[1]]);
                    pp.setValueAtTime(t0 + 0.5, [P[0], P[1]]);
                } else if (type === "fade_in") {
                    var op = il.property("Opacity");
                    op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + 0.5, 100);
                } else if (type === "exit_fade") {
                    var oe = il.property("Opacity");
                    oe.setValueAtTime(il.outPoint - 0.5, 100); oe.setValueAtTime(il.outPoint, 0);
                } else if (type === "pop") {
                    var sp = il.property("Scale");
                    sp.setValueAtTime(t0, [S[0] * 0.6, S[1] * 0.6]);
                    sp.setValueAtTime(t0 + 0.35, [S[0] * 1.06, S[1] * 1.06]);
                    sp.setValueAtTime(t0 + 0.5, [S[0], S[1]]);
                } else if (type === "zoom_emphasis") {
                    var sz = il.property("Scale");
                    sz.setValueAtTime(t0, [S[0], S[1]]);
                    sz.setValueAtTime(t0 + 0.4, [S[0] * 1.08, S[1] * 1.08]);
                    sz.setValueAtTime(t0 + 0.8, [S[0], S[1]]);
                } else if (type === "drift") {
                    var dd = amt || 18;
                    var pd = il.property("Position");
                    pd.setValueAtTime(t0, [P[0], P[1]]);
                    pd.setValueAtTime(il.outPoint, [P[0] + dd, P[1] - dd * 0.4]);
                } else if (type === "shake") {
                    var sa = amt || 10, ps = il.property("Position");
                    for (var si = 0; si <= 6; si++) {
                        var ts = t0 + 0.8 * si / 6;
                        ps.setValueAtTime(ts, [P[0] + ((si % 2) ? sa : -sa) * (1 - si / 6), P[1]]);
                    }
                } else if (type === "stamp") {
                    var m0 = (amt && amt > 100) ? amt : 300;
                    var hit = t0 + 5 / 30.0;
                    var st = il.property("Scale");
                    st.setValueAtTime(t0, [S[0] * m0 / 100, S[1] * m0 / 100]);
                    st.setValueAtTime(hit, [S[0], S[1]]);
                    var ot = il.property("Opacity");
                    ot.setValueAtTime(t0, 0); ot.setValueAtTime(hit, 100);
                } else if (type === "wiggle") {
                    var wa = amt || 8;
                    il.property("Position").expression = "wiggle(1, " + wa + ")";
                } else {
                    continue;
                }
                done++;
            } catch (eOne) { }
        }
        app.endUndoGroup();
        return "OK: " + done + "개 레이어에 " + type;
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}
```

- [ ] **Step 4: 패널 도구 구역을 만든다**

`cep/com.autokairos.pd/index.html`에서 시트 갤러리 아래(적절한 하단 위치)에 넣는다.

```html
    <details id="toolsSection">
      <summary>도구 — AE 보조 기능</summary>
      <div class="tools-body">
        <div class="tools-row">
          <label class="mini-label">SRT 가져오기</label>
          <input type="file" id="srtFile" accept=".srt">
          <button class="mini" id="srtImportBtn">Final에 넣기</button>
        </div>
        <div class="tools-row">
          <label class="mini-label">널 끼우기</label>
          <button class="mini" id="insertNullBtn" title="선택한 레이어와 부모 사이에 널을 끼웁니다">선택 레이어에</button>
        </div>
        <div class="tools-row">
          <label class="mini-label">프리셋 적용</label>
          <select id="presetSelect">
            <option value="slide_in">slide_in — 밀어 등장</option>
            <option value="fade_in">fade_in — 서서히</option>
            <option value="pop">pop — 통통 등장</option>
            <option value="stamp">stamp — 도장</option>
            <option value="zoom_emphasis">zoom_emphasis — 강조</option>
            <option value="shake">shake — 흔들림</option>
            <option value="wiggle">wiggle — 위글</option>
            <option value="drift">drift — 떠다님</option>
            <option value="exit_fade">exit_fade — 퇴장</option>
          </select>
          <input type="text" id="presetAmt" placeholder="진폭(선택)" style="width:70px">
          <button class="mini" id="presetApplyBtn" title="AE에서 선택한 레이어에 겁니다">선택 레이어에</button>
        </div>
        <div id="toolsStatus" class="tools-status"></div>
      </div>
    </details>
```

CSS(같은 파일의 `<style>` 안):

```css
    #toolsSection { margin-top:10px; border-top:1px solid #333; padding-top:6px; }
    #toolsSection summary { cursor:pointer; font-size:12px; color:#aaa; }
    .tools-body { padding:6px 0; }
    .tools-row { display:flex; align-items:center; gap:6px; margin:4px 0; }
    .tools-row .mini-label { font-size:11px; color:#888; width:90px; }
    .tools-status { font-size:11px; color:#8a8; min-height:14px; }
```

- [ ] **Step 5: 패널 바인딩을 넣는다**

`cep/com.autokairos.pd/js/storyboard.js` 끝(초기화 함수들 근처)에 넣고, 기존 초기화
경로에서 `bindTools()`를 한 번 부른다. 모두 순수 ES5.

```javascript
/* ===== 도구 구역 — AE 보조 기능(tools.jsx) ===== */
function _toolsSay(m) { var e = $("toolsStatus"); if (e) e.textContent = m; }

function _runTool(call) {
  var jsx;
  try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/tools.jsx"); }
  catch (e) { _toolsSay("jsx 로드 실패: " + e); return; }
  return evalScript(jsx + "\n" + call).then(function (r) { _toolsSay(r || "(빈 응답)"); });
}

function importSrtFile() {
  var inp = $("srtFile");
  if (!inp || !inp.files || !inp.files.length) { _toolsSay("SRT 파일을 고르세요"); return; }
  var reader = new FileReader();
  reader.onload = function () {
    _toolsSay("파싱 중...");
    fetch(BACKEND + "/api/tools/srt-parse", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ srt: String(reader.result || "") }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.cues || !j.cues.length) { _toolsSay("실패: " + (j.error || "큐 없음")); return; }
        _toolsSay("AE에 넣는 중... (" + j.cues.length + "줄)");
        var tokens = "";   // 토큰 경로는 빌드와 동일 파일 — 없으면 기본 스타일
        _runTool("akImportSrt(" + JSON.stringify(JSON.stringify(j.cues)) + ", " + JSON.stringify(tokens) + ");");
      })
      .catch(function (e) { _toolsSay("오류: " + e); });
  };
  reader.readAsText(inp.files[0]);
}

function bindTools() {
  var b1 = $("srtImportBtn");
  if (b1) b1.addEventListener("click", importSrtFile);
  var b2 = $("insertNullBtn");
  if (b2) b2.addEventListener("click", function () { _runTool("akInsertNull();"); });
  var b3 = $("presetApplyBtn");
  if (b3) b3.addEventListener("click", function () {
    var t = $("presetSelect").value;
    var a = $("presetAmt").value;
    _runTool("akApplyPreset(" + JSON.stringify(t) + ", " + JSON.stringify(a) + ");");
  });
}
```

기존 초기화 위치를 찾아(`grep -n "addEventListener(\"DOMContentLoaded\"\|function init" cep/com.autokairos.pd/js/*.js`) 거기서 `bindTools();`를 부른다. 마땅한 곳이
없으면 `storyboard.js` 최하단에 즉시 호출을 넣는다(다른 전역 바인딩과 같은 방식).

- [ ] **Step 6: 검증한다**

Run: `python3 -m pytest tests/test_semoji_jsx.py -v && python3 -m pytest tests/ -q`
Expected: 모두 PASS

Run: `node --check cep/com.autokairos.pd/js/storyboard.js && grep -nE "=>|\blet\b|\bconst\b" cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/jsx/tools.jsx`
Expected: 출력 없음

- [ ] **Step 7: 커밋한다**

```bash
git add cep/com.autokairos.pd/jsx/tools.jsx cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/storyboard.js tests/test_semoji_jsx.py
git commit -m "feat(panel): 도구 구역 — SRT 가져오기·널 끼우기·프리셋 수동 적용"
```

---

## 사람이 확인해야 하는 것

이 맥에 After Effects가 없어 자동 검증이 안 된다. 테스터 PC에서 확인한다.

1. **stamp의 타격감** — 5프레임 내리찍기가 도장처럼 보이는지, 진폭 300%가 적절한지.
2. **wiggle 진폭** — 기본 8px이 과하지 않은지.
3. **출처 자막** — 우하단 위치·판 폭 익스프레션이 텍스트를 따라가는지, 카메라 줌에 안 딸려가는지.
4. **SRT 가져오기** — 키프레임 타이밍, `말자막`(0.92)과 `가져온자막`(0.86)의 겹침.
5. **널 끼우기·프리셋 수동 적용** — 선택 레이어에서의 실동작.
6. **LLM 사물 모션의 품질** — 프롬프트가 "기본은 모션 없음"을 지키는지, 과한 플랜이 나오면 프롬프트 조정.
