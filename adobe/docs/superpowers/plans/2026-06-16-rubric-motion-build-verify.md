# rubric 기반 모션 생성 + 검증 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** rubric(`docs/research/ae_motion_techniques.md`)을 빌더의 모션 생성(smoothness/role/distance)과 Phase B 검증(헤드리스 렌더 + 듀얼 비디오 gemini 대조)에 동시에 적용한다.

**Architecture:** Part 1은 `build_from_json.jsx`에 옵셔널 파라미터(role/smoothness/distance)를 추가해 rubric 수치로 모션을 만든다(전부 후방호환). Part 2는 `verify_render.jsx`(헤드리스 AE 빌드+렌더) → ffmpeg(mov→mp4) → `gemini_client`(듀얼 비디오 대조, rubric 주입) → 2층 게이트(구조적 일치 + 지각 점수≥75)로 충실도를 판정한다. Part 2가 Part 1의 회귀 안전망이다.

**Tech Stack:** Python 3(stdlib + google-genai), ExtendScript(.jsx, AE 2026), aerender/afterfx 헤드리스, ffmpeg, pytest.

**선행 사실(구현자 필독):**
- 테스트 실행: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -v` (프로젝트 루트 `/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe`에서).
- jsx 구문 검증: `node --check <path>` (exit 0 = 통과, 출력 없음). node v25 가용.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` 추가. 작업은 `feat/tylenol-motion-recreation` 브랜치.
- 빌더 사실: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`의 `akBuildFromJson()`은 자기 폴더 `motion.json`을 읽고(line 10~12), `easeKeys(prop,dim,ease)`의 influence가 하드코딩(line 169: `(ease==="linear")?0.1:75`), `applyPreset(layer,isText,presetName,t0,dur,params)`는 6분기(line 176~220), Final 컴프명 `"TYL_Final"`(line 313), line 324에서 자동 실행.
- AE 실행 바이너리: `/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app/Contents/MacOS/After Effects`. ffmpeg: `/opt/homebrew/bin/ffmpeg`.

**파일 구조:**
| 파일 | 책임 | 신규/수정 |
|------|------|-----------|
| `scripts/motion_learn/curve.py` | smoothness→influence 변환(rubric 스펙 잠금, 순수) | 신규 |
| `cep/.../jsx/tylenol/build_from_json.jsx` | smoothness/role/distance 적용 + motion 경로 env 오버라이드 | 수정 |
| `scripts/motion_learn/gemini_client.py` | gemini File API 공유(analyze/verify) | 신규 |
| `scripts/motion_learn/analyze.py` | gemini_client 사용하도록 리팩터 | 수정 |
| `cep/.../jsx/tylenol/verify_render.jsx` | 헤드리스 빌드+렌더 오케스트레이션 | 신규 |
| `scripts/motion_learn/verify.py` | 구조검사+렌더+ffmpeg+대조+게이트 | 신규 |
| `scripts/motion_learn/__main__.py` | `verify` 서브커맨드 | 수정 |
| `tests/test_motion_learn.py` | 단위테스트 추가 | 수정 |

---

## Task 1: smoothness→influence 변환 (curve.py)

**Files:**
- Create: `scripts/motion_learn/curve.py`
- Test: `tests/test_motion_learn.py`

스펙 §3.1의 5개 앵커 포인트를 구간별 선형 보간하는 순수 함수. jsx가 같은 수치를 구현하며, 이 Python 함수가 스펙을 잠그고 회귀를 막는다.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_motion_learn.py` 끝에 추가

```python
def test_smoothness_to_influence_anchors():
    from scripts.motion_learn.curve import smoothness_to_influence
    assert smoothness_to_influence(0.0) == 0
    assert smoothness_to_influence(0.5) == 33
    assert smoothness_to_influence(0.75) == 75
    assert smoothness_to_influence(0.9) == 90
    assert smoothness_to_influence(1.0) == 95


def test_smoothness_to_influence_interp_and_clamp():
    from scripts.motion_learn.curve import smoothness_to_influence
    # 0.5~0.75 구간 중앙(0.625): 33 + (75-33)*0.5 = 54
    assert smoothness_to_influence(0.625) == 54
    # 범위 밖 클램프
    assert smoothness_to_influence(-1.0) == 0
    assert smoothness_to_influence(2.0) == 95
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py::test_smoothness_to_influence_anchors -v`
Expected: FAIL — `ModuleNotFoundError: scripts.motion_learn.curve`

- [ ] **Step 3: 구현**

