# 레이어 분리 fal 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 씬 레이어 분리를 codex `$imagegen` 대신 fal `xai/grok-imagine-image/v2.0/edit` 로 수행하고, 씬당 레이어를 요소 4 + 배경 1로 제한하며, 마젠타/그린 키 컬러를 이미지에 맞춰 자동 선택한다.

**Architecture:** `backend/fal_api.py` 가 stdlib `urllib` 로 fal REST를 호출한다. `imagegen._run_fal_image` 가 기존 `_run_codex_image` 와 같은 시그니처를 제공하므로, 이미 함수로 분리해 둔 `generate_element_layer` / `generate_background_layer` 는 호출 대상만 바꾸면 QC·재시도·`_prev` 처리를 그대로 재사용한다. 키 컬러는 씬 이미지의 색 분포로 결정해 씬별 사이드카에 고정한다.

**Tech Stack:** Python 3.11 stdlib(`urllib.request`, `base64`, `json`), Pillow + numpy(기존), pytest.

## Global Constraints

- **stdlib만 사용** — fal 호출에 새 패키지를 추가하지 않는다(`tts.py` 의 ElevenLabs 호출과 같은 방식).
- **`FAL_KEY` 는 `env.get_key("FAL_KEY")` 로 읽는다** — `os.environ` 우선, 없으면 auto_kairos `.env`.
- **fal 실패는 조용히 넘기지 않는다** — 키 없음/비200/타임아웃은 예외를 던져 잡 실패로 표면화한다.
- **씬 이미지·캐릭터 생성은 codex 경로를 바꾸지 않는다.** fal은 레이어 분리 전용.
- 한국어 주석·문서에 일본어 가나와 한자를 쓰지 않는다.
- 모델 엔드포인트: `https://fal.run/xai/grok-imagine-image/v2.0/edit`, 헤더 `Authorization: Key {FAL_KEY}`, `image_urls` 는 **최대 3장**.
- 레이어 상한: 요소 `MAX_ELEMENTS = 4`, 배경 1장 → 씬당 최대 5.
- 키 컬러 후보는 마젠타 `#FF00FF` 와 그린 `#00FF00` 둘뿐이다. 동률이면 마젠타.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/fal_api.py` (신규) | fal REST 호출 하나. data URI 인라인, 응답 이미지 다운로드. imagegen을 모른다. |
| `backend/imagegen.py` (수정) | `_run_fal_image`, `pick_key_color`, `chroma_key` 일반화, 요소 4개 상한, 프롬프트에 키 컬러 반영 |
| `cep/com.autokairos.pd/js/storyboard.js` (수정) | 레이어 모달에 `dropped` 표시 + 체크 4개 상한 |
| `.env.example`, `CLAUDE.md` (수정) | `FAL_KEY` 기재, 외부 이미지 API 금지 규칙의 예외 명시 |
| `tests/test_fal_api.py` (신규) | fal 어댑터 단위 테스트 |
| `tests/test_layer_keycolor.py` (신규) | 키 컬러 선택 + 그린 키잉 |
| `tests/test_layer_budget.py` (신규) | 요소 4개 상한 + dropped |

---

### Task 1: fal 어댑터

**Files:**
- Create: `backend/fal_api.py`
- Test: `tests/test_fal_api.py`

**Interfaces:**
- Consumes: `backend.env.get_key(name: str) -> str`
- Produces:
  - `ENDPOINT: str` = `"https://fal.run/xai/grok-imagine-image/v2.0/edit"`
  - `MAX_INPUT_IMAGES: int` = `3`
  - `data_uri(path: Path) -> str`
  - `edit_image(prompt: str, image_paths: list, *, output_format: str = "png", resolution: str = "2k", timeout: int = 180) -> bytes`
  - `FalError(Exception)`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_fal_api.py`:

