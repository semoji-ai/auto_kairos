# 씬 분할 기능 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스토리보드 씬 상세 패널에서 씬을 두 개로 나누고, TTS 재생성 + AI 재분석을 자동 실행한다.

**Architecture:** sceneId(UUID)를 도입해 식별자와 순서를 분리. 분할은 1단계(즉시: 구조 변경+파일 rename)와 2단계(백그라운드: TTS+씬분석)로 나뉜다. 레거시 프로젝트(sceneId 없음)는 sceneNumber 폴백으로 호환 유지.

**Tech Stack:** Python/FastAPI, asyncio, SQLite, Jinja2 HTML, Vanilla JS, ElevenLabs API, Claude CLI

---

## 파일 구조

| 역할 | 파일 |
|------|------|
| sceneId 유틸 | `auto_agent/tools/scene_id.py` (신규) |
| 분할 로직 | `auto_agent/tools/scene_split.py` (신규) |
| image_assets sceneId 지원 | `auto_agent/tools/image_assets.py` (수정) |
| audio_assets sceneId 지원 | `auto_agent/tools/audio_assets.py` (수정) |
| 분할 API 엔드포인트 | `auto_agent/dashboard/scene_editor.py` (수정) |
| 백그라운드 TTS+분석 | `app.py` (수정) |
| 마이그레이션 스크립트 | `auto_agent/scripts/migrate_scene_ids.py` (신규) |
| 분할 UI | `auto_agent/dashboard/templates/partials/_storyboard_scene.html` (수정) |

---

## Task 1: sceneId 유틸 모듈

**Files:**
- Create: `auto_agent/tools/scene_id.py`
- Test: `tests/tools/test_scene_id.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/tools/test_scene_id.py
import pytest
from auto_agent.tools.scene_id import new_scene_id, get_scene_id, ensure_scene_ids

def test_new_scene_id_is_8char_hex():
    sid = new_scene_id()
    assert len(sid) == 8
    assert all(c in "0123456789abcdef" for c in sid)

def test_new_scene_id_unique():
    assert new_scene_id() != new_scene_id()

def test_get_scene_id_returns_existing():
    scene = {"sceneId": "abc12345", "sceneNumber": 1}
    assert get_scene_id(scene) == "abc12345"

def test_get_scene_id_fallback_to_none_for_number():
    scene = {"sceneNumber": 3}
    assert get_scene_id(scene) is None

def test_ensure_scene_ids_adds_missing():
    scenes = [{"sceneNumber": 1}, {"sceneNumber": 2, "sceneId": "existing1"}]
    result = ensure_scene_ids(scenes)
    assert result[0]["sceneId"] is not None
    assert len(result[0]["sceneId"]) == 8
    assert result[1]["sceneId"] == "existing1"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd /Volumes/jleavens/Projects/auto_kairos_v3
.venv/bin/python3.12 -m pytest tests/tools/test_scene_id.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'auto_agent.tools.scene_id'`

- [ ] **Step 3: 구현**

```python
# auto_agent/tools/scene_id.py
"""씬 고유 식별자(sceneId) 유틸."""
import uuid


def new_scene_id() -> str:
    """8자리 hex UUID 생성."""
    return uuid.uuid4().hex[:8]


def get_scene_id(scene: dict) -> str | None:
    """씬에서 sceneId 반환. 없으면 None."""
    return scene.get("sceneId") or None


def ensure_scene_ids(scenes: list[dict]) -> list[dict]:
    """sceneId 없는 씬에 신규 UUID 부여 (원본 수정)."""
    for scene in scenes:
        if not scene.get("sceneId"):
            scene["sceneId"] = new_scene_id()
    return scenes
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
.venv/bin/python3.12 -m pytest tests/tools/test_scene_id.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/scene_id.py tests/tools/test_scene_id.py
git commit -m "feat: sceneId 유틸 모듈 추가"
```

---

## Task 2: image_assets / audio_assets sceneId 지원