```python
"""smoothness(0~1) → AE Keyframe influence(%) 변환. rubric §1-1 스펙 잠금.
빌더 jsx가 동일 수치를 구현하며, 이 함수가 회귀 기준이다.
주의: AE는 influence 최소 0.1을 요구하므로 jsx 측은 0을 0.1로 클램프한다(여기선 rubric 값 0 반환)."""
from __future__ import annotations

_ANCHORS = [(0.0, 0), (0.5, 33), (0.75, 75), (0.9, 90), (1.0, 95)]


def smoothness_to_influence(s: float) -> int:
    if s <= 0.0:
        return 0
    if s >= 1.0:
        return 95
    for (x0, y0), (x1, y1) in zip(_ANCHORS, _ANCHORS[1:]):
        if x0 < s <= x1:
            return round(y0 + (y1 - y0) * (s - x0) / (x1 - x0))
    return 0
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k smoothness -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add scripts/motion_learn/curve.py tests/test_motion_learn.py
git commit -m "feat(motion): smoothness→influence 변환 함수 (rubric 스펙 잠금)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 빌더 — smoothness 헬퍼 + easeKeys 파라미터화 (jsx)

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx:167-175` (easeKeys), 그 위에 헬퍼 2개 추가
- Test: `node --check`

`easeKeys`의 하드코딩 influence를 smoothness 기반으로. ease명만 있고 smoothness 미지정이면 현행 75(easeOut 기본)와 동일하게 매핑 → 동작 불변(후방호환).

- [ ] **Step 1: 헬퍼 함수 추가** — `function easeKeys(` 정의(line 167) 바로 위에 삽입

```javascript
        function easeDefaultSmoothness(ease) {
            if (ease === "linear") return 0.0;
            return 0.75; // easeOut/easeInOut/overshoot → 현행 influence 75
        }
        function smoothnessToInfluence(s) {
            if (s === undefined || s === null) return 75;
            if (s <= 0.0) return 0.1;   // AE influence 최소 0.1
            if (s >= 1.0) return 95;
            var ax = [0.0, 0.5, 0.75, 0.9, 1.0], ay = [0, 33, 75, 90, 95];
            for (var i = 0; i < ax.length - 1; i++) {
                if (s > ax[i] && s <= ax[i + 1]) {
                    return Math.round(ay[i] + (ay[i + 1] - ay[i]) * (s - ax[i]) / (ax[i + 1] - ax[i]));
                }
            }
            return 75;
        }
```

- [ ] **Step 2: easeKeys 시그니처/본문 교체** — line 167-175 전체를 아래로 교체

```javascript
        function easeKeys(prop, dim, ease, smoothness) {
            try {
                var s = (smoothness === undefined || smoothness === null) ? easeDefaultSmoothness(ease) : smoothness;
                var inf = smoothnessToInfluence(s);
                var arr = []; for (var d = 0; d < dim; d++) arr.push(new KeyframeEase(0, inf));
                var n = prop.numKeys;
                if (ease === "easeOut" || ease === "overshoot") prop.setTemporalEaseAtKey(n, arr, arr);
                else if (ease === "easeInOut") { prop.setTemporalEaseAtKey(1, arr, arr); prop.setTemporalEaseAtKey(n, arr, arr); }
            } catch (e) {}
        }
```

- [ ] **Step 3: 구문 검증**

Run: `node --check cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
Expected: exit 0, 출력 없음

- [ ] **Step 4: 후방호환 확인** — 기존 easeKeys 호출부(line 193/198/210/217 등)는 인자 3개만 전달 → smoothness=undefined → easeDefaultSmoothness 경로 → easeOut일 때 influence 75(현행과 동일). 코드 변경 없음, 육안 확인.

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx
git commit -m "feat(builder): easeKeys smoothness 파라미터화 (rubric §1-1, 후방호환)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 빌더 — applyPreset에 role/smoothness/distance 적용 (jsx)

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx:176-220` (applyPreset)
- Test: `node --check`

옵션 해석부를 추가하고 6분기에 role 반전·distance 스케일·smoothness 전달을 적용. 전부 옵셔널, 기본값이 현행과 동일.

- [ ] **Step 1: applyPreset 전체 교체** — line 176-220 (`function applyPreset(` ~ 닫는 `}`) 전체를 아래로 교체