```python
import base64
import json
from pathlib import Path

import pytest

from backend import fal_api


def _png(tmp_path, name="s.png", data=b"\x89PNG-bytes"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_data_uri_encodes_png(tmp_path):
    p = _png(tmp_path, data=b"abc")
    uri = fal_api.data_uri(p)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == b"abc"


def test_edit_image_posts_expected_request(tmp_path, monkeypatch):
    src = _png(tmp_path, data=b"scene")
    seen = {}

    class _Resp:
        def __init__(self, payload):
            self._p = payload
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=None):
        url = req.full_url
        if url.endswith("/edit"):
            seen["url"] = url
            seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
            seen["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp(json.dumps({"images": [{"url": "https://cdn.test/out.png",
                                                 "width": 1920, "height": 1080}]}).encode())
        seen["download"] = url
        return _Resp(b"OUTPUT-PNG")

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "KEY123" if n == "FAL_KEY" else "")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake_urlopen)

    out = fal_api.edit_image("요소만 남겨라", [src])
    assert out == b"OUTPUT-PNG"
    assert seen["url"] == fal_api.ENDPOINT
    assert seen["headers"]["authorization"] == "Key KEY123"
    assert seen["body"]["prompt"] == "요소만 남겨라"
    assert seen["body"]["output_format"] == "png"
    assert seen["body"]["resolution"] == "2k"
    assert seen["body"]["num_images"] == 1
    assert seen["body"]["image_urls"][0].startswith("data:image/png;base64,")
    assert seen["download"] == "https://cdn.test/out.png"


def test_edit_image_truncates_to_three_images(tmp_path, monkeypatch):
    srcs = [_png(tmp_path, f"s{i}.png", data=bytes([i])) for i in range(5)]
    seen = {}

    class _Resp:
        def __init__(self, p):
            self._p = p
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def _fake(req, timeout=None):
        if req.full_url.endswith("/edit"):
            seen["n"] = len(json.loads(req.data.decode())["image_urls"])
            return _Resp(json.dumps({"images": [{"url": "https://cdn.test/o.png"}]}).encode())
        return _Resp(b"X")

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", _fake)
    fal_api.edit_image("p", srcs)
    assert seen["n"] == fal_api.MAX_INPUT_IMAGES == 3


def test_edit_image_without_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "")
    with pytest.raises(fal_api.FalError) as e:
        fal_api.edit_image("p", [_png(tmp_path)])
    assert "FAL_KEY" in str(e.value)


def test_edit_image_raises_on_empty_images(tmp_path, monkeypatch):
    class _Resp:
        def read(self):
            return json.dumps({"images": []}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(fal_api.env, "get_key", lambda n: "K")
    monkeypatch.setattr(fal_api.urllib.request, "urlopen", lambda req, timeout=None: _Resp())
    with pytest.raises(fal_api.FalError):
        fal_api.edit_image("p", [_png(tmp_path)])
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_fal_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.fal_api'`

- [ ] **Step 3: 최소 구현**

`backend/fal_api.py`:

```python
"""fal 이미지 편집 API 호출 — 레이어 분리 전용.

CLAUDE.md의 '이미지 생성은 codex $imagegen 전용' 규칙의 명시적 예외.
씬 이미지·캐릭터 생성은 여전히 codex를 쓰고, 레이어 분리만 이 경로를 탄다.
새 의존성 없이 stdlib urllib만 사용(tts.py의 ElevenLabs 호출과 같은 방식).
"""
from __future__ import annotations

import base64
import json
import mimetypes
import urllib.request
from pathlib import Path

from backend import env

ENDPOINT = "https://fal.run/xai/grok-imagine-image/v2.0/edit"
MAX_INPUT_IMAGES = 3          # 모델 상한 — 초과분은 앞에서부터 자른다


class FalError(Exception):
    """fal 호출 실패 — 키 없음·비200·응답 이상. 상위 잡이 실패로 표면화한다."""


def data_uri(path: Path) -> str:
    """로컬 이미지를 base64 data URI로. fal 입력이 URL이라 로컬 파일을 그대로 못 넘긴다."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def edit_image(prompt: str, image_paths: list, *, output_format: str = "png",
               resolution: str = "2k", timeout: int = 180) -> bytes:
    """참조 이미지들을 두고 prompt대로 편집한 이미지 1장을 바이트로 반환."""
    key = env.get_key("FAL_KEY")
    if not key:
        raise FalError("FAL_KEY 없음(auto_kairos .env 또는 환경변수)")
    paths = [Path(p) for p in (image_paths or []) if Path(p).is_file()]
    if not paths:
        raise FalError("입력 이미지 없음")
    body = json.dumps({
        "prompt": prompt,
        "image_urls": [data_uri(p) for p in paths[:MAX_INPUT_IMAGES]],
        "num_images": 1,
        "output_format": output_format,
        "resolution": resolution,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except FalError:
        raise
    except Exception as e:                       # HTTPError·URLError·타임아웃·파싱 실패
        raise FalError(f"fal 호출 실패: {str(e)[:200]}") from e
    images = data.get("images") or []
    if not images or not images[0].get("url"):
        raise FalError(f"fal 응답에 이미지 없음: {str(data)[:200]}")
    try:
        with urllib.request.urlopen(images[0]["url"], timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        raise FalError(f"fal 결과 내려받기 실패: {str(e)[:200]}") from e
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_fal_api.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/fal_api.py tests/test_fal_api.py
git commit -m "feat(fal): 이미지 편집 API 어댑터 — stdlib urllib, data URI 인라인"
```

---

### Task 2: 키 컬러 자동 선택 + chroma_key 일반화

**Files:**
- Modify: `backend/imagegen.py` (`chroma_key_magenta` 근처, 파일 하단)
- Test: `tests/test_layer_keycolor.py`

**Interfaces:**
- Produces:
  - `KEY_COLORS: dict` = `{"magenta": (255, 0, 255), "green": (0, 255, 0)}`
  - `color_coverage(scene_image, key: str) -> float`
  - `pick_key_color(scene_image) -> dict` — `{"key": str, "rgb": list, "coverage": dict}`
  - `scene_key_color(out_base: Path, sid: str, scene_image) -> dict` — 사이드카 `{sid}__keycolor.json` 에 고정
  - `chroma_key(src_png: Path, out_png: Path, key: str = "magenta") -> dict`
  - `chroma_key_magenta(src_png, out_png) -> dict` — `chroma_key(..., "magenta")` 별칭(기존 호출부 보존)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_keycolor.py`:

```python
import json

import numpy as np
from PIL import Image

from backend import imagegen


