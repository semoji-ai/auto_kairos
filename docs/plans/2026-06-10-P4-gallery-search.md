# P4 — 갤러리 패널 + 이미지 검색 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 스토리보드 탭에 탐색기형 갤러리 패널을 추가한다 — 프로젝트 이미지/비디오 소스 열람, 이미지 검색(serper/pixabay), 결과 저장, 수동 이미지 생성, 그리고 갤러리 이미지를 시트 씬 행에 드래그→적용.

**Architecture:** 백엔드 stdlib `urllib`로 검색(키는 auto_kairos `.env`에서 로드). `env.py`(키 로더) + `search.py`(검색·다운로드) + `media.py`(프로젝트 미디어 목록). 라우터에 `/api/media`, `/api/search-images`, `/api/search-images/save`, `/api/scenes/set-image`. 패널 `gallery.js`가 탐색기·검색·드래그 적용. 이미지 무삭제(버전 생성), 경로 트래버설 방지.

**Tech Stack:** stdlib Python(urllib), pytest(HTTP는 monkeypatch), vanilla JS(CEP, HTML5 drag&drop), node 문법.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**확정 사실:** Serper `POST https://google.serper.dev/images` body `{"q","num"}` 헤더 `X-API-KEY`, 응답 `images[].{imageUrl,thumbnailUrl,title}`. Pixabay `GET https://pixabay.com/api/?key=&q=&per_page=&image_type=photo`, 응답 `hits[].{largeImageURL,webformatURL,previewURL,tags}`. 키: `SERPER_API_KEY`, `PIXABAY_API_KEY`. auto_kairos .env 경로: `AUTO_KAIROS_ENV` 또는 `LocalProjects/auto_kairos_v3/.env`. 무삭제 버전: `imagegen.versioned_path`.

---

## File Structure

- **Create** `backend/env.py` — auto_kairos .env 키 로더(`get_key`).
- **Create** `backend/search.py` — `search_images`(serper/pixabay), `save_image`(다운로드, 무삭제). HTTP 헬퍼 monkeypatch 가능.
- **Create** `backend/media.py` — `list_media`(프로젝트 이미지/비디오 목록), `set_scene_image`(소스→storyboard/sb_{n}.png 복사, 트래버설 방지, 무삭제).
- **Modify** `backend/router.py` — `/api/media`, `/api/search-images`, `/api/search-images/save`, `/api/scenes/set-image`.
- **Test** `tests/test_env.py`, `tests/test_search.py`, `tests/test_media.py`, `tests/test_router.py`.
- **Create** `cep/com.autokairos.pd/js/gallery.js` — 탐색기·검색·수동생성·드래그.
- **Modify** `cep/com.autokairos.pd/index.html` — 스토리보드 탭에 갤러리 패널, gallery.js 로드.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` — 시트 행을 드롭 타겟으로(set-image).
- **Modify** `tests/test_panel_structure.py` — 갤러리 패널 ID.

---

## Task 1: env.get_key — auto_kairos .env 키 로더

**Files:** Create `backend/env.py`; Test `tests/test_env.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_env.py`:

```python
from backend import env


def test_get_key_from_os_env(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "from-os")
    assert env.get_key("SERPER_API_KEY") == "from-os"


def test_get_key_from_file(monkeypatch, tmp_path):
    envf = tmp_path / ".env"
    envf.write_text('# 주석\nSERPER_API_KEY="file-key"\nPIXABAY_API_KEY=pix\n', encoding="utf-8")
    monkeypatch.setenv("AUTO_KAIROS_ENV", str(envf))
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    assert env.get_key("SERPER_API_KEY") == "file-key"   # 따옴표 제거
    assert env.get_key("PIXABAY_API_KEY") == "pix"


def test_get_key_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTO_KAIROS_ENV", str(tmp_path / "nope.env"))
    monkeypatch.delenv("ZZZ", raising=False)
    assert env.get_key("ZZZ") == ""
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_env.py -q` → FAIL.

- [ ] **Step 3: 구현** — `backend/env.py`:

```python
"""auto_kairos .env에서 API 키 로드 — os.environ 우선, 없으면 .env 파일 파싱."""
from __future__ import annotations

import os
from pathlib import Path


def kairos_env_path() -> Path | None:
    """AUTO_KAIROS_ENV 환경변수 → 없으면 LocalProjects/auto_kairos_v3/.env 후보."""
    p = os.environ.get("AUTO_KAIROS_ENV")
    if p:
        pp = Path(p).expanduser()
        return pp if pp.is_file() else None
    cand = Path(__file__).resolve().parents[2] / "auto_kairos_v3" / ".env"
    return cand if cand.is_file() else None