```javascript
        function applyPreset(layer, isText, presetName, t0, dur, params) {
            var P = PRESETS[presetName]; if (!P) return;
            var pr = {}; for (var k in (P.params || {})) pr[k] = P.params[k];
            var cut = params || {};
            for (var k2 in cut) pr[k2] = cut[k2];   // 컷별 오버라이드
            dur = dur || 0.6; t0 = t0 || 0;
            // 옵션 해석: 컷 params > 프리셋 레벨 > 기본
            function opt(key, dflt) { return (cut[key] !== undefined) ? cut[key] : (P[key] !== undefined) ? P[key] : dflt; }
            var role = opt("role", "in");
            var dist = opt("distance", 1.0);
            var smooth = (cut.smoothness !== undefined) ? cut.smoothness
                       : (P.smoothness !== undefined) ? P.smoothness : null;  // null → easeKeys가 ease 기본 매핑
            var rev = (role === "out");
            layer.motionBlur = true;
            try {
                if (presetName === "type_on" && isText) {
                    var an = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                    an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
                    var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
                    try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
                    var off = sel.property("ADBE Text Percent Offset");
                    off.setValueAtTime(t0, rev ? 100 : 0); off.setValueAtTime(t0 + dur, rev ? 0 : 100);
                } else if (presetName === "fade_scale_in") {
                    var sf = 100 - (100 - (pr.scaleFrom || 85)) * dist;
                    var op = layer.property("Opacity"); op.setValueAtTime(t0, rev ? 100 : 0); op.setValueAtTime(t0 + dur * 0.6, rev ? 0 : 100);
                    var sc = layer.property("Scale");
                    sc.setValueAtTime(t0, rev ? [100, 100] : [sf, sf]); sc.setValueAtTime(t0 + dur, rev ? [sf, sf] : [100, 100]);
                    easeKeys(sc, 2, "easeOut", smooth);
                } else if (presetName === "slide_in") {
                    var dir = pr.dir || "left", off2 = (pr.offset || 80) * dist, ps = layer.property("Position"), cur = ps.value;
                    var dx = dir === "left" ? -off2 : dir === "right" ? off2 : 0;
                    var dy = dir === "up" ? -off2 : dir === "down" ? off2 : 0;
                    var pStart = rev ? [cur[0], cur[1]] : [cur[0] + dx, cur[1] + dy];
                    var pEnd = rev ? [cur[0] + dx, cur[1] + dy] : [cur[0], cur[1]];
                    ps.setValueAtTime(t0, pStart); ps.setValueAtTime(t0 + dur, pEnd); easeKeys(ps, 2, "easeOut", smooth);
                    var op2 = layer.property("Opacity"); op2.setValueAtTime(t0, rev ? 100 : 0); op2.setValueAtTime(t0 + dur * 0.4, rev ? 0 : 100);
                } else if (presetName === "pop_bounce") {
                    var ov = 100 + ((pr.overshoot || 110) - 100) * dist, sc2 = layer.property("Scale");
                    if (rev) {
                        sc2.setValueAtTime(t0, [100, 100]); sc2.setValueAtTime(t0 + dur * 0.4, [ov, ov]); sc2.setValueAtTime(t0 + dur, [0, 0]);
                    } else {
                        sc2.setValueAtTime(t0, [0, 0]); sc2.setValueAtTime(t0 + dur * 0.6, [ov, ov]); sc2.setValueAtTime(t0 + dur, [100, 100]);
                    }
                    try { sc2.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80)]); sc2.setTemporalEaseAtKey(3, [new KeyframeEase(0, 60), new KeyframeEase(0, 60)]); } catch (e) {}
                    var op3 = layer.property("Opacity"); op3.setValueAtTime(t0, rev ? 100 : 0); op3.setValueAtTime(t0 + dur * 0.2, rev ? 0 : 100);
                } else if (presetName === "mask_reveal") {
                    try {
                        var cont = layer.property("ADBE Root Vectors Group");
                        var trim = cont.addProperty("ADBE Vector Filter - Trim");
                        var te = trim.property("ADBE Vector Trim End");
                        te.setValueAtTime(t0, rev ? 100 : 0); te.setValueAtTime(t0 + dur, rev ? 0 : 100); easeKeys(te, 1, "easeInOut", smooth);
                    } catch (eM) {
                        var op4 = layer.property("Opacity"); op4.setValueAtTime(t0, rev ? 100 : 0); op4.setValueAtTime(t0 + dur, rev ? 0 : 100);
                    }
                } else if (presetName === "tilt_2_5d") {
                    layer.threeDLayer = true;
                    var ang = (pr.angle || -15) * dist, ry = layer.property("ADBE Transform Group").property("ADBE Rotate Y");
                    ry.setValueAtTime(t0, rev ? ang : 0); ry.setValueAtTime(t0 + dur, rev ? 0 : ang); easeKeys(ry, 1, "easeOut", smooth);
                }
            } catch (eP) {}
        }
```