def _solid(tmp_path, name, rgb, size=(40, 40)):
    p = tmp_path / name
    Image.new("RGB", size, rgb).save(p)
    return p


def test_pick_key_color_avoids_dominant_magenta(tmp_path):
    """씬이 마젠타로 가득하면 마젠타로 키잉할 수 없다 — 그린을 골라야 한다."""
    p = _solid(tmp_path, "m.png", (250, 10, 250))
    res = imagegen.pick_key_color(p)
    assert res["key"] == "green"
    assert res["rgb"] == [0, 255, 0]


def test_pick_key_color_avoids_dominant_green(tmp_path):
    p = _solid(tmp_path, "g.png", (10, 250, 10))
    assert imagegen.pick_key_color(p)["key"] == "magenta"


def test_pick_key_color_defaults_to_magenta(tmp_path):
    """둘 다 없으면 기존 기본값(마젠타)을 유지한다."""
    p = _solid(tmp_path, "b.png", (120, 120, 120))
    res = imagegen.pick_key_color(p)
    assert res["key"] == "magenta"
    assert res["coverage"]["magenta"] == 0.0


def test_scene_key_color_is_sticky(tmp_path):
    """요소·배경·재생성이 같은 색을 써야 한다 — 한 번 정하면 사이드카에 고정."""
    base = tmp_path / "layers"
    base.mkdir()
    p = _solid(tmp_path, "m.png", (250, 10, 250))
    first = imagegen.scene_key_color(base, "ab", p)
    assert first["key"] == "green"
    assert (base / "ab__keycolor.json").is_file()
    # 씬 이미지를 바꿔도 이미 정해진 값을 그대로 쓴다
    p2 = _solid(tmp_path, "g.png", (10, 250, 10))
    assert imagegen.scene_key_color(base, "ab", p2)["key"] == "green"


def test_chroma_key_green_makes_background_transparent(tmp_path):
    """그린 키잉이 마젠타와 같은 기준으로 알파를 만든다."""
    src = tmp_path / "src.png"
    a = np.zeros((10, 10, 3), dtype="uint8")
    a[:, :5] = (0, 255, 0)          # 왼쪽 절반 그린 = 빼낼 배경
    a[:, 5:] = (200, 30, 40)        # 오른쪽 절반 요소
    Image.fromarray(a, "RGB").save(src)
    out = tmp_path / "out.png"
    res = imagegen.chroma_key(src, out, key="green")
    alpha = np.array(Image.open(out).convert("RGBA"))[:, :, 3]
    assert alpha[:, :5].max() == 0            # 그린은 완전 투명
    assert alpha[:, 7:].min() == 255          # 요소는 불투명
    assert 0.4 < res["transparent_ratio"] < 0.6


def test_chroma_key_magenta_alias_still_works(tmp_path):
    src = tmp_path / "src.png"
    a = np.zeros((10, 10, 3), dtype="uint8")
    a[:, :5] = (255, 0, 255)
    a[:, 5:] = (30, 200, 40)
    Image.fromarray(a, "RGB").save(src)
    out = tmp_path / "out.png"
    res = imagegen.chroma_key_magenta(src, out)
    alpha = np.array(Image.open(out).convert("RGBA"))[:, :, 3]
    assert alpha[:, :5].max() == 0
    assert 0.4 < res["transparent_ratio"] < 0.6
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_keycolor.py -q`
Expected: FAIL — `AttributeError: module 'backend.imagegen' has no attribute 'pick_key_color'`

- [ ] **Step 3: 구현**

`backend/imagegen.py` 의 `chroma_key_magenta` 를 아래로 **교체**한다(기존 임계값·수축·페더·디스필 로직 유지, 키 색만 매개변수화):

```python
KEY_COLORS = {"magenta": (255, 0, 255), "green": (0, 255, 0)}
KEY_HEX = {"magenta": "#FF00FF", "green": "#00FF00"}
KEY_LABEL = {"magenta": "마젠타", "green": "그린"}
_COVER_DIST = 0.25          # 이 거리 안이면 '그 색과 겹친다'고 본다


def _key_distance(a: "np.ndarray", key: str) -> "np.ndarray":
    """픽셀별 키 색 거리(0=순수 키 색, 1=정반대). a는 RGB float 배열."""
    kr, kg, kb = KEY_COLORS[key]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return np.sqrt((kr - r) ** 2 + (kg - g) ** 2 + (kb - b) ** 2) / 441.673


def color_coverage(scene_image, key: str) -> float:
    """씬 이미지에서 그 키 색과 겹치는 픽셀 비율(0~1). 작을수록 키 컬러로 쓰기 좋다."""
    with Image.open(scene_image) as im:
        small = im.convert("RGB").resize((64, 64), Image.BILINEAR)
    a = np.array(small).astype(float)
    return float((_key_distance(a, key) < _COVER_DIST).mean())


def pick_key_color(scene_image) -> dict:
    """이미지에 덜 걸치는 키 색을 고른다. 동률이면 마젠타(기존 기본값)."""
    cov = {k: color_coverage(scene_image, k) for k in KEY_COLORS}
    key = "magenta" if cov["magenta"] <= cov["green"] else "green"
    return {"key": key, "rgb": list(KEY_COLORS[key]), "coverage": cov}