def _file_env() -> dict:
    fp = kairos_env_path()
    if not fp:
        return {}
    out: dict[str, str] = {}
    for line in fp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_key(name: str) -> str:
    """name 키 값. os.environ 우선, 없으면 auto_kairos .env. 없으면 ''."""
    return os.environ.get(name) or _file_env().get(name, "")
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_env.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/env.py tests/test_env.py
git commit -m "feat(backend): env.get_key — auto_kairos .env API 키 로더(os.environ 우선)"
```

---

## Task 2: search.search_images / save_image

**Files:** Create `backend/search.py`; Test `tests/test_search.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_search.py`:

```python
from backend import search


def test_search_serper(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY" if k == "SERPER_API_KEY" else "")
    monkeypatch.setattr(search, "_post_json",
        lambda url, payload, headers, timeout=20: {"images": [
            {"title": "차", "imageUrl": "http://x/a.jpg", "thumbnailUrl": "http://x/t.jpg"}]})
    res = search.search_images("전기차", engine="serper")
    assert res["images"][0]["url"] == "http://x/a.jpg"
    assert res["images"][0]["thumb"] == "http://x/t.jpg"
    assert res["images"][0]["source"] == "serper"


def test_search_pixabay(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY" if k == "PIXABAY_API_KEY" else "")
    monkeypatch.setattr(search, "_get_json",
        lambda url, timeout=20: {"hits": [
            {"tags": "car", "largeImageURL": "http://p/l.jpg", "previewURL": "http://p/p.jpg"}]})
    res = search.search_images("car", engine="pixabay")
    assert res["images"][0]["url"] == "http://p/l.jpg"
    assert res["images"][0]["source"] == "pixabay"


def test_search_missing_key(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "")
    res = search.search_images("x", engine="serper")
    assert "error" in res and res["images"] == []


def test_search_unknown_engine(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY")
    res = search.search_images("x", engine="bing")
    assert "error" in res


def test_save_image_downloads_versioned(monkeypatch, tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "images" / "search").mkdir(parents=True)
    (proj / "images" / "search" / "pic.jpg").write_bytes(b"old")  # 기존 → 버전 생성

    def fake_dl(url, dest, timeout=30):
        dest.write_bytes(b"\x89PNG")

    monkeypatch.setattr(search, "_download", fake_dl)
    res = search.save_image(proj, "http://x/a.jpg", "pic.jpg")
    assert res["status"] == "completed"
    assert res["rel"] == "images/search/pic_v2.jpg"      # 무삭제 버전
    assert (proj / "images" / "search" / "pic_v2.jpg").exists()
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_search.py -q` → FAIL.

- [ ] **Step 3: 구현** — `backend/search.py`:

```python
"""이미지 검색(serper/pixabay) + 다운로드(무삭제 버전). HTTP는 urllib(stdlib)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from backend import env
from backend.imagegen import versioned_path

SERPER_URL = "https://google.serper.dev/images"
PIXABAY_URL = "https://pixabay.com/api/"


def _post_json(url, payload, headers, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_json(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url, dest: Path, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        dest.write_bytes(r.read())


def search_images(query: str, engine: str = "serper", count: int = 12) -> dict:
    """{images:[{title,url,thumb,source}]} 또는 {error, images:[]}."""
    eng = (engine or "serper").lower()
    if eng == "serper":
        key = env.get_key("SERPER_API_KEY")
        if not key:
            return {"error": "SERPER_API_KEY 없음(auto_kairos .env)", "images": []}
        data = _post_json(SERPER_URL, {"q": query, "num": count},
                          {"X-API-KEY": key, "Content-Type": "application/json"})
        imgs = [{"title": i.get("title", ""), "url": i.get("imageUrl", ""),
                 "thumb": i.get("thumbnailUrl", i.get("imageUrl", "")), "source": "serper"}
                for i in data.get("images", [])[:count] if i.get("imageUrl")]
        return {"images": imgs}
    if eng == "pixabay":
        key = env.get_key("PIXABAY_API_KEY")
        if not key:
            return {"error": "PIXABAY_API_KEY 없음(auto_kairos .env)", "images": []}
        qs = urllib.parse.urlencode({"key": key, "q": query, "per_page": count,
                                     "image_type": "photo", "safesearch": "true"})
        data = _get_json(f"{PIXABAY_URL}?{qs}")
        imgs = [{"title": h.get("tags", ""),
                 "url": h.get("largeImageURL", h.get("webformatURL", "")),
                 "thumb": h.get("previewURL", h.get("webformatURL", "")), "source": "pixabay"}
                for h in data.get("hits", [])[:count] if h.get("webformatURL") or h.get("largeImageURL")]
        return {"images": imgs}
    return {"error": f"unknown engine: {engine}", "images": []}


def save_image(proj_dir: Path, url: str, name: str, subdir: str = "images/search") -> dict:
    """검색 결과 1장 다운로드 → proj/subdir/name (무삭제 버전)."""
    out_dir = proj_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = versioned_path(out_dir, Path(name).name)
    try:
        _download(url, dest)
    except Exception as e:  # 네트워크/URL 오류
        return {"status": "failed", "error": str(e)}
    return {"status": "completed", "path": str(dest),
            "rel": dest.relative_to(proj_dir).as_posix()}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_search.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/search.py tests/test_search.py
git commit -m "feat(backend): search.py — serper/pixabay 이미지 검색 + 다운로드(무삭제, urllib)"
```

---

## Task 3: media.list_media / set_scene_image

**Files:** Create `backend/media.py`; Test `tests/test_media.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_media.py`:

```python
from backend import media


def test_list_media(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "images").mkdir(); (p / "images" / "ref_1.png").write_bytes(b"\x89PNG")
    (p / "images" / "search").mkdir(); (p / "images" / "search" / "s.jpg").write_bytes(b"x")
    (p / "storyboard").mkdir(); (p / "storyboard" / "sb_1.png").write_bytes(b"x")
    (p / "video_sources").mkdir(); (p / "video_sources" / "v.mp4").write_bytes(b"x")
    items = media.list_media(p)
    rels = {i["rel"]: i["type"] for i in items}
    assert rels["images/ref_1.png"] == "image"
    assert rels["images/search/s.jpg"] == "image"
    assert rels["storyboard/sb_1.png"] == "image"
    assert rels["video_sources/v.mp4"] == "video"
    assert all(i["dir"] == str(p) for i in items)


def test_set_scene_image_copies_versioned(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "images").mkdir(); src = p / "images" / "pick.png"; src.write_bytes(b"\x89PNG")
    (p / "storyboard").mkdir(); (p / "storyboard" / "sb_2.png").write_bytes(b"old")  # 기존
    res = media.set_scene_image(p, 2, "images/pick.png")
    assert res["status"] == "completed"
    assert res["rel"] == "storyboard/sb_2_v2.png"   # 무삭제
    assert (p / "storyboard" / "sb_2_v2.png").read_bytes() == b"\x89PNG"


def test_set_scene_image_rejects_traversal(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    res = media.set_scene_image(p, 1, "../../etc/hosts")
    assert res["status"] == "failed"


def test_set_scene_image_missing_src(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    res = media.set_scene_image(p, 1, "images/nope.png")
    assert res["status"] == "failed"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_media.py -q` → FAIL.

- [ ] **Step 3: 구현** — `backend/media.py`:

```python
"""프로젝트 미디어 목록 + 갤러리→씬 이미지 적용(무삭제, 트래버설 방지)."""
from __future__ import annotations

import shutil
from pathlib import Path

from backend.imagegen import versioned_path

_IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VID_EXT = {".mp4", ".mov", ".webm", ".m4v"}
_MEDIA_DIRS = ["images", "images/search", "storyboard", "characters", "layers", "video_sources"]


def list_media(proj_dir: Path) -> list[dict]:
    """프로젝트 미디어 폴더의 이미지/비디오 파일 목록. [{name, rel, type, dir}]."""
    out: list[dict] = []
    for sub in _MEDIA_DIRS:
        d = proj_dir / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            kind = "image" if ext in _IMG_EXT else ("video" if ext in _VID_EXT else None)
            if not kind:
                continue
            out.append({"name": f.name, "rel": f.relative_to(proj_dir).as_posix(),
                        "type": kind, "dir": str(proj_dir)})
    return out


def set_scene_image(proj_dir: Path, scene_number, src_rel: str) -> dict:
    """proj/src_rel 이미지를 storyboard/sb_{n}.png 로 복사(무삭제 버전). 트래버설 방지."""
    src = (proj_dir / src_rel).resolve()
    if not src.is_relative_to(proj_dir.resolve()):
        return {"status": "failed", "error": "잘못된 경로"}
    if not src.is_file():
        return {"status": "failed", "error": f"소스 없음: {src_rel}"}
    sb = proj_dir / "storyboard"
    sb.mkdir(parents=True, exist_ok=True)
    dest = versioned_path(sb, f"sb_{scene_number}.png")
    shutil.copy(src, dest)
    return {"status": "completed", "path": str(dest),
            "rel": dest.relative_to(proj_dir).as_posix()}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_media.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/media.py tests/test_media.py
git commit -m "feat(backend): media.list_media + set_scene_image(갤러리→씬, 무삭제·트래버설 방지)"
```

---

## Task 4: 라우터 — media / search / save / set-image

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def test_media_list(tmp_path):
    proj = tmp_path / "p"; (proj / "images").mkdir(parents=True)
    (proj / "images" / "a.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/media", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["items"][0]["rel"] == "images/a.png"


def test_search_images_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    monkeypatch.setattr(r.search, "search_images",
                        lambda q, engine="serper", count=12: {"images": [{"url": "u", "thumb": "t", "title": "x", "source": engine}]})
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/search-images",
                                {"project_id": "p", "q": "전기차", "engine": "serper"}, None, ctx)
    assert code == 200 and body["images"][0]["url"] == "u"


def test_search_images_requires_query(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/search-images",
                                {"project_id": "p", "q": ""}, None, ctx)
    assert code == 400


def test_search_save_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    monkeypatch.setattr(r.search, "save_image",
                        lambda proj_dir, url, name, **kw: {"status": "completed", "rel": "images/search/x.jpg"})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/search-images/save", {},
                                {"project_id": "p", "url": "http://x/a.jpg", "name": "x.jpg"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"


def test_scene_set_image_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    monkeypatch.setattr(r.media, "set_scene_image",
                        lambda proj_dir, n, src: {"status": "completed", "rel": f"storyboard/sb_{n}.png"})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/set-image", {},
                                {"project_id": "p", "sceneNumber": 2, "src": "images/a.png"}, ctx)
    assert code == 200 and body["result"]["rel"] == "storyboard/sb_2.png"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → 새 5개 FAIL.

- [ ] **Step 3: 구현** — `router.py` import에 `search, media` 추가:
`from backend import projects, skills_cfg, sessions, pipeline, imagegen, scenes, search, media`

`/api/scenes/image` 블록 다음에 추가:

```python
    if method == "GET" and p == "/api/media":
        pid = query.get("project_id", "")
        return 200, {"items": media.list_media(root / pid)}

    if method == "GET" and p == "/api/search-images":
        pid = query.get("project_id", "")
        q = (query.get("q") or "").strip()
        if not (root / pid).is_dir():
            return 404, {"error": "프로젝트 없음"}
        if not q:
            return 400, {"error": "검색어 필요"}
        return 200, search.search_images(q, engine=query.get("engine", "serper"))

    if method == "POST" and p == "/api/search-images/save":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        url, name = b.get("url", ""), b.get("name", "")
        if not url or not name:
            return 400, {"error": "url, name 필요"}
        return 200, {"result": search.save_image(proj_dir, url, name)}

    if method == "POST" and p == "/api/scenes/set-image":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        return 200, {"result": media.set_scene_image(proj_dir, b.get("sceneNumber"), b.get("src", ""))}
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/media·/api/search-images(+save)·/api/scenes/set-image"
```

---

## Task 5: 패널 — 갤러리 패널 마크업 + 시트 드롭

**Files:** Modify `cep/com.autokairos.pd/index.html`, `cep/com.autokairos.pd/js/storyboard.js`; Modify `tests/test_panel_structure.py`

먼저 `index.html`의 스토리보드 탭과 `storyboard.js`의 `renderRow`/`bindRows`를 Read 한다.

- [ ] **Step 1: index.html — 시트 다음에 갤러리 패널 삽입** — `<div id="sheet">—</div>` 줄 뒤에 추가:

```html
        <div class="label">갤러리 / 소스</div>
        <div style="display:flex;gap:6px">
          <input id="galSearch" type="text" placeholder="이미지 검색어" style="flex:1;box-sizing:border-box;padding:7px;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
          <select id="galEngine" style="padding:6px;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
            <option value="serper">구글(serper)</option>
            <option value="pixabay">pixabay</option>
          </select>
          <button id="btnGalSearch" style="width:auto;padding:7px 12px;margin:0">검색</button>
        </div>
        <button id="btnGalRefresh">소스 새로고침</button>
        <div class="box" id="gallery-panel" style="min-height:40px">—</div>
```

- [ ] **Step 2: gallery.js 스크립트 추가** — `<script src="js/storyboard.js"></script>` 줄 뒤:

```html
  <script src="js/gallery.js"></script>
```

- [ ] **Step 3: storyboard.js — 시트 행을 드롭 타겟으로** — `renderRow`의 최상위 `<div class="box" ...>` 여는 태그에 `ondragover`/`ondrop` 훅을 추가. 즉 `renderRow` 반환의 첫 줄

```javascript
    + '<div class="box" style="display:block" data-scene="' + n + '">'
```

을

```javascript
    + '<div class="box scene-row" style="display:block" data-scene="' + n + '" ondragover="event.preventDefault()" ondrop="dropOnScene(event,' + n + ')">'
```

로 교체. 그리고 파일 끝에 드롭 핸들러 추가:

```javascript
function dropOnScene(ev, n) {
  ev.preventDefault();
  var src = ev.dataTransfer.getData("text/plain");
  if (!src) return;
  _rowStatus(n, "적용 중... (" + src + ")");
  fetch(BACKEND + "/api/scenes/set-image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n, src: src }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _rowStatus(n, (j.result && j.result.status === "completed") ? "적용됨 ✓" : ("실패: " + JSON.stringify(j)));
      if (j.result && j.result.status === "completed") loadSheet();
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}
```

- [ ] **Step 4: 구조 테스트 추가** — `tests/test_panel_structure.py` 끝에:

```python
def test_gallery_panel_present():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="gallery-panel"', 'id="galSearch"', 'id="galEngine"',
               'id="btnGalSearch"', 'id="btnGalRefresh"', 'src="js/gallery.js"']:
        assert el in html, el


def test_storyboard_js_has_drop_handler():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function dropOnScene" in js and "set-image" in js
```

- [ ] **Step 5: JS 문법 + 커밋**

```bash
node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/storyboard.js tests/test_panel_structure.py
git commit -m "feat(panel): 갤러리 패널 마크업 + 시트 행 드롭 타겟(set-image)"
```

---

## Task 6: gallery.js — 탐색기·검색·드래그·수동 생성

**Files:** Create `cep/com.autokairos.pd/js/gallery.js`

- [ ] **Step 1: gallery.js 작성**

```javascript
/* 갤러리 패널 — 프로젝트 미디어 탐색 + 검색(serper/pixabay) + 드래그→시트.
   BACKEND/$/SELECTED_PROJECT는 main.js 전역. */

function _gesc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function loadGallery() {
  if (!SELECTED_PROJECT) { $("gallery-panel").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery-panel").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/media?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var items = j.items || [];
      if (!items.length) { $("gallery-panel").textContent = "(소스 없음)"; return; }
      $("gallery-panel").innerHTML = items.map(function (it) {
        if (it.type === "image") {
          return '<img src="file://' + it.dir + '/' + it.rel + '" draggable="true"'
            + ' ondragstart="event.dataTransfer.setData(\'text/plain\', this.getAttribute(\'data-rel\'))"'
            + ' data-rel="' + _gesc(it.rel) + '" title="' + _gesc(it.rel) + ' — 시트 행으로 드래그"'
            + ' style="width:72px;height:auto;margin:3px;border-radius:4px;cursor:grab;">';
        }
        return '<span data-rel="' + _gesc(it.rel) + '" title="' + _gesc(it.rel) + '" style="display:inline-block;margin:3px;padding:6px;background:#23262b;border-radius:4px;font-size:11px;">🎬 ' + _gesc(it.name) + '</span>';
      }).join("");
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

function searchGallery() {
  if (!SELECTED_PROJECT) { $("gallery-panel").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var q = ($("galSearch").value || "").trim();
  if (!q) { $("gallery-panel").textContent = "검색어를 입력하세요."; return; }
  var engine = $("galEngine").value;
  $("gallery-panel").textContent = "검색 중... (" + engine + ")";
  fetch(BACKEND + "/api/search-images?project_id=" + encodeURIComponent(SELECTED_PROJECT) +
        "&q=" + encodeURIComponent(q) + "&engine=" + encodeURIComponent(engine))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { $("gallery-panel").textContent = "검색 오류: " + j.error; return; }
      var imgs = j.images || [];
      if (!imgs.length) { $("gallery-panel").textContent = "(결과 없음)"; return; }
      $("gallery-panel").innerHTML = imgs.map(function (im, idx) {
        return '<img src="' + _gesc(im.thumb) + '" data-url="' + _gesc(im.url) + '" data-idx="' + idx
          + '" title="클릭하면 소스로 저장: ' + _gesc(im.title) + '"'
          + ' style="width:72px;height:auto;margin:3px;border-radius:4px;cursor:pointer;">';
      }).join("");
      var gi = $("gallery-panel").querySelectorAll("img[data-url]");
      for (var i = 0; i < gi.length; i++) {
        gi[i].addEventListener("click", function () {
          saveSearchResult(this.getAttribute("data-url"), "search_" + this.getAttribute("data-idx") + ".jpg");
        });
      }
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

function saveSearchResult(url, name) {
  $("gallery-panel").innerHTML = "<div>저장 중... " + _gesc(name) + "</div>" + $("gallery-panel").innerHTML;
  fetch(BACKEND + "/api/search-images/save", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, url: url, name: name }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.result && j.result.status === "completed") loadGallery();  // 소스 목록 갱신
      else $("gallery-panel").textContent = "저장 실패: " + JSON.stringify(j);
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnGalRefresh").addEventListener("click", loadGallery);
  $("btnGalSearch").addEventListener("click", searchGallery);
});
```

- [ ] **Step 2: nav.js — 스토리보드 탭 진입 시 갤러리도 로드** — `switchTab`의 `if (!planning && typeof loadSheet === "function") loadSheet();` 다음 줄에 추가:

```javascript
  if (!planning && typeof loadGallery === "function") loadGallery();
```

- [ ] **Step 3: index.html — gallery.js가 storyboard.js 뒤에 로드되는지 확인** (Task 5 Step 2에서 추가됨). nav.js는 main 다음이므로 loadGallery는 클릭/탭 시 호출 → 안전.

- [ ] **Step 4: JS 문법** — `for f in main nav planning storyboard gallery; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK` → `ALL_OK`

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/js/gallery.js cep/com.autokairos.pd/js/nav.js
git commit -m "feat(panel): gallery.js — 미디어 탐색·검색(serper/pixabay)·결과 저장·드래그 소스, 탭 진입 시 로드"
```

---

## Task 7: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning storyboard gallery; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK` → `ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 스토리보드 탭 → 갤러리 패널에 프로젝트 소스 표시 → 검색어+엔진→[검색]→썸네일→클릭 저장 → 소스 이미지를 시트 씬 행에 드래그→적용(썸네일 갱신). (검색은 auto_kairos .env 키 필요.)

---

## Self-Review

- **스펙 커버리지(§3.2 갤러리 패널·드래그→적용·수동 생성·검색, §6 검색 serper/pixabay, §9 env/search/media)**: env(T1)+search(T2)+media(T3)+엔드포인트(T4)+갤러리 마크업/드롭(T5)+gallery.js(T6)로 충족. 수동 "이미지 생성"은 기존 시트 행의 [씬 이미지 생성](P3)·레퍼런스 [이미지 생성](기존) 재사용 — 갤러리 패널 전용 생성 버튼은 미추가(중복 회피, YAGNI). Unsplash는 .env 키 부재로 미구현(스펙 §14 — 키 추가 시 확장).
- **이미지 삭제 금지 준수**: save_image·set_scene_image 모두 `versioned_path`(무삭제). 트래버설 방지(set_scene_image resolve+is_relative_to).
- **Placeholder 없음**: 전 코드 완전. HTTP는 monkeypatch 가능한 `_post_json/_get_json/_download` 분리.
- **타입/ID 일관성**: search→`{images:[{title,url,thumb,source}]}|{error,images}`, /api/search-images 동일, gallery.js가 `j.images`/`im.url`/`im.thumb` 사용. media.list_media→`[{name,rel,type,dir}]`, /api/media→`{items:[...]}`, gallery.js `j.items`/`it.rel`/`it.type`/`it.dir`. set_scene_image→`{status,rel}`, /api/scenes/set-image→`{result}`, dropOnScene `j.result.status`. env.get_key 시그니처 일치.
- **로드 순서**: main→nav→planning→storyboard→gallery. dropOnScene는 storyboard.js(인라인 ondrop이 전역 함수 참조 — 클릭/드롭 시점엔 정의됨). loadGallery는 nav switchTab/버튼에서 호출.
