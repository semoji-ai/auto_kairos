# 통합 모션 라이브러리 P1 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gemini→JSON→AE 빌더의 모션을 명명된 라이브러리(7 프리셋 + 디테일 + 폰트/컬러)로 만들어, gemini가 프리셋명으로 매핑하고 빌더가 정교한 키프레임/이징/이펙트로 적용한다.

**Architecture:** `data/artstyle/motion/`의 JSON 3종이 공유 어휘. `build_from_json.jsx`가 이를 로드해 `applyPreset`(7 프리셋 → 키프레임+이징), `applyDetail`(shadow/glow/blur/grain), `resolveFont/resolveColor`로 적용. 기존 prop 방식과 하위호환.

**Tech Stack:** ExtendScript(AE jsx), JSON, Python(pytest — JSON 스키마/jsx 구문 검증), google-genai(gemini 프롬프트).

---

## 파일 구조

- Create: `data/artstyle/motion/motion_presets.json` — 7 프리셋 정의
- Create: `data/artstyle/motion/font_map.json` — 역할→PS폰트
- Create: `data/artstyle/motion/color_tokens.json` — 키→hex
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx` — loadMotionLib/applyPreset/applyDetail/resolveFont/resolveColor + dispatch
- Modify: `/tmp/tyl_gemini_comp2.py`(또는 새 스크립트) — gemini 프롬프트에 라이브러리 어휘 주입
- Test: `tests/test_motion_library.py`(생성), `tests/test_panel_structure.py`(추가)

테스트 실행: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`

---

## Task 1: 라이브러리 JSON 3종

**Files:**
- Create: `data/artstyle/motion/motion_presets.json`, `font_map.json`, `color_tokens.json`
- Test: `tests/test_motion_library.py`

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_motion_library.py`:
```python
import json
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "motion"


def test_motion_presets_schema():
    """7 프리셋 + 각 props/ease 필드."""
    d = json.loads((LIB / "motion_presets.json").read_text(encoding="utf-8"))
    presets = d["presets"]
    expected = {"type_on", "fade_scale_in", "slide_in", "pop_bounce", "mask_reveal", "tilt_2_5d", "stagger"}
    assert set(presets.keys()) == expected
    for name, p in presets.items():
        assert "props" in p or name == "stagger"   # stagger는 메타(base 계승)


def test_font_map():
    d = json.loads((LIB / "font_map.json").read_text(encoding="utf-8"))
    assert d["gothic_bold"] == "OTSBAggroB"
    assert d["serif"] == "GyeonggiBatangR" and d["rounded"] == "Cafe24Ssurround"