def scene_key_color(out_base: Path, sid: str, scene_image) -> dict:
    """씬의 키 색을 사이드카에 고정해 재사용. 요소·배경·재생성이 반드시 같은 색을 써야 한다."""
    fp = Path(out_base) / f"{sid}__keycolor.json"
    if fp.is_file():
        try:
            saved = json.loads(fp.read_text(encoding="utf-8"))
            if saved.get("key") in KEY_COLORS:
                return saved
        except (json.JSONDecodeError, OSError):
            pass
    res = pick_key_color(scene_image)
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return res


def chroma_key(src_png: Path, out_png: Path, key: str = "magenta") -> dict:
    """키 색 거리 기반 소프트 알파 + 가장자리 수축·페더 + 디스필.
    반환 {"transparent_ratio": float} — QC 게이트 신호로 사용."""
    im = Image.open(src_png).convert("RGBA")
    a = np.array(im).astype(float)
    dist = _key_distance(a, key)
    alpha = np.clip((dist - 0.18) / 0.22, 0.0, 1.0)           # 0.18 이하=투명, 0.40 이상=불투명
    # 가장자리 수축(erode 1px) — 키 색 프린지 제거
    core = alpha >= 0.999
    er = core.copy()
    er[1:, :] &= core[:-1, :]; er[:-1, :] &= core[1:, :]
    er[:, 1:] &= core[:, :-1]; er[:, :-1] &= core[:, 1:]
    edge = core & ~er
    alpha[edge] *= 0.8                                        # 경계 페더
    # 디스필: 남은 픽셀의 키 색 성분 감쇠
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    keep = alpha > 0
    if key == "magenta":
        over = keep & (g < np.minimum(r, b) - 40)
        a[over, 0] = np.minimum(a[over, 0], a[over, 1] + 40)
        a[over, 2] = np.minimum(a[over, 2], a[over, 1] + 40)
    else:                                                     # green
        over = keep & (g > np.maximum(r, b) + 40)
        a[over, 1] = np.minimum(a[over, 1], np.maximum(a[over, 0], a[over, 2]) + 40)
    a[:, :, 3] = alpha * 255
    Image.fromarray(a.astype("uint8"), "RGBA").save(out_png)
    return {"transparent_ratio": float((alpha < 0.5).sum()) / alpha.size}


def chroma_key_magenta(src_png: Path, out_png: Path) -> dict:
    """기존 호출부·테스트 보존용 별칭."""
    return chroma_key(src_png, out_png, key="magenta")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_keycolor.py tests/test_imagegen.py -q`
Expected: PASS — 새 6개 + 기존 imagegen 52개 (기존 마젠타 테스트가 별칭으로 그대로 통과해야 한다)

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py tests/test_layer_keycolor.py
git commit -m "feat(layers): 키 컬러 자동 선택(마젠타/그린) + chroma_key 일반화"
```

---

### Task 3: 프롬프트에 키 컬러 반영 + fal 실행 경로

**Files:**
- Modify: `backend/imagegen.py` (`build_element_layer_prompt`, `generate_element_layer`, `generate_background_layer`, `_gen_element_once`)
- Test: `tests/test_layer_keycolor.py` (추가)

**Interfaces:**
- Consumes: `fal_api.edit_image`, `imagegen.scene_key_color`, `imagegen.chroma_key`, `imagegen.KEY_HEX`, `imagegen.KEY_LABEL`
- Produces:
  - `build_element_layer_prompt(name, location, style_desc, rel_out, others=None, key="magenta") -> str`
  - `_run_fal_image(proj_dir: Path, out: Path, prompt: str, *, images=None, post=None) -> dict` — `{"status": "completed"|"failed", "path": str, "error"?: str}`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_keycolor.py` 에 이어붙인다:

```python
def test_element_prompt_uses_selected_key_color():
    p_m = imagegen.build_element_layer_prompt("인물", "좌측", "STYLE", "layers/a.png")
    assert "#FF00FF" in p_m and "마젠타" in p_m
    p_g = imagegen.build_element_layer_prompt("인물", "좌측", "STYLE", "layers/a.png", key="green")
    assert "#00FF00" in p_g and "그린" in p_g
    assert "#FF00FF" not in p_g


def test_element_prompt_exclusion_uses_key_color():
    p = imagegen.build_element_layer_prompt("인물", "좌측", "STYLE", "layers/a.png",
                                            others=["탁자"], key="green")
    assert "탁자" in p and "그린" in p


def test_run_fal_image_writes_output_and_runs_post(tmp_path, monkeypatch):
    from backend import fal_api
    out = tmp_path / "layers" / "x.png"
    called = {}
    monkeypatch.setattr(fal_api, "edit_image",
                        lambda prompt, imgs, **k: called.setdefault("prompt", prompt) or b"PNGDATA")
    monkeypatch.setattr(imagegen, "fal_api", fal_api)
    res = imagegen._run_fal_image(tmp_path, out, "프롬프트",
                                  images=[tmp_path / "scene.png"],
                                  post=lambda o: called.setdefault("post", str(o)))
    assert res["status"] == "completed"
    assert out.read_bytes() == b"PNGDATA"
    assert called["prompt"] == "프롬프트"
    assert called["post"] == str(out)


