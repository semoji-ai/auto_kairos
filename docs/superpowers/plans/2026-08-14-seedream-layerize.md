# Seedream layerize 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 씬 레이어 분리를 "요소마다 다시 그리기"에서 Seedream layerize의 "한 번에 오려내기"로 바꾸고, 그에 딸린 키 컬러·크로마 키잉·위치 QC 코드를 제거한다.

**Architecture:** `fal_api.layerize()` 가 호출 1회로 투명 PNG 여러 장과 각 레이어의 `bounding_box`·`z_index` 를 받아온다. `split_scene_to_elements` 는 `z_index 0`(인페인팅된 배경판)을 `{sid}__bg.png` 로, 이름 있는 레이어를 기존 요소 파일명으로 저장하고 bbox·z를 요소 사이드카에 남긴다. 매니페스트가 그 bbox로 AE 배치 좌표를 계산하며, bbox가 없는 기존 프로젝트는 지금의 풀프레임 경로를 그대로 탄다.

**Tech Stack:** Python 3.11 stdlib(`urllib`, `base64`, `json`), Pillow, pytest, ExtendScript.

## Global Constraints

- 프롬프트에 **`background` 를 절대 쓰지 않는다.** 쓰면 구멍 뚫린 배경 요소 레이어가 한 장 더 오고 비용도 는다. 배경은 `z_index 0` 을 쓴다.
- 저장 파일명은 기존 규칙 그대로다: 배경 `{sid}__bg.png`, 요소 `{sid}__{i}_{슬러그}[_char].png`. `kind == "character"` 일 때만 `_char` 접미사.
- 응답의 `image.width`/`height` 는 `null` 로 온다 — 내려받은 PNG를 열어 크기를 재야 한다.
- 레이어 PNG 크기는 bbox 크기와 다르다(배율이 레이어마다 제각각, 비율은 유지).
- `MAX_ELEMENTS = 4` 유지. 배경 1장을 더해 씬당 5레이어.
- `FAL_KEY` 는 `fal_api.api_key()`(`FAL_KEY` → `FAL_API_KEY` 순)로 읽는다.
- 실패는 `FalError` 로 던진다 — 조용한 폴백 없음.
- stdlib만 사용, 새 의존성 없음.
- 한국어 주석·문구에 일본어 가나와 한자를 쓰지 않는다.
- ExtendScript는 ES3: `var` 만, 화살표 함수·템플릿 리터럴 금지.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/fal_api.py` | `layerize()` 추가 — 호출·data URI·레이어 다운로드. imagegen을 모른다 |
| `backend/imagegen.py` | `split_scene_to_elements` 를 layerize 기반으로 재작성, 다시 그리기 경로 제거, 사이드카에 bbox·z 저장 |
| `backend/manifest.py` | 사이드카 bbox → `position`/`scale`/`foot`, `z` 순 정렬 |
| `cep/…/js/storyboard.js` | 낱개 재생성·삭제 문구를 "씬 재분리"로 |
| `tests/test_fal_layerize.py` (신규) | layerize 호출 단위 테스트 |
| `tests/test_layer_split.py` (신규) | 저장·사이드카·예산·unexpected |
| `docs/notes/seedream-layerize-trial-response.json` | 실호출 응답 — 테스트 픽스처(이미 커밋됨) |

---

### Task 1: `fal_api.layerize()`

**Files:**
- Modify: `backend/fal_api.py`
- Test: `tests/test_fal_layerize.py`

**Interfaces:**
- Consumes: `fal_api.api_key()`, `fal_api.data_uri(path)`, `fal_api.FalError`
- Produces:
  - `LAYERIZE_ENDPOINT: str` = `"https://fal.run/bytedance/seedream/v5/pro/layerize"`
  - `build_layerize_prompt(names: list) -> str`
  - `layerize(image_path, names: list, *, timeout: int = 600) -> list` — `z_index` 오름차순 `[{"name": str|None, "z": int, "bbox": list|None, "data": bytes}]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_fal_layerize.py`:

```python
"""Seedream layerize 호출 — 프롬프트·요청 형태·응답 파싱."""
import json
from pathlib import Path

import pytest