- [ ] **Step 2: 구문 검증**

Run: `node --check cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
Expected: exit 0

- [ ] **Step 3: 후방호환 육안 확인** — role/distance/smoothness 미지정 시: role="in"(rev=false → 기존 시작/끝 값), dist=1.0(sf/off2/ov/ang 현행값), smooth=null(easeKeys가 easeOut→75). 즉 모든 기본값이 기존 코드와 동일. pop_bounce의 키 인덱스 2/3 ease는 유지.

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx
git commit -m "feat(builder): applyPreset role 반전 + distance 스케일 + smoothness 전달 (rubric §3, 후방호환)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: gemini_client.py 추출 + analyze.py 리팩터 (DRY)

**Files:**
- Create: `scripts/motion_learn/gemini_client.py`
- Modify: `scripts/motion_learn/analyze.py:12-36` (`_gemini_analyze`)
- Test: `tests/test_motion_learn.py`

`analyze.py`의 인라인 gemini(업로드·폴백·JSON)를 공유 모듈로 추출. verify가 듀얼 비디오로 재사용.

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_motion_learn.py` 끝에 추가

```python
def test_gemini_client_compare_videos(monkeypatch):
    from scripts.motion_learn import gemini_client as gc
    monkeypatch.setattr(gc, "_client", lambda: object())
    monkeypatch.setattr(gc, "_upload", lambda client, p: "FILE:" + p)
    captured = {}
    monkeypatch.setattr(gc, "_generate_json",
                        lambda client, contents, models=None: (captured.update(contents=contents), {"score": 88})[1])
    out = gc.compare_videos("orig.mp4", "render.mp4", "PROMPT")
    assert out == {"score": 88}
    assert captured["contents"] == ["FILE:orig.mp4", "FILE:render.mp4", "PROMPT"]


def test_gemini_client_analyze_video(monkeypatch):
    from scripts.motion_learn import gemini_client as gc
    monkeypatch.setattr(gc, "_client", lambda: object())
    monkeypatch.setattr(gc, "_upload", lambda client, p: "F:" + p)
    monkeypatch.setattr(gc, "_generate_json",
                        lambda client, contents, models=None: {"cuts": [], "contents_len": len(contents)})
    out = gc.analyze_video("v.mp4", "PROMPT")
    assert out["contents_len"] == 2  # [file, prompt]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k gemini_client -v`
Expected: FAIL — `ModuleNotFoundError: scripts.motion_learn.gemini_client`

- [ ] **Step 3: gemini_client.py 구현**

```python
"""gemini File API 공유 클라이언트 — analyze(단일 영상)/verify(듀얼 영상) 공용.
모델 폴백 + JSON 응답. 단일 client로 업로드·생성을 묶어 파일 핸들 유효성 보장."""
from __future__ import annotations

import json
import time

DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]


def _client():
    from google import genai
    return genai.Client()


def _upload(client, path: str):
    f = client.files.upload(file=path)
    while f.state.name == "PROCESSING":
        time.sleep(5)
        f = client.files.get(name=f.name)
    return f


def _generate_json(client, contents: list, models=None) -> dict:
    from google.genai import errors, types
    cfg = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000)
    last = None
    for m in (models or DEFAULT_MODELS):
        try:
            resp = client.models.generate_content(model=m, contents=contents, config=cfg)
            return json.loads(resp.text)
        except (errors.ServerError, json.JSONDecodeError) as e:
            last = e
            continue
    raise RuntimeError("gemini 생성 실패: " + str(last))


def analyze_video(mp4_path: str, prompt: str, *, models=None) -> dict:
    client = _client()
    f = _upload(client, mp4_path)
    return _generate_json(client, [f, prompt], models=models)


def compare_videos(path_a: str, path_b: str, prompt: str, *, models=None) -> dict:
    client = _client()
    fa = _upload(client, path_a)
    fb = _upload(client, path_b)
    return _generate_json(client, [fa, fb, prompt], models=models)
```

- [ ] **Step 4: analyze.py 리팩터** — `_gemini_analyze`(line 12-36)를 아래로 교체(프롬프트 빌드만 유지, gemini 호출은 위임)