**Files:**
- Modify: `auto_agent/tools/image_assets.py`
- Modify: `auto_agent/tools/audio_assets.py`
- Test: `tests/tools/test_assets_scene_id.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/tools/test_assets_scene_id.py
import json, pytest
from pathlib import Path
from auto_agent.tools.image_assets import _get_scene as img_get_scene, _load as img_load, _save as img_save
from auto_agent.tools.audio_assets import _get_scene as audio_get_scene, _load as audio_load, _save as audio_save

def _make_img_dir(tmp_path, scenes_data):
    d = tmp_path / "images"
    d.mkdir()
    (d / "image_assets.json").write_text(json.dumps({"scenes": scenes_data}))
    return d

def test_image_get_scene_by_scene_id(tmp_path):
    img_dir = _make_img_dir(tmp_path, [
        {"sceneId": "abc12345", "sceneNumber": 5, "images": []}
    ])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=5, scene_id="abc12345")
    assert scene["sceneId"] == "abc12345"

def test_image_get_scene_fallback_no_scene_id(tmp_path):
    # sceneId 없는 레거시 데이터
    img_dir = _make_img_dir(tmp_path, [
        {"sceneNumber": 3, "images": []}
    ])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=3, scene_id=None)
    assert scene["sceneNumber"] == 3

def test_image_get_scene_creates_new_with_scene_id(tmp_path):
    img_dir = _make_img_dir(tmp_path, [])
    data = img_load(img_dir)
    scene = img_get_scene(data, scene_num=10, scene_id="newid123")
    assert scene["sceneId"] == "newid123"
    assert scene["sceneNumber"] == 10
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
.venv/bin/python3.12 -m pytest tests/tools/test_assets_scene_id.py -v 2>&1 | head -20
```

Expected: `TypeError: _get_scene() got unexpected keyword argument 'scene_id'`

- [ ] **Step 3: image_assets.py `_get_scene` 수정**

`auto_agent/tools/image_assets.py`의 `_get_scene` 함수를 찾아 수정:

```python
def _get_scene(data: dict, scene_num: int, scene_id: str | None = None) -> dict:
    # sceneId 우선 조회
    if scene_id:
        for s in data["scenes"]:
            if s.get("sceneId") == scene_id:
                return s
    # sceneNumber 폴백
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    # 신규 생성
    scene: dict = {"sceneNumber": scene_num, "images": []}
    if scene_id:
        scene["sceneId"] = scene_id
    data["scenes"].append(scene)
    data["scenes"].sort(key=lambda x: x["sceneNumber"])
    return scene
```

- [ ] **Step 4: audio_assets.py `_get_scene` 동일 패턴 수정**

`auto_agent/tools/audio_assets.py`의 `_get_scene` 함수를 찾아 수정:

```python
def _get_scene(data: dict, scene_num: int, scene_id: str | None = None) -> dict:
    if scene_id:
        for s in data["scenes"]:
            if s.get("sceneId") == scene_id:
                return s
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s
    scene: dict = {"sceneNumber": scene_num, "versions": []}
    if scene_id:
        scene["sceneId"] = scene_id
    data["scenes"].append(scene)
    data["scenes"].sort(key=lambda x: x["sceneNumber"])
    return scene
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
.venv/bin/python3.12 -m pytest tests/tools/test_assets_scene_id.py -v
```

Expected: 3 passed

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/tools/image_assets.py auto_agent/tools/audio_assets.py tests/tools/test_assets_scene_id.py
git commit -m "feat: image_assets/audio_assets sceneId 우선 조회 지원"
```

---

## Task 3: scene_split 핵심 로직

**Files:**
- Create: `auto_agent/tools/scene_split.py`
- Test: `tests/tools/test_scene_split.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/tools/test_scene_split.py
import json, shutil
import pytest
from pathlib import Path
from auto_agent.tools.scene_split import split_narration_by_sentence, renumber_files, apply_split_to_specs

def test_split_narration_half():
    narration = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다."
    a, b = split_narration_by_sentence(narration)
    assert a.strip() != ""
    assert b.strip() != ""
    assert "첫 번째" in a
    assert "네 번째" in b

def test_split_narration_single_sentence():
    narration = "하나의 문장만 있습니다."
    a, b = split_narration_by_sentence(narration)
    assert a == narration
    assert b == ""

def test_apply_split_inserts_new_scene():
    specs = {
        "scenes": [
            {"sceneNumber": 1, "sceneId": "id000001", "narration": "씬 1"},
            {"sceneNumber": 2, "sceneId": "id000002", "narration": "씬 2 앞부분. 씬 2 뒷부분."},
            {"sceneNumber": 3, "sceneId": "id000003", "narration": "씬 3"},
        ]
    }
    result = apply_split_to_specs(specs, scene_num=2, narration_a="씬 2 앞부분.", narration_b="씬 2 뒷부분.")
    scenes = result["scenes"]
    assert len(scenes) == 4
    assert scenes[1]["sceneNumber"] == 2
    assert scenes[1]["narration"] == "씬 2 앞부분."
    assert scenes[1]["sceneId"] == "id000002"  # 기존 sceneId 유지
    assert scenes[2]["sceneNumber"] == 3
    assert scenes[2]["narration"] == "씬 2 뒷부분."
    assert scenes[2]["sceneId"] != "id000002"  # 새 sceneId
    assert scenes[3]["sceneNumber"] == 4  # 기존 씬3 → 씬4
    assert scenes[3]["sceneId"] == "id000003"  # sceneId 불변