def test_color_tokens():
    d = json.loads((LIB / "color_tokens.json").read_text(encoding="utf-8"))
    assert d["brand_red"].upper() == "#E4002B" and d["ink"].upper() == "#333333"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_motion_library.py -v` → FAIL(파일 없음)

- [ ] **Step 3: JSON 생성** — `data/artstyle/motion/motion_presets.json`:
```json
{
  "presets": {
    "type_on":        {"props": ["textOffset"], "ease": "linear", "params": {"cps": 14}},
    "fade_scale_in":  {"props": ["opacity", "scale"], "ease": "easeOut", "params": {"scaleFrom": 85}},
    "slide_in":       {"props": ["position", "opacity"], "ease": "easeOut", "params": {"dir": "left", "offset": 80}},
    "pop_bounce":     {"props": ["scale", "opacity"], "ease": "overshoot", "params": {"overshoot": 110, "settle": 6}},
    "mask_reveal":    {"props": ["trimEnd"], "ease": "easeInOut", "params": {"mode": "trim", "dir": "left"}},
    "tilt_2_5d":      {"props": ["rotationY"], "ease": "easeOut", "params": {"angle": -15}},
    "stagger":        {"meta": true, "params": {"base": "fade_scale_in", "offset": 5, "dir": "forward"}}
  }
}
```
`font_map.json`:
```json
{
  "gothic_bold": "OTSBAggroB", "gothic_med": "OTSBAggroM", "gothic_light": "OTSBAggroL",
  "serif": "GyeonggiBatangR", "rounded": "Cafe24Ssurround", "sans": "Pretendard-Regular",
  "fallback": "AppleSDGothicNeo-Bold"
}
```
`color_tokens.json`:
```json
{
  "brand_red": "#E4002B", "ink": "#333333", "bg_gray": "#F3F3F3",
  "white": "#FFFFFF", "muted": "#9AA0A6", "purple": "#7F58E7"
}
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_motion_library.py -v` → 3 PASS

- [ ] **Step 5: 커밋**
```bash
git add data/artstyle/motion/ tests/test_motion_library.py
git commit -m "feat(motion): 라이브러리 JSON 3종 — 7 프리셋/폰트맵/컬러토큰

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 빌더 — 라이브러리 로드 + resolveFont/resolveColor

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패 테스트** — `tests/test_panel_structure.py` 끝에 추가:
```python
def test_builder_loads_motion_lib():
    """빌더가 motion_presets/font_map/color_tokens 로드 + resolve 함수."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "motion_presets.json" in jsx and "font_map.json" in jsx and "color_tokens.json" in jsx
    assert "function resolveFont" in jsx and "function resolveColor" in jsx
```
(PANEL은 test_panel_structure.py 상단에 정의됨)

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_panel_structure.py::test_builder_loads_motion_lib -v` → FAIL

- [ ] **Step 3: 빌더 수정** — `build_from_json.jsx`의 `var here = new File($.fileName).parent;` 줄 **뒤**(D 로드 근처)에 라이브러리 로드 추가. 먼저 라이브러리 경로: jsx는 `cep/.../jsx/tylenol/`, 라이브러리는 `data/artstyle/motion/`. 상대경로로 `here.parent.parent.parent.parent` 계산이 불안정하므로, **라이브러리를 jsx 폴더에 복사**해두고 `here/motion_presets.json`에서 읽는다(빌더 단순화). Task 1에서 만든 3 JSON을 jsx 폴더로 복사하는 것은 Step 5 커밋 전에 수행.

`akBuildFromJson` 안, `var D = ...` 파싱 직후에 추가:
```javascript
        function loadJson(name) {
            var f = new File(here.fsName + "/" + name);
            if (!f.exists) return {};
            f.open("r"); var t = f.read(); f.close();
            try { return (typeof JSON === "object" && JSON.parse) ? JSON.parse(t) : eval("(" + t + ")"); }
            catch (e) { return {}; }
        }
        var PRESETS = (loadJson("motion_presets.json").presets) || {};
        var FONTMAP = loadJson("font_map.json");
        var COLORS = loadJson("color_tokens.json");
        function resolveFont(role) { return FONTMAP[role] || role || FONTMAP.fallback || "AppleSDGothicNeo-Bold"; }
        function resolveColor(key) {
            if (!key) return null;
            var v = (key.charAt(0) === "#") ? key : COLORS[key];
            return v ? hex(v) : null;
        }