```python
def _gemini_analyze(mp4_path: str, lib_keys: list[str]) -> dict:
    """gemini 동영상이해 → {cuts, new_presets}. gemini_client에 위임."""
    from scripts.motion_learn import gemini_client
    prompt = (
        "이 모션그래픽 영상을 After Effects 컴프로 재현할 JSON으로만 출력(순수 JSON).\n"
        "모션은 가능한 한 아래 기존 프리셋명으로 매핑: " + json.dumps(lib_keys, ensure_ascii=False) + "\n"
        "기존으로 표현 안 되는 모션은 new_presets에 후보로 제안: "
        "{name(snake_case), props(opacity/scale/position/rotationY/trimEnd/textOffset 우선), ease, params, why}.\n"
        "출력: {\"cuts\":[{type,start,dur,bg,layers:[{type,text,color,font,x,y,w,h,"
        "anim:[{preset,t0,dur,params}]}]}], \"new_presets\":[...]}\n순수 JSON만."
    )
    return gemini_client.analyze_video(mp4_path, prompt)
```

이후 `import time`이 analyze.py에서 미사용이면 제거. `from google import genai` 등 상단 인라인 import도 `_gemini_analyze` 내부에 있었으므로 제거됨(파일 상단 import 확인).

- [ ] **Step 5: 테스트 통과 + 회귀 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -v`
Expected: PASS (신규 2 + 기존 test_analyze_splits_output 포함 전부 통과 — 기존 테스트는 `analyze._gemini_analyze`를 직접 패치하므로 영향 없음)

- [ ] **Step 6: 커밋**

```bash
git add scripts/motion_learn/gemini_client.py scripts/motion_learn/analyze.py tests/test_motion_learn.py
git commit -m "refactor(motion-learn): gemini File API 공유 모듈 추출 (analyze/verify DRY)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: verify.py 순수 로직 (구조검사·게이트·파싱·커맨드)

**Files:**
- Create: `scripts/motion_learn/verify.py` (순수 로직 함수만 우선; 오케스트레이션은 Task 7)
- Test: `tests/test_motion_learn.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_motion_learn.py` 끝에 추가

```python
def test_verify_structural_check():
    from scripts.motion_learn.verify import structural_check
    lib = {"presets": {"fade_scale_in": {}, "slide_in": {}}}
    motion_ok = {"cuts": [{"layers": [{"anim": [{"preset": "fade_scale_in"}]}]}]}
    r = structural_check(motion_ok, lib)
    assert r["pass"] is True and r["cut_count"] == 1 and r["issues"] == []
    motion_bad = {"cuts": [{"layers": [{"anim": [{"preset": "nope"}]}]}]}
    r2 = structural_check(motion_bad, lib)
    assert r2["pass"] is False and any("nope" in i for i in r2["issues"])
    r3 = structural_check({"cuts": []}, lib)
    assert r3["pass"] is False


def test_verify_passes_gate():
    from scripts.motion_learn.verify import passes_gate
    assert passes_gate(True, 80, 75) is True
    assert passes_gate(True, 70, 75) is False
    assert passes_gate(False, 99, 75) is False


def test_verify_parse_verdict():
    from scripts.motion_learn.verify import parse_verdict
    v = parse_verdict('{"score": 82, "diffs": [{"cut": 0, "kind": "easing", "detail": "x"}], "summary": "ok"}')
    assert v["score"] == 82 and v["diffs"][0]["kind"] == "easing" and v["summary"] == "ok"
    v2 = parse_verdict({"score": "50"})
    assert v2["score"] == 50 and v2["diffs"] == []


def test_verify_commands():
    from scripts.motion_learn.verify import build_ae_command, build_ffmpeg_command
    assert build_ae_command("/AE", "/x/verify.jsx") == ["/AE", "-r", "/x/verify.jsx"]
    assert build_ffmpeg_command("a.mov", "b.mp4")[:3] == ["ffmpeg", "-y", "-i"]
    assert build_ffmpeg_command("a.mov", "b.mp4")[-1] == "b.mp4"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k verify -v`
Expected: FAIL — `ModuleNotFoundError: scripts.motion_learn.verify`

- [ ] **Step 3: verify.py 순수 로직 구현**