def test_apply_split_legacy_no_scene_id():
    specs = {
        "scenes": [
            {"sceneNumber": 1, "narration": "씬 1"},
            {"sceneNumber": 2, "narration": "씬 2 앞. 씬 2 뒤."},
        ]
    }
    result = apply_split_to_specs(specs, scene_num=2, narration_a="씬 2 앞.", narration_b="씬 2 뒤.")
    assert len(result["scenes"]) == 3
    assert result["scenes"][2]["narration"] == "씬 2 뒤."

def test_renumber_files(tmp_path):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "scene_003.mp3").write_bytes(b"audio3")
    (audio_dir / "scene_004.mp3").write_bytes(b"audio4")
    renumber_files(tmp_path, from_scene=3, is_legacy=True)
    assert (audio_dir / "scene_004.mp3").read_bytes() == b"audio3"
    assert (audio_dir / "scene_005.mp3").read_bytes() == b"audio4"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
.venv/bin/python3.12 -m pytest tests/tools/test_scene_split.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'auto_agent.tools.scene_split'`

- [ ] **Step 3: scene_split.py 구현**

```python
# auto_agent/tools/scene_split.py
"""씬 분할 핵심 로직."""
import re
import copy
from pathlib import Path
from auto_agent.tools.scene_id import new_scene_id