from backend import fal_api

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "notes" / "seedream-layerize-trial-response.json"


def _png(tmp_path, name="scene.png", data=b"SCENE"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


class _Resp:
    def __init__(self, payload):
        self._p = payload
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _fake_transport(seen, payload):
    """POST는 payload를, 그 외(레이어 다운로드)는 URL을 본뜬 바이트를 돌려준다."""
    def _open(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url == fal_api.LAYERIZE_ENDPOINT:
            seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp(json.dumps(payload).encode())
        seen.setdefault("downloads", []).append(url)
        return _Resp(b"PNG:" + url.encode()[-6:])
    return _open


def test_prompt_lists_names_and_never_says_background():
    """background를 이름으로 쓰면 구멍 뚫린 배경 요소가 한 장 더 온다 — 절대 쓰지 않는다."""
    p = fal_api.build_layerize_prompt(["white electric car", "man on the right"])
    assert "white electric car" in p and "man on the right" in p
    assert "background" not in p.lower()


def test_layerize_posts_expected_request(tmp_path, monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    seen = {}
    monkeypatch.setattr(fal_api, "api_key", lambda: "KEY1")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport(seen, payload))

    layers = fal_api.layerize(_png(tmp_path), ["white electric car"])
    assert seen["headers"]["authorization"] == "Key KEY1"
    assert seen["body"]["image_url"].startswith("data:image/png;base64,")
    assert seen["body"]["image_size"] == "auto"
    assert "white electric car" in seen["body"]["prompt"]
    assert len(layers) == 6                       # 픽스처 실측: z0 배경판 + 이름 5장
    assert len(seen["downloads"]) == 6


def test_layerize_returns_layers_sorted_with_plate_first(tmp_path, monkeypatch):
    """z0은 이름·bbox가 없는 인페인팅 배경판 — 항상 맨 앞."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_transport({}, payload))

    layers = fal_api.layerize(_png(tmp_path), ["white electric car"])
    assert [L["z"] for L in layers] == [0, 1, 2, 3, 4, 5]
    assert layers[0]["name"] is None and layers[0]["bbox"] is None
    car = [L for L in layers if L["name"] == "white electric car"][0]
    assert car["bbox"] == [344, 500, 1254, 912]   # 실측 bbox
    assert car["data"].startswith(b"PNG:")


def test_layerize_without_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "")
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), ["a"])


def test_layerize_empty_layers_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen",
                        _fake_transport({}, {"images": [], "layers": []}))
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), ["a"])


def test_layerize_requires_names(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api, "api_key", lambda: "K")
    with pytest.raises(fal_api.FalError):
        fal_api.layerize(_png(tmp_path), [])
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_fal_layerize.py -q`
Expected: FAIL — `AttributeError: module 'backend.fal_api' has no attribute 'LAYERIZE_ENDPOINT'`

- [ ] **Step 3: 구현**

`backend/fal_api.py` 끝에 추가한다:

```python
LAYERIZE_ENDPOINT = "https://fal.run/bytedance/seedream/v5/pro/layerize"


def build_layerize_prompt(names: list) -> str:
    """분리할 요소 이름을 영어로 나열한다.

    이 모델은 프롬프트에 적은 이름대로 쪼갠다 — 적지 않은 것은 배경에 남는다.
    'background'는 절대 넣지 않는다: 넣으면 하늘·도로가 뚫린 배경 요소 레이어가
    한 장 더 오는데, 우리가 쓰는 배경은 z_index 0의 인페인팅된 판이다."""
    joined = ", ".join(n for n in names if n)
    return ("Separate this illustration into transparent layers. "
            f"Extract each of these as its own layer: {joined}. "
            "Keep each element whole and in its original position.")


def layerize(image_path, names: list, *, timeout: int = 600) -> list:
    """씬 이미지를 레이어로 분리. z_index 오름차순 목록을 돌려준다.

    각 항목 {name(z0은 None), z, bbox(z0은 None), data(PNG 바이트)}.
    응답의 image.width/height는 null로 오므로 크기는 호출자가 PNG에서 읽는다."""
    key = api_key()
    if not key:
        raise FalError("FAL_KEY(또는 FAL_API_KEY) 없음 — auto_kairos .env 또는 환경변수")
    picked = [n for n in (names or []) if n]
    if not picked:
        raise FalError("분리할 요소 이름 없음")
    src = Path(image_path)
    if not src.is_file():
        raise FalError(f"씬 이미지 없음: {src}")
    body = json.dumps({
        "image_url": data_uri(src),
        "prompt": build_layerize_prompt(picked),
        "image_size": "auto",
    }).encode("utf-8")
    req = urllib.request.Request(
        LAYERIZE_ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except FalError:
        raise
    except Exception as e:
        raise FalError(f"layerize 호출 실패: {str(e)[:200]}") from e
    raw = data.get("layers") or []
    if not raw:
        raise FalError(f"layerize 응답에 레이어 없음: {str(data)[:200]}")
    out = []
    for L in sorted(raw, key=lambda x: x.get("z_index") or 0):
        url = ((L.get("image") or {}).get("url") or "").strip()
        if not url:
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:
                blob = resp.read()
        except Exception as e:
            raise FalError(f"레이어 내려받기 실패: {str(e)[:200]}") from e
        bb = (L.get("bounding_box") or {}).get("absolute")
        out.append({"name": L.get("name"), "z": L.get("z_index") or 0,
                    "bbox": list(bb) if bb else None, "data": blob})
    if not out:
        raise FalError("layerize 응답에 내려받을 이미지가 없음")
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_fal_layerize.py tests/test_fal_api.py -q`
Expected: PASS — 신규 6개 + 기존 fal_api 8개

- [ ] **Step 5: 커밋**

```bash
git add backend/fal_api.py tests/test_fal_layerize.py
git commit -m "feat(fal): Seedream layerize 호출 — 이름 기반 분리, z0 배경판 포함"
```

---

### Task 2: 분리를 layerize 기반으로 재작성

**Files:**
- Modify: `backend/imagegen.py` — `split_scene_to_elements`
- Test: `tests/test_layer_split.py`

**Interfaces:**
- Consumes: `fal_api.layerize`, `imagegen.write_element_specs`, `imagegen._layer_slug`, `imagegen.versioned_path`, `imagegen._archive_prev_layers`, `imagegen.apply_element_budget`
- Produces: `split_scene_to_elements(proj_dir, scene_image, sid, elements, *, subdir="layers", concurrency=1, on_event=None) -> dict` — `{"layers": [{"name","rel","status","z","bbox"}], "unexpected": [str]}`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_split.py`:

```python
"""layerize 기반 분리 — 저장 규칙·사이드카·예산·예상 외 레이어."""
import json
from pathlib import Path

from backend import imagegen

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "notes" / "seedream-layerize-trial-response.json"

ELEMENTS = [
    {"name": "차량", "name_en": "white electric car", "location": "중앙",
     "kind": "object", "reason": "r", "intent": "i"},
    {"name": "남자", "name_en": "man on the right", "location": "우측",
     "kind": "character", "reason": "r", "intent": "i"},
]


def _fake_layerize(seen):
    """픽스처의 z/name/bbox를 그대로 흉내낸다(데이터는 짧은 더미 PNG 바이트)."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _call(image_path, names, **kw):
        seen["names"] = list(names)
        out = []
        for L in sorted(payload["layers"], key=lambda x: x["z_index"]):
            bb = (L.get("bounding_box") or {}).get("absolute")
            out.append({"name": L.get("name"), "z": L["z_index"],
                        "bbox": list(bb) if bb else None,
                        "data": b"\x89PNG" + str(L["z_index"]).encode()})
        return out
    return _call


def _run(tmp_path, monkeypatch, elements=None):
    seen = {}
    monkeypatch.setattr(imagegen.fal_api, "layerize", _fake_layerize(seen))
    scene = tmp_path / "scene.png"
    scene.write_bytes(b"\x89PNG")
    res = imagegen.split_scene_to_elements(tmp_path, str(scene), "ab",
                                           elements if elements is not None else ELEMENTS)
    return res, seen, tmp_path / "layers"


def test_prompt_names_come_from_name_en_only(tmp_path, monkeypatch):
    _res, seen, _d = _run(tmp_path, monkeypatch)
    assert seen["names"] == ["white electric car", "man on the right"]
    assert not any("background" in n.lower() for n in seen["names"])


def test_plate_saved_as_background_file(tmp_path, monkeypatch):
    """z0(이름·bbox 없음)이 기존 배경 파일명으로 저장돼야 매니페스트·삭제가 그대로 동작한다."""
    _res, _seen, d = _run(tmp_path, monkeypatch)
    assert (d / "ab__bg.png").is_file()


def test_named_layers_use_existing_filename_rule(tmp_path, monkeypatch):
    res, _seen, d = _run(tmp_path, monkeypatch)
    names = sorted(p.name for p in d.glob("ab__*.png"))
    assert "ab__0_white_electric_car.png" in names
    assert any(n.startswith("ab__1_man_on_the_right") and n.endswith("_char.png") for n in names)
    assert all(L["status"] == "completed" for L in res["layers"])


def test_sidecar_keeps_bbox_and_z(tmp_path, monkeypatch):
    _res, _seen, d = _run(tmp_path, monkeypatch)
    specs = imagegen.load_element_specs(d, "ab")
    car = [s for s in specs if s["name_en"] == "white electric car"][0]
    assert car["bbox"] == [344, 500, 1254, 912]      # 실측 bbox
    assert car["z"] == 3
    assert car["intent"] == "i" and car["kind"] == "object"


def test_unexpected_layers_are_reported_not_dropped(tmp_path, monkeypatch):
    """요청하지 않은 이름이 오면(모델이 임의로 쪼갬) 버리지 않고 알린다."""
    res, _seen, _d = _run(tmp_path, monkeypatch)
    assert "background" in res["unexpected"]         # 픽스처의 z1은 요청 목록에 없다
    assert "EV charger" in res["unexpected"]


def test_budget_caps_names_sent(tmp_path, monkeypatch):
    six = [{"name": f"요소{i}", "name_en": f"thing {i}", "location": "",
            "kind": "object", "reason": "r", "intent": "i"} for i in range(6)]
    _res, seen, _d = _run(tmp_path, monkeypatch, elements=six)
    assert len(seen["names"]) == imagegen.MAX_ELEMENTS == 4


def test_previous_layers_archived(tmp_path, monkeypatch):
    d = tmp_path / "layers"
    d.mkdir()
    (d / "ab__0_old.png").write_bytes(b"\x89PNG")
    _res, _seen, _d = _run(tmp_path, monkeypatch)
    assert not (d / "ab__0_old.png").exists()
    assert (d / "_prev" / "ab__0_old.png").is_file()
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_split.py -q`
Expected: FAIL — 기존 `split_scene_to_elements` 가 `_run_fal_image` 를 부르므로 `fal_api.layerize` 가짜가 호출되지 않아 `seen["names"]` 가 없다(`KeyError`)

- [ ] **Step 3: 구현**

`backend/imagegen.py` 의 `split_scene_to_elements` 전체를 아래로 교체한다:

```python
def split_scene_to_elements(proj_dir: Path, scene_image: str, sid: str, elements: list,
                            *, subdir: str = "layers", concurrency: int = 1, on_event=None) -> dict:
    """씬 이미지를 layerize로 분리해 투명 PNG 여러 장을 저장한다.

    모델이 프롬프트에 적은 이름대로 오려내므로 다시 그리지 않는다 — 원위치가 어긋날 수 없다.
    z_index 0은 요소가 지워지고 메워진 배경판이라 그대로 배경 레이어로 쓴다.
    concurrency는 호출 1회 구조라 쓰지 않으며, 기존 호출부 호환을 위해 남긴다."""
    out_base = Path(proj_dir) / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    _archive_prev_layers(out_base, sid)     # 재분리 시 기존 레이어 누적 방지(무삭제)
    picked = apply_element_budget(elements)["elements"]
    names = [(e.get("name_en") or "").strip() for e in picked]
    names = [n for n in names if n]
    layers = fal_api.layerize(scene_image, names)

    by_name = {}
    for i, el in enumerate(picked):
        key = (el.get("name_en") or "").strip()
        if key:
            by_name[key] = (i, el)

    results, specs, kinds, unexpected = [], [], {}, []
    for L in layers:
        nm = L.get("name")
        if nm is None:                       # z0 — 인페인팅된 배경판
            out = versioned_path(out_base, f"{sid}__bg.png")
            out.write_bytes(L["data"])
            results.append({"name": "배경", "rel": out.relative_to(proj_dir).as_posix(),
                            "status": "completed", "z": L["z"], "bbox": None})
            if on_event:
                on_event(results[-1])
            continue
        hit = by_name.get(nm.strip())
        if hit is None:
            unexpected.append(nm)
            if on_event:
                on_event({"name": nm, "status": "unexpected"})
            continue
        i, el = hit
        tag = "_char" if el.get("kind") == "character" else ""
        out = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(nm)}{tag}.png")
        out.write_bytes(L["data"])
        stem = out.stem
        kinds[stem] = el.get("kind", "object")
        specs.append({"layer": stem, "index": i, "name": el.get("name", ""),
                      "name_en": nm, "location": el.get("location", ""),
                      "kind": el.get("kind", "object"), "intent": el.get("intent", ""),
                      "bbox": L.get("bbox"), "z": L.get("z")})
        results.append({"name": el.get("name", nm), "rel": out.relative_to(proj_dir).as_posix(),
                        "status": "completed", "z": L.get("z"), "bbox": L.get("bbox")})
        if on_event:
            on_event(results[-1])

    (out_base / KINDS_SIDECAR.format(sid=sid)).write_text(
        json.dumps(kinds, ensure_ascii=False, indent=2), encoding="utf-8")
    write_element_specs(out_base, sid, specs)
    return {"layers": results, "unexpected": unexpected}
```

`backend/imagegen.py` 상단 import에 `fal_api` 가 이미 있는지 확인하고, 없으면 `from backend import env, fal_api` 로 둔다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_split.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py tests/test_layer_split.py
git commit -m "feat(layers): 분리를 layerize 한 번 호출로 — z0 배경판 + bbox 사이드카"
```

---

### Task 3: 다시 그리기 경로 제거

**Files:**
- Modify: `backend/imagegen.py`
- Delete: `tests/test_layer_keycolor.py`
- Modify: `tests/test_imagegen.py`, `tests/test_layer_edit.py`, `tests/test_layer_budget.py`, `tests/test_layer_analysis.py`

**Interfaces:**
- Produces: 없음(삭제 태스크). `split_scene_to_elements`·`regenerate_layer`·`delete_layer`·`load_element_specs`·`write_element_specs`·`analyze_scene_layers`·`generate_one`·`generate_character` 는 그대로 유지된다.

- [ ] **Step 1: 삭제 대상이 정말 안 쓰이는지 확인**

Run:
```bash
grep -rn "chroma_key\|pick_key_color\|scene_key_color\|position_score\|flatten_colors\|normalize_layer_size\|_alpha_foot\|generate_element_layer\|generate_background_layer\|build_element_layer_prompt\|_run_fal_image\|_aspect_mismatch\|_qc_feedback\|_gen_element_once\|KEY_COLORS\|KEY_HEX\|KEY_LABEL" backend/ cep/ | grep -v "^backend/imagegen.py"
```
Expected: `backend/manifest.py` 의 `_alpha_foot` 한 줄만 나온다. 그 외 백엔드·패널 참조가 있으면 멈추고 보고한다(테스트 파일 참조는 Step 3에서 정리한다).

- [ ] **Step 2: 제거**

`backend/imagegen.py` 에서 아래 심볼을 정의째 지운다:

`KEY_COLORS` `KEY_HEX` `KEY_LABEL` `_COVER_DIST` `_key_distance` `color_coverage` `pick_key_color` `scene_key_color` `chroma_key` `chroma_key_magenta` `position_score` `_qc_feedback` `_gen_element_once` `generate_element_layer` `generate_background_layer` `build_element_layer_prompt` `_run_fal_image` `flatten_colors` `_aspect_mismatch` `normalize_layer_size` `QC_MIN` `QC_MAX` `QC_POS_MIN` `_scene_size`

`regenerate_layer` 는 남기되 본문을 아래로 교체한다(layerize는 한 장만 다시 뽑을 수 없다):

```python
def regenerate_layer(proj_dir: Path, scene_image: str, sid: str, layer: str, *,
                     subdir: str = "layers", on_event=None) -> dict:
    """레이어 재생성 — layerize는 씬 단위 호출이라 그 씬을 통째로 다시 분리한다.
    기존 요소 명세(이름·종류·의도)를 그대로 다시 써서 같은 구성으로 뽑는다."""
    out_base = Path(proj_dir) / subdir
    specs = load_element_specs(out_base, sid)
    if not specs:
        return {"error": f"요소 명세 없음 — 먼저 레이어 분리 필요: {sid}"}
    elements = [{"name": s.get("name", ""), "name_en": s.get("name_en", ""),
                 "location": s.get("location", ""), "kind": s.get("kind", "object"),
                 "reason": "", "intent": s.get("intent", "")} for s in specs]
    res = split_scene_to_elements(proj_dir, scene_image, sid, elements,
                                  subdir=subdir, on_event=on_event)
    return {"layer": {"name": "씬 재분리", "status": "completed"},
            "layers": res.get("layers", []), "unexpected": res.get("unexpected", [])}
```

`Image`·`np` import는 다른 함수(`_img_size` 등)가 계속 쓰므로 남긴다. 제거 후 `python3 -c "from backend import imagegen"` 로 임포트가 되는지 확인한다.

- [ ] **Step 3: 테스트 정리**

`tests/test_layer_keycolor.py` 를 통째로 삭제한다 — 키 컬러 선택·크로마 키잉·요소 재생성만 검증하는 파일이라 남길 것이 없다.

```bash
git rm tests/test_layer_keycolor.py
```

나머지 네 파일에서는 **제거된 심볼을 참조하는 테스트만** 지운다. 남길지 지울지는 이 기준으로 판단한다 — `split_scene_to_elements`/`delete_layer`/`load_element_specs`/`analyze_scene_layers`/`apply_element_budget` 의 동작을 보는 테스트는 남기고(필요하면 `fal_api.layerize` 가짜로 갈아끼운다), 키잉·QC·요소 재생성 내부를 보는 테스트는 지운다.

- `tests/test_imagegen.py` — `_run_fal_image`/`chroma_key`/`scene_key_color`/`normalize_layer_size`/`build_element_layer_prompt` 를 patch 하거나 참조하는 테스트(대략 13개의 `test_split_*`/`test_bg_*`)를 지운다. `generate_one`·`generate_character`·`_run_codex_image` 테스트는 **그대로 둔다** — codex 경로는 유지된다.
- `tests/test_layer_edit.py` — `_run_fal_image`/`chroma_key`/`position_score` 를 patch 하는 재생성 테스트 2개를 지우고, `delete_layer`·`load_element_specs`·`is_background_layer` 테스트는 남긴다.
- `tests/test_layer_budget.py` — `_run_fal_image` 를 patch 하는 배경 프롬프트 테스트를 지우고, `apply_element_budget` 순수 함수 테스트와 `analyze_scene_layers` 예산 테스트는 남긴다.
- `tests/test_layer_analysis.py` — `_run_fal_image`/`chroma_key`/`position_score` 를 patch 하는 사이드카 왕복 테스트를 지운다(같은 내용을 Task 2의 `test_sidecar_keeps_intent`... 가 아니라 `tests/test_layer_split.py::test_sidecar_keeps_bbox_and_z` 가 이미 덮는다). 프롬프트·맥락 전달 테스트는 남긴다.

- [ ] **Step 4: 회귀 확인**

Run:
```bash
python3 -c "from backend import imagegen, manifest, router; print('import ok')"
python3 -m pytest tests/ -q \
  --ignore=tests/test_research_web_smoke.py \
  --ignore=tests/test_research_web_agent.py \
  --ignore=tests/test_research_news.py \
  --ignore=tests/test_research_lanes_basic.py
```
Expected: PASS. 테스트 수는 줄어든다(삭제분만큼). 실패가 남으면 그 테스트가 제거된 심볼을 참조하는지 확인하고 Step 3 기준으로 정리한다.

- [ ] **Step 5: 커밋**

```bash
git add -A
git commit -m "refactor(layers): 다시 그리기 경로 제거 — 키컬러·크로마 키잉·위치 QC 삭제"
```

---

### Task 4: 매니페스트가 bbox로 배치 좌표를 만든다

**Files:**
- Modify: `backend/manifest.py` — `_scene_layers`, `_alpha_foot` 제거
- Test: `tests/test_manifest.py`

**Interfaces:**
- Consumes: `imagegen.load_element_specs(out_base, sid) -> list`(항목에 `layer`·`bbox`·`z`)
- Produces: 매니페스트 레이어 항목에 `position: [x, y]`·`scale: float`·`foot: [x, y]`(bbox가 있을 때만)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_manifest.py` 에 이어붙인다:

```python
def test_layer_placement_from_bbox(tmp_path):
    """layerize 레이어는 크롭돼 오므로 bbox로 위치·크기를 되살린다(실측값 고정)."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (1052, 477)).save(lay / "ab__0_car.png")      # 실측 PNG 크기
    Image.new("RGB", (1536, 1024)).save(lay / "ab__bg.png")
    (lay / "ab__elements.json").write_text(_j.dumps([
        {"layer": "ab__0_car", "index": 0, "name": "차량", "name_en": "car",
         "kind": "object", "bbox": [344, 500, 1254, 912], "z": 3}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    car = [L for L in mf["scenes"][0]["layers"] if "car" in L["name"]][0]
    assert car["position"] == [799.0, 706.0]        # bbox 중심
    assert round(car["scale"], 1) == 86.5           # (1254-344)/1052*100
    assert car["foot"] == [799.0, 912.0]            # bbox 하단 중앙


def test_layers_ordered_by_z(tmp_path):
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    for nm in ("ab__bg.png", "ab__0_front.png", "ab__1_back.png"):
        Image.new("RGBA", (100, 100)).save(lay / nm)
    (lay / "ab__elements.json").write_text(_j.dumps([
        {"layer": "ab__0_front", "index": 0, "name": "앞", "kind": "object",
         "bbox": [0, 0, 50, 50], "z": 5},
        {"layer": "ab__1_back", "index": 1, "name": "뒤", "kind": "object",
         "bbox": [0, 0, 50, 50], "z": 2}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    names = [L["name"] for L in mf["scenes"][0]["layers"]]
    assert names[0] == "ab__bg"                     # 배경이 항상 맨 앞(AE 최하단)
    assert names.index("ab__1_back") < names.index("ab__0_front")   # z 오름차순


def test_legacy_layers_without_bbox_stay_fullframe(tmp_path):
    """기존 프로젝트는 풀프레임 PNG라 좌표가 없다 — 지금처럼 1:1로 겹친다."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (1920, 1080)).save(lay / "ab__0_old.png")
    Image.new("RGB", (1920, 1080)).save(lay / "ab__bg.png")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    old = [L for L in mf["scenes"][0]["layers"] if "old" in L["name"]][0]
    assert "position" not in old and "scale" not in old
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: FAIL — `KeyError: 'position'`

- [ ] **Step 3: 구현**

`backend/manifest.py` 의 `_alpha_foot` 함수를 통째로 지우고, `_scene_layers` 를 아래로 교체한다:

```python
def _scene_layers(proj_dir: Path, layer_rels: list, sid: str = "") -> list:
    """[{name, path(abs), kind, position?, scale?, foot?}] — 배경(__bg)을 맨 앞(AE 최하단)으로.

    layerize 레이어는 요소 크기로 크롭돼 오므로 요소 사이드카의 bbox로 위치·크기를 되살린다:
    position=bbox 중심, scale=bbox폭/PNG폭. bbox가 없는 기존 프로젝트 레이어는
    풀프레임 PNG라 좌표를 싣지 않고 jsx가 1:1로 겹친다."""
    from backend import imagegen
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(proj_dir / "layers", sid)} if sid else {}
    bg = [r for r in layer_rels if "__bg" in Path(r).name]
    el = [r for r in layer_rels if "__bg" not in Path(r).name]
    el.sort(key=lambda r: (specs.get(Path(r).stem, {}).get("z") is None,
                           specs.get(Path(r).stem, {}).get("z") or 0,
                           Path(r).name))
    out = []
    for r in bg + el:
        stem = Path(r).stem
        entry = {"name": stem, "path": _abs(proj_dir, r),
                 "kind": "bg" if "__bg" in Path(r).name else "element"}
        bbox = (specs.get(stem) or {}).get("bbox")
        if entry["kind"] == "element" and bbox and len(bbox) == 4:
            l, t, rr, b = [float(v) for v in bbox]
            size = _img_size(proj_dir / r)
            if size and size[0]:
                entry["position"] = [(l + rr) / 2, (t + b) / 2]
                entry["scale"] = (rr - l) / size[0] * 100
                entry["foot"] = [(l + rr) / 2, b]
        out.append(entry)
    return out
```

`_scene_layers` 호출부에 `sid` 를 넘기도록 고친다:

```python
        layers = [] if is_layout_scene else _scene_layers(proj_dir, s.get("_layers") or [], sid)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_manifest.py tests/test_layer_split.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/manifest.py tests/test_manifest.py
git commit -m "feat(layers): bbox로 AE 배치 좌표 계산 + z 순 정렬, 기존 풀프레임 폴백 유지"
```

---

### Task 5: 패널 문구 + 전체 회귀

**Files:**
- Modify: `cep/com.autokairos.pd/js/storyboard.js`
- Test: `tests/test_panel_structure.py`

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_panel_structure.py` 에 이어붙인다:

```python
def test_layer_buttons_say_scene_resplit():
    """layerize는 씬 단위 호출이라 레이어 한 장만 다시 뽑을 수 없다 — 문구가 그걸 알려야 한다."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "씬을 다시 분리" in js
    assert "이 레이어만 다시 생성" not in js
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_panel_structure.py::test_layer_buttons_say_scene_resplit -q`
Expected: FAIL — `AssertionError`

- [ ] **Step 3: 구현**

`cep/com.autokairos.pd/js/storyboard.js` 에서 썸네일 버튼 title을 고친다. `↻` 버튼의 title 삼항식을 아래로 교체한다:

```javascript
      +   '<button class="lyr-regen" title="' + (isBg ? '씬을 다시 분리(배경 포함 전체)' : '씬을 다시 분리합니다 — 레이어 전체가 새로 만들어집니다') + '">↻</button>'
```

`deleteLayer` 의 확인 문구를 교체한다:

```javascript
  if (!confirm("레이어 '" + stem + "' 를 뺍니다.\n\n"
             + "지운 요소는 다시 배경에 포함되어야 하므로 씬을 다시 분리합니다(1~2분).\n"
             + "파일은 지워지지 않고 layers/_prev 로 이동합니다.")) return;
```

`regenLayer` 의 상태 문구를 교체한다:

```javascript
  _rowStatus(n, "씬 다시 분리 중... (layerize)");
```

- [ ] **Step 4: 테스트·문법 확인**

Run:
```bash
python3 -m pytest tests/test_panel_structure.py -q
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
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js tests/test_panel_structure.py
git commit -m "feat(panel): 레이어 재생성 문구를 씬 재분리로 — layerize는 씬 단위 호출"
```

---

## 사람이 직접 확인해야 하는 것

fal 호출은 전부 픽스처로 대체된다. 아래는 자동으로 검증할 수 없다.

1. `projects/tesla` 씬 5(`sb_230205cf.png`)로 실제 분리를 돌려 **AE에서 원본과 겹쳐** 위치·크기가 맞는지. bbox 배치가 틀리면 요소가 어긋난 자리에 놓인다.
2. 배경판(z0)이 요소가 움직여도 빈자리를 안 드러내는지.
3. `unexpected` 로 보고되는 레이어가 얼마나 자주 오는지 — 잦으면 프롬프트를 다듬어야 하고, 요금은 그만큼 더 나간다.
4. 인물 레이어에 `_char` 접미사가 실제로 붙어 모션 플랜이 그것을 캐릭터로 인식하는지.