```python
"""Phase B 검증 — 헤드리스 렌더 + 듀얼 비디오 gemini 대조 + 2층 게이트.
이 파일 전반부는 순수 로직(테스트 대상), verify()는 오케스트레이션."""
from __future__ import annotations

import json


def structural_check(motion: dict, lib: dict) -> dict:
    """motion.json 정합성: 컷 존재 + 사용 프리셋이 라이브러리에 존재하는가(결정론적)."""
    issues = []
    cuts = motion.get("cuts", []) or []
    if not cuts:
        issues.append("컷 없음")
    presets = set((lib.get("presets") or {}).keys())
    for i, c in enumerate(cuts):
        for lyr in (c.get("layers", []) or []):
            for an in (lyr.get("anim", []) or []):
                pn = an.get("preset")
                if pn and pn not in presets:
                    issues.append(f"cut{i}: 미존재 프리셋 {pn}")
    return {"pass": not issues, "issues": issues, "cut_count": len(cuts)}


def passes_gate(structural_pass: bool, score: int, threshold: int = 75) -> bool:
    return bool(structural_pass) and int(score) >= int(threshold)


def parse_verdict(raw) -> dict:
    data = raw if isinstance(raw, dict) else json.loads(raw)
    return {
        "score": int(data.get("score", 0)),
        "diffs": data.get("diffs", []) or [],
        "summary": data.get("summary", "") or "",
    }


def build_ae_command(afterfx_bin: str, jsx_path: str) -> list:
    return [afterfx_bin, "-r", jsx_path]


def build_ffmpeg_command(mov: str, mp4: str) -> list:
    return ["ffmpeg", "-y", "-i", mov, "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k verify -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add scripts/motion_learn/verify.py tests/test_motion_learn.py
git commit -m "feat(verify): 구조검사·게이트·verdict 파싱·커맨드 구성 순수 로직

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: verify_render.jsx + 빌더 motion 경로 env 오버라이드

**Files:**
- Modify: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx:9-12` (motion.json 경로 env 오버라이드)
- Create: `cep/com.autokairos.pd/jsx/tylenol/verify_render.jsx`
- Test: `node --check`

- [ ] **Step 1: 빌더 motion 경로 오버라이드** — line 9-11(`var here = ...` ~ `if (!jf.exists)`)을 아래로 교체

```javascript
        var here = new File($.fileName).parent;
        var envMotion = $.getenv("AK_VERIFY_MOTION");
        var jf = (envMotion && String(envMotion).length) ? new File(envMotion) : new File(here.fsName + "/motion.json");
        if (!jf.exists) return "ERROR: motion.json 없음: " + jf.fsName;
```

- [ ] **Step 2: 빌더 구문 검증**

Run: `node --check cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx`
Expected: exit 0

- [ ] **Step 3: verify_render.jsx 작성**

```javascript
// verify_render.jsx — 헤드리스 빌드+렌더. 실행: "After Effects" -r verify_render.jsx
// env: AK_VERIFY_MOTION(motion.json 절대경로), AK_VERIFY_OUT(.mov 절대경로), AK_VERIFY_AEP(.aep 절대경로)
// build_from_json.jsx 가 AK_VERIFY_MOTION 을 읽어 TYL_Final 컴프를 만든다. 여기선 그 컴프를 렌더.
(function () {
    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === name) return it;
        }
        return null;
    }
    try {
        var here = new File($.fileName).parent;
        $.evalFile(new File(here.fsName + "/build_from_json.jsx"));  // 자동 실행 → TYL_Final 생성
        var comp = findComp("TYL_Final");
        if (!comp) { $.writeln("ERROR: TYL_Final 컴프 없음"); app.quit(); return; }
        var outPath = $.getenv("AK_VERIFY_OUT");
        var aepPath = $.getenv("AK_VERIFY_AEP");
        if (aepPath && String(aepPath).length) app.project.save(new File(aepPath));
        var rqi = app.project.renderQueue.items.add(comp);
        rqi.outputModule(1).file = new File(outPath);
        app.project.renderQueue.render();
        $.writeln("OK: " + outPath);
    } catch (e) {
        $.writeln("ERROR: " + e.toString());
    }
    app.quit();
})();
```

- [ ] **Step 4: verify_render.jsx 구문 검증**

Run: `node --check cep/com.autokairos.pd/jsx/tylenol/verify_render.jsx`
Expected: exit 0

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx cep/com.autokairos.pd/jsx/tylenol/verify_render.jsx
git commit -m "feat(verify): 헤드리스 빌드+렌더 jsx + 빌더 motion 경로 env 오버라이드

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: verify() 오케스트레이션

**Files:**
- Modify: `scripts/motion_learn/verify.py` (verify() + 상수 + _compare_prompt + _next_round 추가)
- Test: `tests/test_motion_learn.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_motion_learn.py` 끝에 추가