def split_narration_by_sentence(narration: str) -> tuple[str, str]:
    """나레이션을 문장 단위로 절반 분할. 문장이 하나면 (전체, "") 반환."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', narration.strip()) if s.strip()]
    if len(sentences) <= 1:
        return narration, ""
    mid = max(1, len(sentences) // 2)
    a = " ".join(sentences[:mid])
    b = " ".join(sentences[mid:])
    return a, b


def apply_split_to_specs(specs: dict, scene_num: int, narration_a: str, narration_b: str) -> dict:
    """scene_specs 딕셔너리에 씬 분할을 적용한다. 원본을 수정하지 않고 새 dict 반환."""
    result = copy.deepcopy(specs)
    scenes = result["scenes"]

    # 대상 씬 찾기
    target_idx = next((i for i, s in enumerate(scenes) if s["sceneNumber"] == scene_num), None)
    if target_idx is None:
        raise ValueError(f"sceneNumber {scene_num} not found")

    # 원본 씬 수정 (narration_a, sceneId 유지)
    original = scenes[target_idx]
    original["narration"] = narration_a
    original.pop("narration_tts", None)
    original.pop("subtitle_lines", None)
    original.pop("subtitle_lines_tts", None)
    original.pop("tts_changes", None)

    # 새 씬 생성 (narration_b, 신규 sceneId)
    new_scene = copy.deepcopy(original)
    new_scene["sceneId"] = new_scene_id()
    new_scene["narration"] = narration_b
    new_scene["imageAsset"] = {
        "source": original.get("imageAsset", {}).get("source", "generate"),
        "prompt": "",
        "placement": "fullscreen",
        "opacity": 1.0,
    }
    new_scene.pop("narration_tts", None)
    new_scene.pop("subtitle_lines", None)
    new_scene.pop("subtitle_lines_tts", None)
    new_scene.pop("tts_changes", None)

    # num+1 이후 씬 sceneNumber +1
    for scene in scenes[target_idx + 1:]:
        scene["sceneNumber"] += 1

    # 새 씬 삽입 (target_idx+1 위치)
    new_scene["sceneNumber"] = scene_num + 1
    scenes.insert(target_idx + 1, new_scene)

    return result


def renumber_files(out_dir: Path, from_scene: int, is_legacy: bool) -> None:
    """레거시 프로젝트: from_scene 이후 파일들을 역순으로 +1 rename."""
    if not is_legacy:
        return

    audio_dir = out_dir / "audio"
    subtitles_dir = out_dir / "subtitles"
    img_gen_dir = out_dir / "images" / "generated"
    img_search_dir = out_dir / "images" / "search"

    # 최대 씬 번호 파악
    max_n = from_scene
    if audio_dir.exists():
        for f in audio_dir.glob("scene_*.mp3"):
            try:
                n = int(f.stem.split("_")[1])
                max_n = max(max_n, n)
            except (IndexError, ValueError):
                pass

    # 역순 rename으로 충돌 방지
    for n in range(max_n, from_scene - 1, -1):
        # audio
        if audio_dir.exists():
            src = audio_dir / f"scene_{n:03d}.mp3"
            if src.exists():
                src.rename(audio_dir / f"scene_{n+1:03d}.mp3")
        # subtitles
        if subtitles_dir.exists():
            src = subtitles_dir / f"scene_{n:03d}.json"
            if src.exists():
                src.rename(subtitles_dir / f"scene_{n+1:03d}.json")
        # generated images
        if img_gen_dir.exists():
            for f in list(img_gen_dir.glob(f"scene_{n:03d}_*.png")) + list(img_gen_dir.glob(f"scene_{n:03d}_*.jpg")):
                new_name = f.name.replace(f"scene_{n:03d}_", f"scene_{n+1:03d}_")
                f.rename(f.parent / new_name)
        # search images
        if img_search_dir.exists():
            for f in list(img_search_dir.glob(f"scene_{n:03d}_*.png")) + list(img_search_dir.glob(f"scene_{n:03d}_*.jpg")):
                new_name = f.name.replace(f"scene_{n:03d}_", f"scene_{n+1:03d}_")
                f.rename(f.parent / new_name)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
.venv/bin/python3.12 -m pytest tests/tools/test_scene_split.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/scene_split.py tests/tools/test_scene_split.py
git commit -m "feat: scene_split 핵심 로직 구현"
```

---

## Task 4: 분할 API 엔드포인트

**Files:**
- Modify: `auto_agent/dashboard/scene_editor.py`

- [ ] **Step 1: scene_editor.py 하단에 split 엔드포인트 추가**

`auto_agent/dashboard/scene_editor.py` 마지막 함수 뒤에 추가:

```python
@router.post("/scenes/{scene_num}/split")
async def split_scene(slug: str, scene_num: int, request: Request):
    """씬 분할 — 1단계(즉시): 구조 변경 + 파일 rename + 매니페스트 재빌드."""
    import json as _json
    from datetime import datetime
    from auto_agent.tools.scene_split import apply_split_to_specs, renumber_files
    from auto_agent.tools.image_assets import _load as ia_load, _save as ia_save

    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)

    out_dir = project.get("output_dir", "")
    body = await request.json()
    narration_a = (body.get("narration_a") or "").strip()
    narration_b = (body.get("narration_b") or "").strip()

    if not narration_a or not narration_b:
        return JSONResponse({"error": "narration_a, narration_b 모두 필요합니다"}, status_code=400)

    specs_path = Path(out_dir) / "scene_specs.json"
    if not specs_path.exists():
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    specs = _json.loads(specs_path.read_text(encoding="utf-8"))
    target = next((s for s in specs.get("scenes", []) if s["sceneNumber"] == scene_num), None)
    if not target:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    # 레거시 여부: sceneId가 없는 씬이 있으면 레거시
    is_legacy = not target.get("sceneId")

    # 백업
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(out_dir) / f"scene_specs.bak.{ts}.json"
    bak.write_text(specs_path.read_text(encoding="utf-8"), encoding="utf-8")

    # 분할 적용
    new_specs = apply_split_to_specs(specs, scene_num, narration_a, narration_b)
    new_scene_num = scene_num + 1
    new_scene = next(s for s in new_specs["scenes"] if s["sceneNumber"] == new_scene_num)
    new_scene_id = new_scene.get("sceneId", "")

    # image_assets sceneNumber 동기화
    img_dir = Path(out_dir) / "images"
    if img_dir.exists() and (img_dir / "image_assets.json").exists():
        ia = ia_load(img_dir)
        for s in ia.get("scenes", []):
            if s["sceneNumber"] >= new_scene_num and not s.get("sceneId"):
                s["sceneNumber"] += 1
        ia_save(img_dir, ia)

    # video_assets sceneNumber 동기화
    va_path = Path(out_dir) / "video_assets.json"
    if va_path.exists():
        va = _json.loads(va_path.read_text(encoding="utf-8"))
        for s in va.get("scenes", []):
            if s.get("sceneNumber", 0) >= new_scene_num and not s.get("sceneId"):
                s["sceneNumber"] += 1
        va_path.write_text(_json.dumps(va, ensure_ascii=False, indent=2), encoding="utf-8")

    # 레거시 파일 rename
    renumber_files(Path(out_dir), from_scene=new_scene_num, is_legacy=is_legacy)

    # scene_specs 저장
    specs_path.write_text(_json.dumps(new_specs, ensure_ascii=False, indent=2), encoding="utf-8")

    # 매니페스트 재빌드
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        dir_name = Path(out_dir).name
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        print(f"[WARN] 분할 후 매니페스트 리빌드 실패: {e}")

    return JSONResponse({
        "status": "splitting",
        "scene_a": scene_num,
        "scene_b": new_scene_num,
        "scene_b_id": new_scene_id,
    })
```

- [ ] **Step 2: 수동 동작 확인**

대시보드가 실행 중인지 확인 (`curl http://localhost:8080/` 응답 오면 OK).
없으면: `.venv/bin/python3.12 -m uvicorn app:app --host 0.0.0.0 --port 8080` 백그라운드 실행.

```bash
curl -s -X POST "http://localhost:8080/api/p/포켓몬스터_30주년_브랜드백과사전_1편/editor/scenes/3/split" \
  -H "Content-Type: application/json" \
  -d '{"narration_a":"앞부분 나레이션.","narration_b":"뒷부분 나레이션."}' | python3.12 -m json.tool
```

Expected:
```json
{"status": "splitting", "scene_a": 3, "scene_b": 4, "scene_b_id": "xxxxxxxx"}
```

- [ ] **Step 3: 백업 파일 생성 확인**

```bash
ls /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.bak.*.json | tail -1
```

- [ ] **Step 4: 씬 수 증가 확인 후 롤백**

```bash
python3.12 -c "
import json
specs = json.load(open('/Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json'))
print('총 씬 수:', len(specs['scenes']))
"
```

확인 후 백업으로 복원:

```bash
BAK=$(ls /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.bak.*.json | tail -1)
cp "$BAK" /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json
.venv/bin/python3.12 -m auto_agent.scripts.build_manifest --local output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/scene_editor.py
git commit -m "feat: 씬 분할 API 엔드포인트 추가"
```

---

## Task 5: 백그라운드 TTS + 씬 재분석

**Files:**
- Modify: `app.py`

- [ ] **Step 1: app.py에 백그라운드 분할 처리 함수 추가**

`app.py` 상단 import 근처 (기존 `regenerate_tts` 함수 아래) 에 추가:

```python
async def _bg_split_postprocess(slug: str, project: dict, scene_a: int, scene_b: int):
    """분할 후 백그라운드 처리: 양쪽 씬 TTS 재생성 + 씬 재분석."""
    import asyncio as _asyncio
    out_dir = project.get("output_dir", "")

    async def _process_one(scene_num: int):
        specs_path = Path(out_dir) / "scene_specs.json"
        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        scene = next((s for s in specs.get("scenes", []) if s["sceneNumber"] == scene_num), None)
        if not scene:
            return

        narration = scene.get("narration", "")

        # 1. TTS 재생성
        try:
            config = project.get("config", {})
            if isinstance(config, str):
                config = json.loads(config)
            STYLE_VOICE = {
                "semoji": "W7FnAxJNpD5WGjrF5GLp",
                "iromism": "9Sj8ugvpK1DmcAXyvi3a",
                "default": "4JJwo477JUAx3HV0T7n7",
            }
            voice_id = config.get("voice_id") or STYLE_VOICE.get(config.get("writing_style", "default"), STYLE_VOICE["default"])

            import requests as _requests
            from auto_agent.tools.audio_assets import add_version as audio_add, next_filename as audio_next
            audio_dir = Path(out_dir) / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            fname = audio_next(audio_dir, scene_num)
            output_path = audio_dir / fname

            voice_settings = {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": True}
            resp = _requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", ""), "Content-Type": "application/json"},
                json={"text": narration, "model_id": "eleven_multilingual_v2", "voice_settings": voice_settings},
                timeout=60,
            )
            if resp.status_code == 200:
                output_path.write_bytes(resp.content)
                audio_add(audio_dir, scene_num, fname, "split_tts", voice_id=voice_id, text=narration[:100])
            # 자막 동기화
            subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.generate_subtitles", out_dir, "--scene", str(scene_num)],
                cwd=str(get_workspace_dir()), capture_output=True, timeout=120,
            )
        except Exception as e:
            print(f"[WARN] 분할 TTS 실패 씬{scene_num}: {e}")

        # 2. 씬 재분석 (script-director)
        try:
            scene_ctx = json.dumps(scene, ensure_ascii=False, indent=2)
            prompt = f"""아래 씬의 연출을 다시 검토하고 개선하세요.