```

- [ ] **Step 4: 라이브러리를 jsx 폴더에 복사 + 통과 확인**
```bash
cp data/artstyle/motion/*.json cep/com.autokairos.pd/jsx/tylenol/
```
Run: `... -m pytest tests/test_panel_structure.py::test_builder_loads_motion_lib -v` → PASS
Run: `node --check cep/com.autokairos.pd/js/storyboard.js` (무관 회귀 없음 확인용은 생략 가능 — jsx는 node 검사 불가, 괄호 균형으로):
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -c "s=open('cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx').read(); print('OK' if all(s.count(a)==s.count(b) for a,b in [('{','}'),('(',')'),('[',']')]) else 'X')"
```
Expected: OK

- [ ] **Step 5: 커밋**
```bash
git add cep/com.autokairos.pd/jsx/tylenol/ tests/test_panel_structure.py
git commit -m "feat(motion): 빌더 라이브러리 로드 + resolveFont/resolveColor

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(주의: jsx 폴더의 *.json은 gitignore 아님 — motion 라이브러리는 추적. assets/만 ignore)

---

## Task 3: 빌더 — applyPreset (7 프리셋)

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_builder_apply_preset():
    """applyPreset가 7 프리셋 분기 + 커스텀 이징."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "function applyPreset" in jsx
    for p in ("type_on", "fade_scale_in", "slide_in", "pop_bounce", "mask_reveal", "tilt_2_5d"):
        assert p in jsx, p
    assert "KeyframeEase" in jsx        # 커스텀 이징
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: applyPreset 추가** — `build_from_json.jsx`의 `function applyAnim` **앞**에 추가:
```javascript
        // 프리셋명 → AE 키프레임+이징. params는 프리셋 기본값 + 컷별 오버라이드 병합.
        function easeKeys(prop, dim, ease) {
            try {
                var inf = (ease === "linear") ? 0.1 : 75;
                var arr = []; for (var d = 0; d < dim; d++) arr.push(new KeyframeEase(0, inf));
                var n = prop.numKeys;
                if (ease === "easeOut" || ease === "overshoot") prop.setTemporalEaseAtKey(n, arr, arr);
                else if (ease === "easeInOut") { prop.setTemporalEaseAtKey(1, arr, arr); prop.setTemporalEaseAtKey(n, arr, arr); }
            } catch (e) {}
        }
        function applyPreset(layer, isText, presetName, t0, dur, params) {
            var P = PRESETS[presetName]; if (!P) return;
            var pr = {}; for (var k in (P.params || {})) pr[k] = P.params[k];
            for (var k2 in (params || {})) pr[k2] = params[k2];   // 컷별 오버라이드
            dur = dur || 0.6; t0 = t0 || 0;
            layer.motionBlur = true;
            try {
                if (presetName === "type_on" && isText) {
                    var an = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                    an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
                    var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
                    try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
                    var off = sel.property("ADBE Text Percent Offset");
                    off.setValueAtTime(t0, 0); off.setValueAtTime(t0 + dur, 100);
                } else if (presetName === "fade_scale_in") {
                    var sf = pr.scaleFrom || 85;
                    var op = layer.property("Opacity"); op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + dur * 0.6, 100);
                    var sc = layer.property("Scale"); sc.setValueAtTime(t0, [sf, sf]); sc.setValueAtTime(t0 + dur, [100, 100]); easeKeys(sc, 2, "easeOut");
                } else if (presetName === "slide_in") {
                    var dir = pr.dir || "left", off2 = pr.offset || 80, ps = layer.property("Position"), cur = ps.value;
                    var dx = dir === "left" ? -off2 : dir === "right" ? off2 : 0;
                    var dy = dir === "up" ? -off2 : dir === "down" ? off2 : 0;
                    ps.setValueAtTime(t0, [cur[0] + dx, cur[1] + dy]); ps.setValueAtTime(t0 + dur, [cur[0], cur[1]]); easeKeys(ps, 2, "easeOut");
                    var op2 = layer.property("Opacity"); op2.setValueAtTime(t0, 0); op2.setValueAtTime(t0 + dur * 0.4, 100);
                } else if (presetName === "pop_bounce") {
                    var ov = pr.overshoot || 110, sc2 = layer.property("Scale");
                    sc2.setValueAtTime(t0, [0, 0]); sc2.setValueAtTime(t0 + dur * 0.6, [ov, ov]); sc2.setValueAtTime(t0 + dur, [100, 100]);
                    try { sc2.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80)]); sc2.setTemporalEaseAtKey(3, [new KeyframeEase(0, 60), new KeyframeEase(0, 60)]); } catch (e) {}
                    var op3 = layer.property("Opacity"); op3.setValueAtTime(t0, 0); op3.setValueAtTime(t0 + dur * 0.2, 100);
                } else if (presetName === "mask_reveal") {
                    // 셰이프 레이어 Trim Paths End 0→100(선 그리기). 셰이프 아니면 opacity 폴백.
                    try {
                        var cont = layer.property("ADBE Root Vectors Group");
                        var trim = cont.addProperty("ADBE Vector Filter - Trim");
                        var te = trim.property("ADBE Vector Trim End");
                        te.setValueAtTime(t0, 0); te.setValueAtTime(t0 + dur, 100); easeKeys(te, 1, "easeInOut");
                    } catch (eM) {
                        var op4 = layer.property("Opacity"); op4.setValueAtTime(t0, 0); op4.setValueAtTime(t0 + dur, 100);
                    }
                } else if (presetName === "tilt_2_5d") {
                    layer.threeDLayer = true;
                    var ang = pr.angle || -15, ry = layer.property("ADBE Transform Group").property("ADBE Rotate Y");
                    ry.setValueAtTime(t0, 0); ry.setValueAtTime(t0 + dur, ang); easeKeys(ry, 1, "easeOut");
                }
            } catch (eP) {}
        }
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_panel_structure.py::test_builder_apply_preset -v` → PASS. 괄호 균형 OK.

- [ ] **Step 5: 커밋**
```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx tests/test_panel_structure.py
git commit -m "feat(motion): applyPreset 7종 — type_on/fade_scale_in/slide_in/pop_bounce/mask_reveal/tilt_2_5d

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 빌더 — applyDetail (디테일 레이어)

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_builder_apply_detail():
    """applyDetail — shadow/glow/grain 이펙트."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "function applyDetail" in jsx
    assert "ADBE Drop Shadow" in jsx and "ADBE Glo2" in jsx and "ADBE Add Grain" in jsx
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: applyDetail 추가** — `applyPreset` 뒤에 추가:
```javascript
        function applyDetail(layer, details) {
            if (!details || !details.length) return;
            for (var i = 0; i < details.length; i++) {
                var d = details[i];
                try {
                    if (d === "shadow") {
                        var ds = layer.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
                        ds.property("ADBE Drop Shadow-0002").setValue(60); ds.property("ADBE Drop Shadow-0004").setValue(20); ds.property("ADBE Drop Shadow-0005").setValue(50);
                    } else if (d === "glow") {
                        layer.property("ADBE Effect Parade").addProperty("ADBE Glo2");
                    } else if (d === "depth_blur") {
                        var gb = layer.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
                        gb.property("ADBE Gaussian Blur 2-0001").setValue(4);
                    } else if (d === "motion_blur") {
                        layer.motionBlur = true;
                    }
                } catch (e) {}
            }
        }
        // grain은 컷 전체에 조정 레이어로 — 컷 빌드 후 호출
        function addGrainAdjustment(comp) {
            try {
                var g = comp.layers.addSolid([1, 1, 1], "grain", comp.width, comp.height, 1.0);
                g.adjustmentLayer = true;
                try { var ag = g.property("ADBE Effect Parade").addProperty("ADBE Add Grain"); ag.property("ADBE AddGrain-0002").setValue(0.4); }
                catch (eA) { var nz = g.property("ADBE Effect Parade").addProperty("ADBE Noise2"); nz.property("ADBE Noise2-0001").setValue(6); g.property("Opacity").setValue(40); }
            } catch (e) {}
        }
```

- [ ] **Step 4: 통과 확인** → PASS. 괄호 균형 OK.

- [ ] **Step 5: 커밋**
```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx tests/test_panel_structure.py
git commit -m "feat(motion): applyDetail — shadow/glow/depth_blur/motion_blur + 컷 그레인 조정레이어

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 빌더 — preset/font/color/detail 라우팅 + 하위호환

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_builder_routes_preset_font_color():
    """anim.preset → applyPreset, layer.font → resolveFont, detail → applyDetail 라우팅 + 기존 prop 하위호환."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "applyPreset(" in jsx and "applyDetail(" in jsx
    assert "resolveFont(" in jsx and "resolveColor(" in jsx
    assert "an.preset" in jsx           # anim에 preset 있으면 applyPreset
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: applyAnim 라우팅 추가** — `applyAnim` 함수 맨 앞(루프 안 `var an = anims[a]` 다음)에 preset 분기 추가. 기존:
```javascript
            for (var a = 0; a < anims.length; a++) {
                var an = anims[a], t0 = an.t0 || 0, t1 = an.t1 == null ? t0 + 0.5 : an.t1;
```
교체:
```javascript
            for (var a = 0; a < anims.length; a++) {
                var an = anims[a], t0 = an.t0 || 0, t1 = an.t1 == null ? t0 + 0.5 : an.t1;
                if (an.preset) { applyPreset(layer, isText, an.preset, t0, (an.dur || (t1 - t0)), an.params); continue; }   // 프리셋 우선
```

`makeText`에서 폰트/색 resolve 적용. 기존:
```javascript
            td.fontSize = opt.size || 48; td.fillColor = opt.rgb;
```
이 부분은 makeText가 opt.rgb(이미 rgb)를 받음. dispatch에서 layer.font/layer.color를 resolve해 넘기도록, 컷 루프의 makeText 호출 전에 변환. 컷 루프 `else if (L.type === "text")` 처리부를 찾아 수정 — `makeText(comp, L)` 호출 전에:
```javascript
                    if (L.font) L._fontResolved = resolveFont(L.font);
                    var lc = resolveColor(L.color); if (lc) L.rgb = lc;
```
그리고 `makeText` 안 폰트 체인을 `L._fontResolved` 우선으로:
```javascript
            var ff = opt._fontResolved ? [opt._fontResolved, "AppleSDGothicNeo-Bold"] : ["OTSBAggroM", "Cafe24Ssurround", "AppleSDGothicNeo-Bold"];
```
(기존 `var ff = [...]` 줄 교체)

`detail` 적용 — 컷 루프에서 레이어 생성 후 `if (lay) applyAnim(...)` 다음에:
```javascript
                if (lay && L.detail) applyDetail(lay, L.detail);
```

컷 그레인 — 컷 루프 끝, `comps.push` 전에:
```javascript
            if (cut.grain) addGrainAdjustment(comp);
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_panel_structure.py -v` → 신규 통과 + 전체 회귀 없음(`... -m pytest -q`). 괄호 균형 OK.

- [ ] **Step 5: 커밋**
```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx tests/test_panel_structure.py
git commit -m "feat(motion): anim.preset/font/color/detail 라우팅 + 기존 prop 하위호환

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: gemini 프롬프트 — 라이브러리 어휘 주입

**Files:**
- Create: `scripts/tylenol_analyze.py` (gemini 재분석, 라이브러리 어휘 포함)
- Test: 없음(외부 API — 산출 JSON 스키마는 빌더가 하위호환 처리)

- [ ] **Step 1: 스크립트 작성** — `scripts/tylenol_analyze.py`:
```python
"""타이레놀 영상 → 라이브러리 어휘(프리셋/폰트/컬러/디테일)로 motion.json 생성.
업로드된 파일 재사용(files/tdz4a7uge0w2, 48h 만료 시 재업로드). 결과를 파일로 직접 저장(파이프 잘림 방지)."""
import sys, time, json
from pathlib import Path
from google import genai
from google.genai import errors, types

LIB = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "motion"
presets = list(json.loads((LIB / "motion_presets.json").read_text())["presets"].keys())
fonts = list(json.loads((LIB / "font_map.json").read_text()).keys())
colors = list(json.loads((LIB / "color_tokens.json").read_text()).keys())

client = genai.Client()
f = client.files.get(name="files/tdz4a7uge0w2")
PROMPT = f"""이 70초 광고를 AE 컴프로 생성할 JSON으로만 출력(순수 JSON).
모션은 아래 프리셋명만 사용: {presets}
폰트는 역할명만: {fonts}
컬러는 토큰키 또는 hex: {colors}
디테일(옵션): shadow, glow, depth_blur, motion_blur

컷 스키마:
- searchbar: {{"type":"searchbar","text":..,"redText":..,"start":..,"dur":..,"bg":"토큰키/hex"}}
- button: {{"type":"button","text":..,"start":..,"dur":..,"bg":..}}
- cut: {{"type":"cut","start":..,"dur":..,"bg":..,"grain":true,
    "layers":[{{"type":"text|rrect|line|image|live","text":..,"asset":..,"color":"토큰키/hex","font":"역할명","size":..,"x":..,"y":..,"w":..,"h":..,"align":..,"round":..,"detail":["shadow"],
      "anim":[{{"preset":"프리셋명","t0":..,"dur":..,"params":{{"dir":"left"}}}}]}}]}}
출력: {{"cuts":[...35컷...]}} 순수 JSON만."""
cfg = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000)
for attempt in range(6):
    for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]:
        try:
            resp = client.models.generate_content(model=m, contents=[f, PROMPT], config=cfg)
            data = json.loads(resp.text)
            out = Path(__file__).resolve().parents[1] / "cep/com.autokairos.pd/jsx/tylenol/motion.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"성공 {m}: {len(data['cuts'])}컷 → {out}")
            sys.exit(0)
        except json.JSONDecodeError as e: print(f"{m} JSON실패 {str(e)[:50]}")
        except errors.ServerError as e: print(f"{m} {str(e)[:60]}")
        except Exception as e: print(f"{m} {str(e)[:100]}")
    time.sleep(20 * (attempt + 1))
print("ERROR")
```

- [ ] **Step 2: 실행(수동, API 필요)** — 사용자/운영 시 실행:
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m scripts.tylenol_analyze
```
Expected: `성공 ...: 35컷 → .../motion.json` (rate limit 시 폴백 재시도). 실패해도 기존 motion.json 유지(하위호환).

- [ ] **Step 3: 커밋**
```bash
git add scripts/tylenol_analyze.py
git commit -m "feat(motion): gemini 분석 스크립트 — 라이브러리 어휘(프리셋/폰트/컬러/디테일) 주입

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 통합 검증 + 하위호환 회귀

**Files:**
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 하위호환 + 빌더 무결성 테스트** — 추가:
```python
def test_builder_backward_compatible_and_intact():
    """기존 prop 방식(preset 없는 anim)도 동작 + 빌더 괄호 균형."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    # preset 없을 때 기존 prop 분기 존재
    assert 'an.prop === "opacity"' in jsx and 'an.prop === "typeOn"' in jsx
    for o, c in [("{", "}"), ("(", ")"), ("[", "]")]:
        assert jsx.count(o) == jsx.count(c), o + c
```

- [ ] **Step 2: 실행** — `... -m pytest tests/test_panel_structure.py -v` → PASS

- [ ] **Step 3: 전체 스위트** — `... -m pytest -q` → 전체 PASS(회귀 없음)

- [ ] **Step 4: 커밋**
```bash
git add tests/test_panel_structure.py
git commit -m "test(motion): 빌더 하위호환 + 무결성 검증

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: 수동 E2E 안내(사용자)** — AE에서 `build_from_json.jsx` 실행 → 프리셋 적용된 컷(fade_scale_in/pop_bounce/mask_reveal/tilt_2_5d) + 디테일(그림자/그레인) 확인. gemini 재분석(Task 6) 후 motion.json이 프리셋명 기반이면 더 풍부.

---

## 자기 검토 결과 (Self-Review)

- **스펙 커버리지**: §3 프리셋 7종(Task 1·3), §4 디테일(Task 4), §5 폰트/컬러(Task 1·2·5), §6 gemini 스키마(Task 6), §7 빌더 확장(Task 2·3·4·5), §8 단일소스/하위호환/테스트(Task 1·7). P2/P3는 의도적 범위 밖.
- **플레이스홀더**: 없음 — 모든 코드 단계에 실제 코드.
- **타입 일관성**: `PRESETS/FONTMAP/COLORS`(Task 2) → `applyPreset/resolveFont/resolveColor`(Task 2·3)에서 동일 사용. `applyPreset(layer,isText,presetName,t0,dur,params)` 시그니처가 Task 3 정의 → Task 5 라우팅에서 동일 호출. `applyDetail(layer,details)`·`addGrainAdjustment(comp)`(Task 4) → Task 5에서 동일.
- **미해결**: mask_reveal의 `ADBE Vector Trim End` matchName은 AE 버전 차 가능 → Step에 opacity 폴백 포함. Glow matchName `ADBE Glo2` 확인 필요(안 되면 빌드 시 try/catch로 무시).