```python
def test_verify_orchestration(tmp_path, monkeypatch):
    import subprocess
    from scripts.motion_learn import verify as V, gemini_client, state
    refs = tmp_path / "refs"; ref = refs / "s1"; ref.mkdir(parents=True)
    (refs / "s1.mp4").write_bytes(b"orig")
    (ref / "motion.json").write_text(json.dumps({"cuts": [{"layers": [{"anim": [{"preset": "fade_scale_in"}]}]}]}), encoding="utf-8")
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {}}}), encoding="utf-8")

    # AE/ffmpeg subprocess 모킹: 호출되면 출력 파일 생성
    def fake_run(cmd, **kw):
        # AE 렌더면 .mov, ffmpeg면 .mp4 생성
        for a in cmd:
            if str(a).endswith(".mov"):
                env = kw.get("env") or {}
                p = env.get("AK_VERIFY_OUT")
                if p:
                    open(p, "wb").write(b"mov")
            if str(a).endswith(".mp4"):
                open(a, "wb").write(b"mp4")
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(gemini_client, "compare_videos",
                        lambda a, b, prompt, **kw: {"score": 80, "diffs": [], "summary": "good"})

    out = V.verify("s1", refs, lib, threshold=75)
    assert out["passed"] is True and out["score"] == 80
    assert (ref / "verify" / "verdict.json").is_file()
    assert state.get_state(ref)["stage"] == "verified"


def test_verify_missing_inputs(tmp_path):
    from scripts.motion_learn import verify as V
    refs = tmp_path / "refs"; (refs / "s2").mkdir(parents=True)
    lib = tmp_path / "lib.json"; lib.write_text('{"presets":{}}', encoding="utf-8")
    out = V.verify("s2", refs, lib)
    assert "error" in out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k "verify_orchestration or verify_missing" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'verify'`

- [ ] **Step 3: verify.py에 오케스트레이션 추가** — Task 5의 순수 로직 아래에 추가

```python
import os
import subprocess
from pathlib import Path

from scripts.motion_learn import state, gemini_client

ROOT = Path(__file__).resolve().parents[2]
AFTERFX_BIN = os.environ.get(
    "AK_AFTERFX_BIN",
    "/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app/Contents/MacOS/After Effects",
)
VERIFY_JSX = ROOT / "cep" / "com.autokairos.pd" / "jsx" / "tylenol" / "verify_render.jsx"
RUBRIC_PATH = ROOT / "docs" / "research" / "ae_motion_techniques.md"


def _next_round(verify_dir: Path) -> int:
    n = 1
    while (verify_dir / f"build_{n:02d}.aep").exists() or (verify_dir / f"render_{n:02d}.mov").exists():
        n += 1
    return n


def _compare_prompt(rubric: str) -> str:
    return (
        "두 영상의 모션그래픽 충실도를 비교한다. 첫 번째=원본 레퍼런스, 두 번째=AE 렌더 결과.\n"
        "아래 rubric의 명명된 원칙(이징/오버슈트/타이밍/폴리시)으로 판정하라. "
        "'비슷해 보임'이 아니라 'easeOut인데 overshoot 없음', 'influence 대칭이라 기계적', "
        "'anticipation 없음', '모션블러 누락' 처럼 구체적으로.\n"
        "JSON으로만 출력: {\"score\": 0~100, "
        "\"diffs\": [{\"cut\": 정수, \"kind\": \"timing|position|easing|color|missing|polish\", \"detail\": \"...\"}], "
        "\"summary\": \"...\"}\n\n=== RUBRIC ===\n" + rubric
    )


def verify(slug: str, refs_dir: Path, lib_path: Path, *, threshold: int = 75, timeout: int = 600) -> dict:
    ref_dir = Path(refs_dir) / slug
    motion_fp = ref_dir / "motion.json"
    orig = Path(refs_dir) / (slug + ".mp4")
    if not motion_fp.is_file():
        return {"error": "motion.json 없음"}
    if not orig.is_file():
        return {"error": "원본 mp4 없음"}
    motion = json.loads(motion_fp.read_text(encoding="utf-8"))
    lib = json.loads(Path(lib_path).read_text(encoding="utf-8"))
    structural = structural_check(motion, lib)

    verify_dir = ref_dir / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    rnd = _next_round(verify_dir)
    aep = verify_dir / f"build_{rnd:02d}.aep"
    mov = verify_dir / f"render_{rnd:02d}.mov"
    mp4 = verify_dir / f"render_{rnd:02d}.mp4"

    env = dict(os.environ)
    env.update({"AK_VERIFY_MOTION": str(motion_fp), "AK_VERIFY_OUT": str(mov), "AK_VERIFY_AEP": str(aep)})
    try:
        subprocess.run(build_ae_command(AFTERFX_BIN, str(VERIFY_JSX)), env=env, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as e:
        return {"error": "AE 렌더 실패: " + str(e), "structural": structural}
    if not mov.exists():
        return {"error": "렌더 산출물 없음", "structural": structural}
    try:
        subprocess.run(build_ffmpeg_command(str(mov), str(mp4)), timeout=timeout)
    except (subprocess.SubprocessError, OSError) as e:
        return {"error": "ffmpeg 실패: " + str(e), "structural": structural}
    if not mp4.exists():
        return {"error": "mp4 변환 실패", "structural": structural}

    rubric = RUBRIC_PATH.read_text(encoding="utf-8") if RUBRIC_PATH.is_file() else ""
    try:
        raw = gemini_client.compare_videos(str(orig), str(mp4), _compare_prompt(rubric))
    except Exception as e:  # noqa: BLE001 — gemini 폴백 소진 등 모든 실패를 비차단 보고
        return {"error": "gemini 대조 실패: " + str(e), "structural": structural}
    v = parse_verdict(raw)
    passed = passes_gate(structural["pass"], v["score"], threshold)
    verdict = {
        "structural": structural, "score": v["score"], "diffs": v["diffs"],
        "summary": v["summary"], "threshold": threshold, "passed": passed, "round": rnd,
    }
    (verify_dir / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    state.set_stage(ref_dir, "verified" if passed else "needs_improvement",
                    {"verify_score": v["score"], "verify_round": rnd})
    return verdict
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -k verify -v`
Expected: PASS (Task 5의 4개 + 신규 2개)