def test_run_fal_image_failure_returns_failed(tmp_path, monkeypatch):
    from backend import fal_api

    def _boom(*a, **k):
        raise fal_api.FalError("FAL_KEY 없음")

    monkeypatch.setattr(fal_api, "edit_image", _boom)
    res = imagegen._run_fal_image(tmp_path, tmp_path / "y.png", "p", images=[])
    assert res["status"] == "failed" and "FAL_KEY" in res["error"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_keycolor.py -q`
Expected: FAIL — `TypeError: build_element_layer_prompt() got an unexpected keyword argument 'key'`

- [ ] **Step 3: 구현**

`backend/imagegen.py` 상단 import에 `fal_api` 를 추가한다:

```python
from backend import env, fal_api
```

`build_element_layer_prompt` 를 교체한다:

```python
def build_element_layer_prompt(name: str, location: str, style_desc: str, rel_out: str,
                               others: list | None = None, key: str = "magenta") -> str:
    """단일 요소 레이어 프롬프트. others=별도 레이어로 분리되는 다른 요소들(이 레이어에서 제외).
    이 요소 위에 얹힌/붙은 것(others 제외)은 함께 그려 한 덩어리로 유지.
    key=빼낼 배경으로 채울 키 색(씬마다 scene_key_color가 정한다)."""
    others = [o for o in (others or []) if o and o != name]
    kl, kh = KEY_LABEL[key], KEY_HEX[key]
    excl = (f"단, 다음은 별도 레이어이므로 포함하지 말고 {kl}로 채운다: {', '.join(others)}.\n"
            if others else "")
    return (
        f"{style_desc}\n\n## 레이어 분리 — 단일 요소\n첨부한 씬 이미지를 레퍼런스로 사용한다.\n"
        f"이 씬에서 '{name}'({location})를 다시 그린다. "
        f"가장 중요한 규칙: 원본 씬에서 이 요소가 차지하는 **정확히 같은 좌표와 같은 크기** 그대로 그려라 — "
        f"절대 확대하지 말고, 중앙으로 옮기지 말고, 화면을 채우지 말 것. "
        f"이 레이어를 원본 위에 겹치면 픽셀이 일치해야 한다.\n"
        f"이 요소 위에 얹혀 있거나 붙어 있는 것(예: 위에 놓인 문서·물건)도 함께 그려 한 덩어리로 유지한다.\n"
        f"{excl}"
        f"그 외 전 영역(다른 인물·사물·배경)은 순수 {kl} 단색({kh})으로 채운다.\n"
        f"텍스트 없음."
    )
```

`_run_codex_image` 아래에 fal 실행 함수를 추가한다:

```python
def _run_fal_image(proj_dir: Path, out: Path, prompt: str, *, images=None, post=None) -> dict:
    """fal 편집 API로 이미지 1장 생성 → out에 저장. _run_codex_image와 같은 계약.
    레이어 분리 전용 경로(CLAUDE.md 예외). 실패는 {"status": "failed", "error": ...}."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = fal_api.edit_image(prompt, list(images or []))
    except fal_api.FalError as e:
        return {"status": "failed", "error": str(e)[:200], "path": str(out)}
    out.write_bytes(data)
    if post:
        post(out)
    return {"status": "completed", "path": str(out)}
```

`_gen_element_once` 의 시그니처와 본문에서 codex 호출을 fal 호출로 바꾸고 키 색을 받는다:

```python
def _gen_element_once(proj_dir: Path, scene_image: str, out: Path, prompt: str, scene_size,
                      key: str = "magenta"):
    """요소 레이어 1회 생성 + 후처리 → (res, transparent_ratio, position_score)."""
    ratio_box = {}

    def _post(o):
        raw_dir = o.parent / "_raw"
        raw_dir.mkdir(exist_ok=True)
        shutil.copy(o, raw_dir / o.name)
        flatten_colors(o)
        ratio_box.update(chroma_key(o, o, key=key))

    res = _run_fal_image(proj_dir, out, prompt, images=[scene_image], post=_post)
    pos = None
    if res.get("status") == "completed":
        if scene_size and _aspect_mismatch(out, scene_size):
            return res, ratio_box.get("transparent_ratio"), 0.0
        if scene_size:
            normalize_layer_size(out, scene_size)
        pos = position_score(out, scene_image)
    return res, ratio_box.get("transparent_ratio"), pos
```

`generate_element_layer` 에서 키 색을 결정해 프롬프트·키잉·재시도에 모두 넘긴다. 함수 앞부분의 `style`/`scene_size` 결정 직후에 다음을 추가하고, `build_element_layer_prompt` 호출 2곳에 `key=key` 를, `_gen_element_once` 호출 2곳에 `key` 를, 재시도 실패 시 `chroma_key_magenta(out, out)` 를 `chroma_key(out, out, key=key)` 로 바꾼다:

```python
    key = scene_key_color(out_base, sid, scene_image)["key"]
```

`generate_background_layer` 도 같은 방식으로 키 색을 읽어 `_run_codex_image` 호출을 `_run_fal_image` 로 바꾼다. 배경은 키잉하지 않으므로 프롬프트 문구는 그대로 두고 호출만 교체한다:

```python
        res = _run_fal_image(proj_dir, out, prompt, images=[scene_image])
```

- [ ] **Step 4: 테스트 통과 확인**

먼저 **분리 경로를 가짜로 바꾸던 기존 테스트의 대상**을 옮긴다. `_run_codex_image` 를 패치하는 곳 중 **레이어 분리 테스트만** `_run_fal_image` 로 바꾸고, 씬 이미지·캐릭터 생성 테스트는 그대로 둔다(그 경로는 codex 유지).

바꿀 곳 — `monkeypatch.setattr(ig, "_run_codex_image", fake_run_codex)` → `monkeypatch.setattr(ig, "_run_fal_image", fake_run_codex)`:
- `tests/test_imagegen.py::test_split_scene_to_elements` (약 223행)
- `tests/test_imagegen.py::test_split_normalizes_to_scene_size` (약 295행)

바꿀 곳 — `monkeypatch.setattr(imagegen, "_run_codex_image", _fake)` → `monkeypatch.setattr(imagegen, "_run_fal_image", _fake)`:
- `tests/test_layer_edit.py::test_regenerate_background_uses_remaining_names` (약 89행)
- `tests/test_layer_edit.py::test_regenerate_element_only_touches_that_layer` (약 115행)

그대로 두는 곳(codex 경로 유지):
- `test_generate_one_attaches_base`, `test_generate_one_with_character_ref_order`, `test_generate_character_attaches_base`, `test_run_codex_image_classifies_rate_limit`

가짜 함수의 시그니처는 `(proj_dir, out, prompt, images=None, post=None)` 으로 맞춘다. `_run_fal_image` 는 `retries`·`size` 를 받지 않으므로, 기존 가짜가 `**kw` 로 받고 있으면 수정이 필요 없다.

또한 `test_layer_edit.py` 의 두 테스트는 `chroma_key_magenta` 를 패치하는데, 요소 생성이 이제 `chroma_key(o, o, key=key)` 를 부르므로 패치 대상을 `chroma_key` 로 바꾸고 가짜 시그니처에 `key=None` 을 추가한다.

Run: `python3 -m pytest tests/test_layer_keycolor.py tests/test_layer_edit.py tests/test_imagegen.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py tests/test_layer_keycolor.py tests/test_layer_edit.py
git commit -m "feat(layers): 분리 경로를 fal로 전환 + 프롬프트에 선택된 키 컬러 반영"
```

---

### Task 4: 레이어 예산 — 요소 4 + 배경 1

**Files:**
- Modify: `backend/imagegen.py` (`analyze_scene_layers` 반환부)
- Test: `tests/test_layer_budget.py`

**Interfaces:**
- Produces:
  - `MAX_ELEMENTS: int` = `4`
  - `apply_element_budget(elements: list) -> dict` — `{"elements": [...최대 4], "dropped": [...]}`
  - `analyze_scene_layers(...) -> dict` — 반환에 `dropped` 키 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_layer_budget.py`:

```python
import json

from backend import imagegen


def _els(n):
    return [{"name": f"el{i}", "location": "loc", "kind": "object", "reason": "r"} for i in range(n)]


def test_budget_keeps_first_four_in_priority_order():
    """분석 프롬프트가 이미 우선순위(캐릭터 > 가리는 전경 > 필요한 소품) 순으로 주므로 앞에서 자른다."""
    res = imagegen.apply_element_budget(_els(6))
    assert [e["name"] for e in res["elements"]] == ["el0", "el1", "el2", "el3"]
    assert [e["name"] for e in res["dropped"]] == ["el4", "el5"]
    assert imagegen.MAX_ELEMENTS == 4


def test_budget_passes_through_when_under_limit():
    res = imagegen.apply_element_budget(_els(3))
    assert len(res["elements"]) == 3 and res["dropped"] == []


def test_budget_handles_empty():
    res = imagegen.apply_element_budget([])
    assert res["elements"] == [] and res["dropped"] == []


def test_analyze_applies_budget(tmp_path, monkeypatch):
    """씬당 최대 5레이어 = 요소 4 + 배경 1."""
    out_json = tmp_path / ".layer_analysis.json"

    def _fake_run(prompt, proj_dir, **kw):
        out_json.write_text(json.dumps({"elements": _els(6)}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(imagegen.llm, "run_orchestrator", _fake_run)
    res = imagegen.analyze_scene_layers(tmp_path, str(tmp_path / "scene.png"))
    assert len(res["elements"]) == 4
    assert len(res["dropped"]) == 2


def test_background_prompt_excludes_only_kept_elements(tmp_path, monkeypatch):
    """잘린 요소는 배경에 남아야 하므로 제거 목록에서 빠진다."""
    seen = {}
    monkeypatch.setattr(imagegen, "_run_fal_image",
                        lambda proj_dir, out, prompt, images=None, post=None:
                            (seen.__setitem__("prompt", prompt),
                             Path(out).write_bytes(b"\x89PNG"),
                             {"status": "completed", "path": str(out)})[2])
    monkeypatch.setattr(imagegen, "load_style", lambda: "STYLE")
    monkeypatch.setattr(imagegen, "_scene_size", lambda p: None)
    base = tmp_path / "layers"
    base.mkdir()
    imagegen.generate_background_layer(tmp_path, str(tmp_path / "s.png"), "ab",
                                       ["el0", "el1", "el2", "el3"], out_base=base)
    assert "el3" in seen["prompt"] and "el4" not in seen["prompt"]
```

파일 맨 위에 `from pathlib import Path` 를 추가한다.

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_layer_budget.py -q`
Expected: FAIL — `AttributeError: module 'backend.imagegen' has no attribute 'apply_element_budget'`

- [ ] **Step 3: 구현**

`backend/imagegen.py` 의 `analyze_scene_layers` 위에 추가한다:

```python
MAX_ELEMENTS = 4        # 씬당 요소 레이어 상한. 배경 1장을 더해 최대 5레이어.


def apply_element_budget(elements: list) -> dict:
    """요소를 MAX_ELEMENTS개로 자른다. 분석 프롬프트가 이미 우선순위 순으로 주므로 앞에서 취한다.
    잘린 것은 dropped로 함께 돌려준다 — 패널이 '예산 초과로 제외'를 보여주고,
    배경 프롬프트는 채택된 것만 제거 대상으로 삼는다(잘린 요소는 배경에 남아야 한다)."""
    els = list(elements or [])
    return {"elements": els[:MAX_ELEMENTS], "dropped": els[MAX_ELEMENTS:]}
```

`analyze_scene_layers` 의 마지막 줄을 바꾼다:

```python
    return {**apply_element_budget(data.get("elements", []))}
```

그리고 실패 반환 두 곳에도 `dropped` 를 넣어 호출부가 키를 항상 기대할 수 있게 한다:

```python
        return {"error": "분석 실패", "elements": [], "dropped": []}
```

```python
        return {"error": "분석 결과 파싱 실패", "elements": [], "dropped": []}
```

라우터가 `dropped` 를 패널로 흘리도록 `backend/router.py` 의 `/api/scenes/analyze-layers` 반환을 바꾼다:

```python
        return 200, {"job_id": jid, "elements": res.get("elements", []),
                     "dropped": res.get("dropped", []), "error": res.get("error")}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_layer_budget.py tests/test_router.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py backend/router.py tests/test_layer_budget.py
git commit -m "feat(layers): 씬당 요소 4개 상한 + 초과분 dropped 반환"
```

---

### Task 5: 패널 모달 — dropped 표시 + 체크 4개 상한

**Files:**
- Modify: `cep/com.autokairos.pd/js/storyboard.js` (`_renderLayerPane`, `analyzeLayers` 의 `.then`)
- Modify: `cep/com.autokairos.pd/index.html` (`.layer-dropped` 스타일)
- Test: `tests/test_panel_structure.py` (추가)

**Interfaces:**
- Consumes: `/api/scenes/analyze-layers` 응답의 `elements`, `dropped`
- Produces: 없음(패널 내부)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_panel_structure.py` 에 이어붙인다:

```python
def test_layer_modal_shows_budget():
    """씬당 요소 4개 상한 — 초과분은 '예산 초과로 제외'로 보이고 체크는 4개까지."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "MAX_LAYER_ELEMENTS" in js and "= 4" in js
    assert "layer-dropped" in js
    assert "예산 초과" in js
    assert "_enforceLayerCap" in js
    html = HTML.read_text(encoding="utf-8")
    assert ".layer-dropped" in html
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_panel_structure.py::test_layer_modal_shows_budget -q`
Expected: FAIL — `AssertionError`

- [ ] **Step 3: 구현**

`cep/com.autokairos.pd/js/storyboard.js` 에서 `_renderLayerPane` 를 교체하고 위에 상수·헬퍼를 추가한다:

```javascript
/* 씬당 요소 레이어 상한 — 배경 1장을 더해 최대 5레이어(백엔드 MAX_ELEMENTS와 같은 값). */
var MAX_LAYER_ELEMENTS = 4;

/* 체크 개수를 상한으로 묶는다 — 상한에 닿으면 꺼진 체크박스를 잠근다. */
function _enforceLayerCap(pane) {
  var chks = pane.querySelectorAll('input[type="checkbox"]');
  var on = 0, i;
  for (i = 0; i < chks.length; i++) if (chks[i].checked) on++;
  for (i = 0; i < chks.length; i++) chks[i].disabled = (!chks[i].checked && on >= MAX_LAYER_ELEMENTS);
  var note = pane.querySelector(".layer-cap-note");
  if (note) note.textContent = on + "/" + MAX_LAYER_ELEMENTS + " 선택 (배경 1장이 자동으로 더해집니다)";
}

function _renderLayerPane(n, els, err, dropped) {
  var pane = $("layerList").querySelector('.layer-pane[data-scene="' + n + '"]');
  if (!pane) return;
  if (!els.length) {
    pane.innerHTML = '<div style="color:#e74c3c;padding:8px">씬 ' + n + ' 분석 실패: ' + _esc(err || "") + '</div>';
    return;
  }
  function row(e, i, off) {
    var tag = e.kind === "character" ? "👤 인물" : "📦 사물";
    return '<label class="layer-chk' + (off ? " layer-dropped" : "") + '">'
      + '<input type="checkbox" data-idx="' + i + '"' + (off ? "" : " checked") + (off ? " disabled" : "") + '>'
      + '<span><b>' + tag + '</b> ' + _esc(e.name)
      + ' <span style="color:#9aa0a6">(' + _esc(e.location) + ')</span>'
      + (off ? ' <span style="color:#e8b339">예산 초과로 제외</span>' : '')
      + (e.reason ? '<br><span style="font-size:10px;color:#9aa0a6">' + _esc(e.reason) + '</span>' : '')
      + '</span></label>';
  }
  var html = '<div class="layer-cap-note" style="font-size:11px;color:#9aa0a6;padding:4px 2px"></div>';
  html += els.map(function (e, i) { return row(e, i, false); }).join("");
  html += (dropped || []).map(function (e, i) { return row(e, els.length + i, true); }).join("");
  pane.innerHTML = html;
  var chks = pane.querySelectorAll('input[type="checkbox"]');
  for (var c = 0; c < chks.length; c++) {
    chks[c].addEventListener("change", function () { _enforceLayerCap(pane); });
  }
  _enforceLayerCap(pane);
}
```

`analyzeLayers` 의 성공 콜백에서 `dropped` 를 넘기고 상태 문구에 반영한다:

```javascript
      .then(function (j) {
        var els = j.elements || [], dropped = j.dropped || [];
        _layerMulti[n] = { els: els.concat(dropped), done: true };
        _renderLayerPane(n, els, j.error, dropped);
        _rowStatus(n, els.length
          ? (els.length + "개 요소 분석됨" + (dropped.length ? " (+" + dropped.length + "개 예산 초과)" : ""))
          : ("분석 실패: " + (j.error || "")));
        _updateLayerModalStatus();
      })
```

실패 콜백의 `_renderLayerPane(n, [], String(e))` 는 그대로 둔다(마지막 인자 없으면 `dropped` 가 `undefined` → `(dropped || [])` 가 받는다).

`cep/com.autokairos.pd/index.html` 의 `#layerTabs` 스타일 근처에 추가한다:

```css
    .layer-chk.layer-dropped { opacity:0.55; }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_panel_structure.py -q && node --check cep/com.autokairos.pd/js/storyboard.js`
Expected: PASS + 문법 오류 없음

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 레이어 모달에 예산 초과 표시 + 체크 4개 상한"
```

---

### Task 6: 설정·문서 + 전체 회귀

**Files:**
- Modify: `.env.example`
- Modify: `/Users/jleavens_macmini/CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: `.env.example` 에 키 추가**

기존 내용 끝에 한 줄 추가:

```
FAL_KEY=
```

- [ ] **Step 2: `CLAUDE.md` 에 예외 명시**

`/Users/jleavens_macmini/CLAUDE.md` 의 "# 이미지 생성 규칙" 항목 끝에 추가한다:

```markdown
- **예외 — 레이어 분리**: 씬 이미지를 요소별 투명 레이어로 쪼개는 작업(`backend/imagegen.py` 의 레이어 분리 경로)은 fal `xai/grok-imagine-image/v2.0/edit` 를 쓴다. 이 경로만 예외이고, 씬 이미지·캐릭터 생성 등 나머지 이미지 생성은 codex `$imagegen` 전용 규칙을 그대로 따른다.
```

- [ ] **Step 3: README에 키 요구사항 한 줄**

`README.md` 끝에 추가한다:

```markdown
환경 키: `OPENAI_API_KEY`(codex 이미지), `ELEVENLABS_API_KEY`(TTS), `FAL_KEY`(레이어 분리).
```

- [ ] **Step 4: 전체 회귀 실행**

Run:
```bash
python3 -m pytest tests/ -q \
  --ignore=tests/test_research_web_smoke.py \
  --ignore=tests/test_research_web_agent.py \
  --ignore=tests/test_research_news.py \
  --ignore=tests/test_research_lanes_basic.py
```
Expected: PASS — 이전 626개 + 이번 신규분. 실패가 있으면 그 테스트가 `_run_codex_image` 를 가짜로 바꾸고 있는지 확인하고 `_run_fal_image` 로 대상을 바꾼다.

- [ ] **Step 5: 커밋**

```bash
git add .env.example README.md
git commit -m "docs(fal): FAL_KEY 설정 + 레이어 분리 예외 명시"
```

---

## 사람이 직접 확인해야 하는 것

자동 테스트는 fal 호출을 전부 가짜로 대체한다. 아래는 자동으로 검증할 수 없다.

1. `.env` 에 실제 `FAL_KEY` 를 넣고 씬 하나를 분리해 **요소가 원위치·원크기로 뽑히는지**.
2. data URI 입력이 실제로 받아들여지는지. 거부되면 fal 스토리지 업로드 경로를 `fal_api.py` 에 추가해야 한다(설계 시점에 문서가 429로 막혀 확인하지 못했다).
3. 마젠타가 많은 씬에서 그린 키잉이 실제로 더 깨끗한지.
4. `resolution="2k"` 출력이 1920×1080 씬에서 비율 검사를 통과하는지 — 자주 재시도가 걸리면 `aspect_ratio` 파라미터를 함께 보내는 것을 검토한다.