씬 번호, 나레이션, 챕터는 변경하지 마세요.
layout, mood, imageAsset, motion, title, concept, headline/items 등 연출 요소 전체를 개선합니다.

현재 씬:
{scene_ctx}

반드시 씬 전체를 JSON으로만 응답하세요 (설명 없이 JSON만).
"""
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            result = subprocess.run(
                ["claude", "--model", "claude-sonnet-4-6", "--max-turns", "3",
                 "--output-format", "text", "--no-ansi"],
                input=prompt, capture_output=True, text=True, env=env,
                cwd=str(get_workspace_dir()), timeout=180,
            )
            raw = (result.stdout or "").strip()
            if "```" in raw:
                lines = raw.split("\n")
                start = 1 if lines[0].strip().startswith("```") else 0
                end = -1 if lines[-1].strip() == "```" else len(lines)
                raw = "\n".join(lines[start:end]).strip()
            updated = json.loads(raw)
            # scene_specs 업데이트
            specs2 = json.loads(specs_path.read_text(encoding="utf-8"))
            for i, s in enumerate(specs2.get("scenes", [])):
                if s["sceneNumber"] == scene_num:
                    # sceneId, sceneNumber, narration 유지
                    updated["sceneId"] = s.get("sceneId", updated.get("sceneId"))
                    updated["sceneNumber"] = scene_num
                    updated["narration"] = s["narration"]
                    specs2["scenes"][i] = updated
                    break
            specs_path.write_text(json.dumps(specs2, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] 분할 씬재분석 실패 씬{scene_num}: {e}")

    # 양쪽 씬 병렬 처리
    await _asyncio.gather(_process_one(scene_a), _process_one(scene_b))

    # 매니페스트 재빌드
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        dir_name = Path(out_dir).name
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        print(f"[WARN] 분할 백그라운드 매니페스트 리빌드 실패: {e}")

    print(f"[SPLIT] 백그라운드 처리 완료: 씬{scene_a}, 씬{scene_b}")
```

- [ ] **Step 2: scene_editor.py의 split 엔드포인트에서 백그라운드 태스크 시작하도록 수정**

`auto_agent/dashboard/scene_editor.py`의 `split_scene` 함수에서 `return JSONResponse(...)` 직전에 추가:

```python
    # 백그라운드 태스크 시작
    import asyncio as _asyncio
    from app import _bg_split_postprocess
    _asyncio.create_task(_bg_split_postprocess(slug, project, scene_num, new_scene_num))
```

- [ ] **Step 3: 수동 동작 확인**

```bash
curl -s -X POST "http://localhost:8080/api/p/포켓몬스터_30주년_브랜드백과사전_1편/editor/scenes/3/split" \
  -H "Content-Type: application/json" \
  -d '{"narration_a":"앞부분.","narration_b":"뒷부분."}' | python3.12 -m json.tool
```

30초 후 오디오 파일 생성 확인:

```bash
ls /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/audio/ | grep "scene_003\|scene_004" 
```

확인 후 백업으로 복원:

```bash
BAK=$(ls /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.bak.*.json | tail -1)
cp "$BAK" /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json
.venv/bin/python3.12 -m auto_agent.scripts.build_manifest --local output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

- [ ] **Step 4: 커밋**

```bash
git add app.py auto_agent/dashboard/scene_editor.py
git commit -m "feat: 분할 백그라운드 TTS+씬재분석 처리 추가"
```

---

## Task 6: 분할 UI

**Files:**
- Modify: `auto_agent/dashboard/templates/partials/_storyboard_scene.html`

- [ ] **Step 1: 씬 분할 버튼 추가**

`_storyboard_scene.html`에서 씬 상세 헤더 액션 버튼 영역을 찾아 (기존 "재연출" 버튼 근처) 추가:

```html
<button class="btn btn-sm" onclick="openSplitEditor(slug, sceneNum)" style="background:rgba(245,158,11,0.15);color:#F59E0B;border-color:rgba(245,158,11,0.3)">✂️ 씬 분할</button>
```

- [ ] **Step 2: 분할 편집기 HTML 추가**

씬 상세 패널 내 (나레이션 표시 영역 아래) 에 추가:

```html
<div id="split-editor" style="display:none;margin-top:16px;border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:16px;background:rgba(245,158,11,0.05)">
  <div style="font-size:12px;color:#F59E0B;font-weight:600;margin-bottom:8px">✂️ 씬 분할</div>
  <label style="font-size:11px;color:var(--text-muted)">앞 씬 나레이션</label>
  <textarea id="split-narration-a" rows="4" style="width:100%;margin-top:4px;margin-bottom:12px;background:rgba(0,0,0,0.3);color:var(--text-primary);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px;font-size:13px;resize:vertical"></textarea>
  <div style="text-align:center;font-size:11px;color:#F59E0B;margin-bottom:12px">── 분할선 ──</div>
  <label style="font-size:11px;color:var(--text-muted)">뒷 씬 나레이션</label>
  <textarea id="split-narration-b" rows="4" style="width:100%;margin-top:4px;margin-bottom:16px;background:rgba(0,0,0,0.3);color:var(--text-primary);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px;font-size:13px;resize:vertical"></textarea>
  <div style="display:flex;gap:8px;justify-content:flex-end">
    <button class="btn btn-sm" onclick="closeSplitEditor()" style="background:rgba(255,255,255,0.05)">취소</button>
    <button class="btn btn-sm" onclick="executeSplit()" style="background:rgba(245,158,11,0.2);color:#F59E0B;border-color:rgba(245,158,11,0.4);font-weight:600">분할 실행</button>
  </div>
</div>
```

- [ ] **Step 3: 분할 JS 함수 추가**

`_storyboard_scene.html` `<script>` 섹션에 추가:

```javascript
function openSplitEditor(slug, sceneNum) {
  var narration = document.querySelector('.scene-narration-text')?.textContent || '';
  // 문장 단위 절반 분할
  var sentences = narration.trim().split(/(?<=[.!?。])\s+/).filter(Boolean);
  var mid = Math.max(1, Math.floor(sentences.length / 2));
  document.getElementById('split-narration-a').value = sentences.slice(0, mid).join(' ');
  document.getElementById('split-narration-b').value = sentences.slice(mid).join(' ');
  document.getElementById('split-editor').style.display = 'block';
  document.getElementById('split-editor').scrollIntoView({behavior: 'smooth'});
}

function closeSplitEditor() {
  document.getElementById('split-editor').style.display = 'none';
}

function executeSplit() {
  var a = document.getElementById('split-narration-a').value.trim();
  var b = document.getElementById('split-narration-b').value.trim();
  if (!a || !b) {
    alert('앞 씬과 뒷 씬 나레이션을 모두 입력해주세요.');
    return;
  }
  var btn = document.querySelector('#split-editor button:last-child');
  btn.textContent = '처리 중...';
  btn.disabled = true;

  fetch('/api/p/' + encodeURIComponent(slug) + '/editor/scenes/' + sceneNum + '/split', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({narration_a: a, narration_b: b})
  })
  .then(function(r) { return r.json(); })
  .then(function(res) {
    if (res.status === 'splitting') {
      closeSplitEditor();
      // 스토리보드 갱신
      if (window.clearManifestCache) window.clearManifestCache(null, {refreshDetail: false});
      alert('씬 분할 완료! 씬 ' + res.scene_a + '와 씬 ' + res.scene_b + '에 TTS+분석이 진행 중입니다.');
    } else {
      alert('오류: ' + (res.error || JSON.stringify(res)));
      btn.textContent = '분할 실행';
      btn.disabled = false;
    }
  })
  .catch(function(e) {
    alert('요청 실패: ' + e);
    btn.textContent = '분할 실행';
    btn.disabled = false;
  });
}
```

- [ ] **Step 4: 브라우저에서 동작 확인**

1. `http://localhost:8080` 열기
2. 포켓몬스터 1편 프로젝트 → 스토리보드 탭
3. 임의의 씬 클릭 → 상세 패널에서 "✂️ 씬 분할" 버튼 확인
4. 버튼 클릭 → 분할 편집기 표시, textarea에 나레이션 자동 분할 확인
5. "취소" 클릭 → 편집기 닫힘 확인

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/templates/partials/_storyboard_scene.html
git commit -m "feat: 씬 분할 UI 추가"
```

---

## Task 7: 마이그레이션 스크립트

**Files:**
- Create: `auto_agent/scripts/migrate_scene_ids.py`

- [ ] **Step 1: 마이그레이션 스크립트 작성**

```python
# auto_agent/scripts/migrate_scene_ids.py
"""기존 프로젝트 scene_specs에 sceneId 일괄 부여."""
import argparse, json, sys
from pathlib import Path
from auto_agent.paths import get_workspace_dir
from auto_agent.tools.scene_id import new_scene_id


def migrate(project_dir: str):
    out = Path(project_dir) if Path(project_dir).is_absolute() else get_workspace_dir() / "output" / project_dir
    specs_path = out / "scene_specs.json"
    if not specs_path.exists():
        print(f"[ERROR] scene_specs.json 없음: {specs_path}")
        sys.exit(1)

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    added = 0
    for scene in specs.get("scenes", []):
        if not scene.get("sceneId"):
            scene["sceneId"] = new_scene_id()
            added += 1

    # image_assets.json에 sceneId 추가
    ia_path = out / "images" / "image_assets.json"
    if ia_path.exists():
        ia = json.loads(ia_path.read_text(encoding="utf-8"))
        scene_id_map = {s["sceneNumber"]: s.get("sceneId") for s in specs["scenes"]}
        for entry in ia.get("scenes", []):
            sn = entry.get("sceneNumber")
            if sn and not entry.get("sceneId") and scene_id_map.get(sn):
                entry["sceneId"] = scene_id_map[sn]
        ia_path.write_text(json.dumps(ia, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  image_assets.json sceneId 동기화 완료")

    # video_assets.json에 sceneId 추가
    va_path = out / "video_assets.json"
    if va_path.exists():
        va = json.loads(va_path.read_text(encoding="utf-8"))
        for entry in va.get("scenes", []):
            sn = entry.get("sceneNumber")
            if sn and not entry.get("sceneId") and scene_id_map.get(sn):
                entry["sceneId"] = scene_id_map[sn]
        va_path.write_text(json.dumps(va, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  video_assets.json sceneId 동기화 완료")

    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DONE] {added}개 씬에 sceneId 부여 완료: {specs_path.parent.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="프로젝트 slug 또는 절대경로")
    args = parser.parse_args()
    migrate(args.project)
```

- [ ] **Step 2: 포켓몬스터 1편에 마이그레이션 실행**

```bash
cd /Volumes/jleavens/Projects/auto_kairos_v3
.venv/bin/python3.12 -m auto_agent.scripts.migrate_scene_ids \
  --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

Expected:
```
[DONE] 84개 씬에 sceneId 부여 완료: 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

- [ ] **Step 3: sceneId 적용 확인**

```bash
.venv/bin/python3.12 -c "
import json
specs = json.load(open('/Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json'))
has_id = sum(1 for s in specs['scenes'] if s.get('sceneId'))
print(f'sceneId 있는 씬: {has_id}/{len(specs[\"scenes\"])}')
print('샘플:', specs['scenes'][0]['sceneId'], '씬', specs['scenes'][0]['sceneNumber'])
"
```

Expected: `sceneId 있는 씬: 84/84`

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/scripts/migrate_scene_ids.py
git commit -m "feat: sceneId 마이그레이션 스크립트 + 포켓몬스터 1편 마이그레이션 적용"
```

---

## Task 8: 전체 통합 테스트

- [ ] **Step 1: 씬 3 분할 전체 흐름 테스트**

```bash
# 씬 3 나레이션 확인
.venv/bin/python3.12 -c "
import json
specs = json.load(open('/Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json'))
s = next(x for x in specs['scenes'] if x['sceneNumber'] == 3)
print('씬3 sceneId:', s['sceneId'])
print('씬3 나레이션:', s['narration'][:80])
print('총 씬 수:', len(specs['scenes']))
"
```

- [ ] **Step 2: 분할 API 호출**

```bash
curl -s -X POST "http://localhost:8080/api/p/포켓몬스터_30주년_브랜드백과사전_1편/editor/scenes/3/split" \
  -H "Content-Type: application/json" \
  -d '{"narration_a":"첫 번째 나레이션 부분.","narration_b":"두 번째 나레이션 부분."}' \
  | python3.12 -m json.tool
```

- [ ] **Step 3: 결과 검증**

```bash
.venv/bin/python3.12 -c "
import json
specs = json.load(open('/Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json'))
print('총 씬 수 (85여야 함):', len(specs['scenes']))
s3 = next(x for x in specs['scenes'] if x['sceneNumber'] == 3)
s4 = next(x for x in specs['scenes'] if x['sceneNumber'] == 4)
print('씬3 narration:', s3['narration'])
print('씬3 sceneId:', s3['sceneId'])
print('씬4 narration:', s4['narration'])
print('씬4 sceneId:', s4['sceneId'])
print('씬3/씬4 sceneId 다름:', s3['sceneId'] != s4['sceneId'])
"
```

Expected: 총 씬 수 85, 씬3/씬4 sceneId 다름 True

- [ ] **Step 4: 복원**

```bash
BAK=$(ls /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.bak.*.json | tail -1)
cp "$BAK" /Volumes/jleavens/Projects/auto_kairos_v3/output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/scene_specs.json
.venv/bin/python3.12 -m auto_agent.scripts.build_manifest --local output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
echo "복원 완료"
```

- [ ] **Step 5: 최종 커밋**

```bash
git add -A
git commit -m "feat: 씬 분할 기능 완성 — sceneId, split API, UI, 마이그레이션"
```