- [ ] **Step 5: 커밋**

```bash
git add scripts/motion_learn/verify.py tests/test_motion_learn.py
git commit -m "feat(verify): verify() 오케스트레이션 — 헤드리스 렌더→ffmpeg→듀얼비디오 gemini→2층 게이트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: CLI verify 서브커맨드

**Files:**
- Modify: `scripts/motion_learn/__main__.py:17-47` (build_parser + main)
- Test: `tests/test_motion_learn.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_motion_learn.py` 끝에 추가

```python
def test_cli_verify_dispatch(tmp_path, monkeypatch):
    import scripts.motion_learn.__main__ as cli
    monkeypatch.setattr(cli, "REFS", tmp_path / "refs")
    monkeypatch.setattr(cli, "LIB", tmp_path / "lib.json")
    captured = {}
    from scripts.motion_learn import verify as V
    monkeypatch.setattr(V, "verify",
                        lambda slug, refs, lib, **kw: captured.update(slug=slug) or {"passed": True, "score": 90, "structural": {"issues": []}})
    cli.main(["verify", "--slug", "s9"])
    assert captured["slug"] == "s9"
```

기존 `test_cli_help_lists_commands`는 collect/analyze/merge 존재만 `in`으로 검사하므로 verify 추가로 깨지지 않는다(별도 수정 불필요).

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py::test_cli_verify_dispatch -v`
Expected: FAIL — argparse "invalid choice: 'verify'"

- [ ] **Step 3: build_parser에 verify 추가** — `build_parser()`의 `return p` 직전에 추가

```python
    v = sub.add_parser("verify"); v.add_argument("--slug", required=True); v.add_argument("--threshold", type=int, default=75)
```

- [ ] **Step 4: main()에 verify 분기 추가** — `main()`의 import 줄을 `from scripts.motion_learn import collect, analyze, merge_presets, verify`로 바꾸고, merge 분기 뒤에 추가

```python
    elif args.cmd == "verify":
        r = verify.verify(args.slug, REFS, LIB, threshold=args.threshold)
        if r.get("error"):
            print("검증 실패:", r["error"])
        else:
            print(f"검증: {'통과' if r['passed'] else '재시도'} (점수 {r['score']}/{r['threshold']}, "
                  f"구조 {'OK' if not r['structural']['issues'] else r['structural']['issues']}) → refs/{args.slug}/verify/verdict.json")
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -v`
Expected: PASS (전체)

- [ ] **Step 6: 커밋**

```bash
git add scripts/motion_learn/__main__.py tests/test_motion_learn.py
git commit -m "feat(cli): motion_learn verify 서브커맨드

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 완료 후

전체 테스트: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -q` 로 회귀 확인.
수동 E2E(CI 아님, 실제 AE 필요): `python -m scripts.motion_learn verify --slug <기존 분석된 slug>` 로 닫힌 루프(빌더 P1 → 렌더 → gemini 점수) 1회 검증.
범위 밖(별도): Phase C 개선 루프, P2 고급효과(트랜지션/파티클/모핑 — Effect 레이어 확장).
