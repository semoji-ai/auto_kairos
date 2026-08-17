# 모션 학습 파이프라인 Phase A 구현 계획 (수집·분석·기법화)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 큐레이션 URL의 모션그래픽 영상을 yt-dlp로 수집하고, gemini 동영상이해로 컷·프리셋을 분석해 신규 프리셋 후보를 제안하며, 검토 승인분을 라이브러리에 머지한다.

**Architecture:** `scripts/motion_learn/` 패키지의 4 모듈(collect/analyze/merge_presets/state). collect는 yt-dlp로 refs/에 다운, analyze는 gemini로 motion.json+new_presets 산출, merge_presets는 검토 게이트로 라이브러리 확장, state는 진행 상태. 외부 도구(yt-dlp/gemini)는 subprocess/SDK로 호출하되 순수 로직(slug/머지/스키마)은 단위 테스트.

**Tech Stack:** Python(stdlib + google-genai), yt-dlp(CLI), JSON, pytest.

---

## 파일 구조

- Create: `scripts/motion_learn/__init__.py`
- Create: `scripts/motion_learn/state.py` — 레퍼런스별 진행 상태(state.json) 읽기/쓰기
- Create: `scripts/motion_learn/collect.py` — yt-dlp 다운 + slug + 메타
- Create: `scripts/motion_learn/analyze.py` — gemini 분석 → motion.json + new_presets
- Create: `scripts/motion_learn/merge_presets.py` — 후보 검토·머지(라이브러리 확장)
- Test: `tests/test_motion_learn.py`

테스트 실행: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`

---

## Task 1: state.py — 진행 상태

**Files:**
- Create: `scripts/motion_learn/__init__.py`, `scripts/motion_learn/state.py`
- Test: `tests/test_motion_learn.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_motion_learn.py`:
```python
import json
from pathlib import Path
from scripts.motion_learn import state


def test_state_roundtrip(tmp_path):
    ref = tmp_path / "abc123"
    state.set_stage(ref, "collected", {"title": "Test"})
    s = state.get_state(ref)
    assert s["stage"] == "collected" and s["title"] == "Test"
    state.set_stage(ref, "analyzed")
    assert state.get_state(ref)["stage"] == "analyzed"
    assert state.get_state(ref)["title"] == "Test"   # 기존 필드 보존


def test_state_missing(tmp_path):
    assert state.get_state(tmp_path / "none") == {}
```

- [ ] **Step 2: 실패 확인** — `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -v` → FAIL(ModuleNotFoundError)

- [ ] **Step 3: 구현** — `scripts/motion_learn/__init__.py`: (빈 파일)
`scripts/motion_learn/state.py`:
```python
"""레퍼런스별 진행 상태 — refs/{slug}/state.json. 멱등 단계 진행."""
from __future__ import annotations

import json
from pathlib import Path


def _path(ref_dir: Path) -> Path:
    return ref_dir / "state.json"


def get_state(ref_dir: Path) -> dict:
    fp = _path(ref_dir)
    if not fp.is_file():
        return {}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def set_stage(ref_dir: Path, stage: str, extra: dict | None = None) -> dict:
    """stage 갱신 + extra 병합(기존 필드 보존). 반환=새 상태."""
    ref_dir.mkdir(parents=True, exist_ok=True)
    s = get_state(ref_dir)
    s["stage"] = stage
    if extra:
        s.update(extra)
    _path(ref_dir).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_motion_learn.py -v` → 2 PASS

- [ ] **Step 5: 커밋**
```bash
git add scripts/motion_learn/__init__.py scripts/motion_learn/state.py tests/test_motion_learn.py
git commit -m "feat(motion-learn): 진행 상태 모듈(state)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: collect.py — yt-dlp 수집

**Files:**
- Create: `scripts/motion_learn/collect.py`
- Test: `tests/test_motion_learn.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가(yt-dlp는 monkeypatch로 모킹, 순수 로직만 검증):
```python
def test_slug_stable():
    from scripts.motion_learn import collect
    s1 = collect.slug_for("https://youtu.be/AbC123xyz")
    s2 = collect.slug_for("https://youtu.be/AbC123xyz")
    assert s1 == s2 and len(s1) == 12 and s1.isalnum()


def test_collect_skips_existing(tmp_path, monkeypatch):
    from scripts.motion_learn import collect
    calls = []
    monkeypatch.setattr(collect, "_run_ytdlp", lambda url, out: (calls.append(url), out.write_bytes(b"x"))[-1])
    monkeypatch.setattr(collect, "_probe_meta", lambda p: {"title": "T", "duration": 10.0, "width": 1920, "height": 1080})
    refs = tmp_path / "refs"
    r1 = collect.collect(["https://youtu.be/AbC123xyz"], refs)
    assert len(r1) == 1 and len(calls) == 1
    r2 = collect.collect(["https://youtu.be/AbC123xyz"], refs)   # 이미 받음 → 스킵
    assert len(calls) == 1 and r2[0]["slug"] == r1[0]["slug"]
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: 구현** — `scripts/motion_learn/collect.py`:
```python
"""큐레이션 URL → yt-dlp 다운 + 메타. 무삭제·멱등(slug 기준)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts.motion_learn import state


def slug_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _run_ytdlp(url: str, out: Path) -> None:
    subprocess.run(
        ["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]",
         "--merge-output-format", "mp4", "-o", str(out), url],
        check=True, capture_output=True, timeout=600)


def _probe_meta(path: Path) -> dict:
    import shutil
    if not shutil.which("ffprobe"):
        return {}
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration:format_tags=title",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    try:
        j = json.loads(r.stdout)
        st = (j.get("streams") or [{}])[0]
        fmt = j.get("format") or {}
        return {"width": st.get("width"), "height": st.get("height"),
                "duration": float(fmt.get("duration", 0) or 0)}
    except (json.JSONDecodeError, ValueError):
        return {}


def collect(urls: list[str], refs_dir: Path) -> list[dict]:
    """각 URL → refs/{slug}.mp4 + refs/{slug}/state.json. 반환 [{slug,path,...}]."""
    refs_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for url in urls:
        slug = slug_for(url)
        mp4 = refs_dir / (slug + ".mp4")
        ref_dir = refs_dir / slug
        if not mp4.exists():
            _run_ytdlp(url, mp4)
        meta = _probe_meta(mp4)
        meta["url"] = url
        state.set_stage(ref_dir, "collected", meta)
        out.append({"slug": slug, "path": str(mp4), **meta})
    return out
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_motion_learn.py -v` → PASS

- [ ] **Step 5: 커밋**
```bash
git add scripts/motion_learn/collect.py tests/test_motion_learn.py
git commit -m "feat(motion-learn): yt-dlp 수집 모듈(collect) — slug 멱등 + 메타

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: merge_presets.py — 후보 검토·머지

**Files:**
- Create: `scripts/motion_learn/merge_presets.py`
- Test: `tests/test_motion_learn.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_merge_presets(tmp_path):
    from scripts.motion_learn import merge_presets
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {"props": ["opacity"], "ease": "easeOut"}}}), encoding="utf-8")
    candidates = [
        {"name": "wipe_in", "props": ["trimEnd"], "ease": "easeInOut", "params": {}},
        {"name": "fade_scale_in", "props": ["opacity"], "ease": "easeOut"},   # 중복 → 스킵
        {"name": "particle_burst", "props": ["particles"], "ease": "easeOut"}  # 새 props → 빌더확장 플래그
    ]
    res = merge_presets.merge(lib, candidates, approved=["wipe_in", "fade_scale_in", "particle_burst"])
    d = json.loads(lib.read_text())
    assert "wipe_in" in d["presets"]                    # 신규 추가
    assert res["skipped_duplicate"] == ["fade_scale_in"]
    assert res["needs_builder"] == ["particle_burst"]   # 미지원 props → 플래그(추가는 하되 표시)
    assert "particle_burst" in d["presets"]


def test_merge_known_props_only():
    from scripts.motion_learn import merge_presets
    assert merge_presets.is_builder_supported({"props": ["opacity", "scale"]})
    assert not merge_presets.is_builder_supported({"props": ["particles"]})
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: 구현** — `scripts/motion_learn/merge_presets.py`:
```python
"""신규 프리셋 후보 → 라이브러리 머지(검토 게이트). 중복 스킵·무삭제.
빌더(build_from_json.jsx applyPreset)가 지원하는 props만 즉시 동작 — 그 외는 needs_builder 플래그."""
from __future__ import annotations

import json
from pathlib import Path

# P1 빌더 applyPreset이 다루는 props (이 외 props는 빌더 코드 확장 필요)
BUILDER_PROPS = {"opacity", "scale", "position", "rotationY", "trimEnd", "textOffset"}


def is_builder_supported(preset: dict) -> bool:
    return set(preset.get("props", [])) <= BUILDER_PROPS


def list_candidates(new_presets_path: Path) -> list[dict]:
    if not new_presets_path.is_file():
        return []
    try:
        return json.loads(new_presets_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def merge(lib_path: Path, candidates: list[dict], approved: list[str]) -> dict:
    """approved 이름의 후보를 lib_path(motion_presets.json)에 추가. 중복 이름은 스킵.
    반환 {added, skipped_duplicate, needs_builder}."""
    lib = json.loads(lib_path.read_text(encoding="utf-8"))
    presets = lib.setdefault("presets", {})
    added, dup, needs = [], [], []
    by_name = {c.get("name"): c for c in candidates}
    for name in approved:
        c = by_name.get(name)
        if not c:
            continue
        if name in presets:
            dup.append(name); continue
        entry = {k: c[k] for k in ("props", "ease", "params") if k in c}
        presets[name] = entry
        added.append(name)
        if not is_builder_supported(c):
            needs.append(name)
    lib_path.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"added": added, "skipped_duplicate": dup, "needs_builder": needs}
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_motion_learn.py -v` → PASS

- [ ] **Step 5: 커밋**
```bash
git add scripts/motion_learn/merge_presets.py tests/test_motion_learn.py
git commit -m "feat(motion-learn): 신규 프리셋 후보 검토·머지(merge_presets) — 중복스킵+빌더지원 플래그

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: analyze.py — gemini 분석

**Files:**
- Create: `scripts/motion_learn/analyze.py`
- Test: `tests/test_motion_learn.py` (추가 — gemini 호출은 monkeypatch)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_analyze_splits_output(tmp_path, monkeypatch):
    """gemini 응답(JSON)을 motion.json + new_presets.json으로 분리 저장."""
    from scripts.motion_learn import analyze, state
    refs = tmp_path / "refs"; ref = refs / "slug1"; ref.mkdir(parents=True)
    (refs / "slug1.mp4").write_bytes(b"x")
    state.set_stage(ref, "collected", {"url": "u"})
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {}}}), encoding="utf-8")
    fake = {"cuts": [{"type": "cut", "start": 0, "dur": 1, "layers": []}],
            "new_presets": [{"name": "wipe_in", "props": ["trimEnd"], "ease": "easeInOut"}]}
    monkeypatch.setattr(analyze, "_gemini_analyze", lambda mp4, lib_keys: fake)
    res = analyze.analyze("slug1", refs, lib)
    assert json.loads((ref / "motion.json").read_text())["cuts"][0]["dur"] == 1
    assert json.loads((ref / "new_presets.json").read_text())[0]["name"] == "wipe_in"
    assert state.get_state(ref)["stage"] == "analyzed"
    assert res["new_preset_count"] == 1
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: 구현** — `scripts/motion_learn/analyze.py`:
```python
"""gemini 동영상이해 → motion.json(컷·프리셋) + new_presets.json(신규 후보).
gemini는 기존 프리셋 카탈로그를 받아 가능한 건 매핑, 안 되는 건 후보 제안."""
from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.motion_learn import state


def _gemini_analyze(mp4_path: str, lib_keys: list[str]) -> dict:
    """gemini File API 업로드 + 분석. {cuts, new_presets} 반환. 모델 폴백."""
    from google import genai
    from google.genai import errors, types
    client = genai.Client()
    f = client.files.upload(file=mp4_path)
    while f.state.name == "PROCESSING":
        time.sleep(5); f = client.files.get(name=f.name)
    prompt = (
        "이 모션그래픽 영상을 After Effects 컴프로 재현할 JSON으로만 출력(순수 JSON).\n"
        "모션은 가능한 한 아래 기존 프리셋명으로 매핑: " + json.dumps(lib_keys, ensure_ascii=False) + "\n"
        "기존으로 표현 안 되는 모션은 new_presets에 후보로 제안: "
        "{name(snake_case), props(opacity/scale/position/rotationY/trimEnd/textOffset 우선), ease, params, why}.\n"
        "출력: {\"cuts\":[{type,start,dur,bg,layers:[{type,text,color,font,x,y,w,h,"
        "anim:[{preset,t0,dur,params}]}]}], \"new_presets\":[...]}\n순수 JSON만."
    )
    cfg = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000)
    last = None
    for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]:
        try:
            resp = client.models.generate_content(model=m, contents=[f, prompt], config=cfg)
            return json.loads(resp.text)
        except (errors.ServerError, json.JSONDecodeError) as e:
            last = e; continue
    raise RuntimeError("gemini 분석 실패: " + str(last))


def analyze(slug: str, refs_dir: Path, lib_path: Path) -> dict:
    """refs/{slug}.mp4 분석 → refs/{slug}/motion.json + new_presets.json. 반환 {cuts, new_preset_count}."""
    ref_dir = refs_dir / slug
    mp4 = refs_dir / (slug + ".mp4")
    lib_keys = list(json.loads(lib_path.read_text(encoding="utf-8")).get("presets", {}).keys())
    data = _gemini_analyze(str(mp4), lib_keys)
    cuts = data.get("cuts", [])
    new_presets = data.get("new_presets", [])
    (ref_dir / "motion.json").write_text(json.dumps({"cuts": cuts}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ref_dir / "new_presets.json").write_text(json.dumps(new_presets, ensure_ascii=False, indent=2), encoding="utf-8")
    state.set_stage(ref_dir, "analyzed", {"cut_count": len(cuts), "new_preset_count": len(new_presets)})
    return {"cuts": len(cuts), "new_preset_count": len(new_presets)}
```

- [ ] **Step 4: 통과 확인** — `... -m pytest tests/test_motion_learn.py -v` → 전체 PASS. 전체 스위트 `... -m pytest -q`.

- [ ] **Step 5: 커밋**
```bash
git add scripts/motion_learn/analyze.py tests/test_motion_learn.py
git commit -m "feat(motion-learn): gemini 분석 모듈(analyze) — motion.json + 신규 프리셋 후보 분리 저장

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: CLI 엔트리 + refs gitignore

**Files:**
- Create: `scripts/motion_learn/__main__.py` — CLI(collect/analyze/merge)
- Modify: `.gitignore` — refs/ 비추적
- Test: `tests/test_motion_learn.py` (추가)

- [ ] **Step 1: 실패 테스트** — 추가:
```python
def test_cli_help_lists_commands():
    """CLI가 collect/analyze/merge 서브커맨드를 제공."""
    import scripts.motion_learn.__main__ as cli
    p = cli.build_parser()
    sub = p._subparsers._group_actions[0].choices
    assert "collect" in sub and "analyze" in sub and "merge" in sub
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: 구현** — `scripts/motion_learn/__main__.py`:
```python
"""모션 학습 파이프라인 CLI (Phase A).
사용: python -m scripts.motion_learn collect --urls refs/urls.txt
      python -m scripts.motion_learn analyze --slug <slug>
      python -m scripts.motion_learn merge --slug <slug> --approve name1 name2"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "refs"
LIB = ROOT / "data" / "artstyle" / "motion" / "motion_presets.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="motion_learn")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--urls", required=True, help="URL 목록 파일(한 줄 1개)")
    a = sub.add_parser("analyze"); a.add_argument("--slug", required=True)
    m = sub.add_parser("merge"); m.add_argument("--slug", required=True); m.add_argument("--approve", nargs="*", default=[])
    sub.add_parser("candidates").add_argument("--slug", required=True)
    return p


def main(argv=None):
    from scripts.motion_learn import collect, analyze, merge_presets
    args = build_parser().parse_args(argv)
    if args.cmd == "collect":
        urls = [ln.strip() for ln in Path(args.urls).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        for r in collect.collect(urls, REFS):
            print("수집:", r["slug"], r.get("title", ""), r["path"])
    elif args.cmd == "analyze":
        r = analyze.analyze(args.slug, REFS, LIB)
        print(f"분석: 컷 {r['cuts']}, 신규 프리셋 후보 {r['new_preset_count']}개 → refs/{args.slug}/new_presets.json")
    elif args.cmd == "candidates":
        cands = merge_presets.list_candidates(REFS / args.slug / "new_presets.json")
        print(json.dumps(cands, ensure_ascii=False, indent=2))
    elif args.cmd == "merge":
        cands = merge_presets.list_candidates(REFS / args.slug / "new_presets.json")
        res = merge_presets.merge(LIB, cands, args.approve)
        print("머지:", res)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: refs gitignore + 통과 확인**
```bash
grep -q "^refs/" .gitignore || echo "
# 모션 학습 레퍼런스 영상(로컬, 내부 분석용)
refs/" >> .gitignore
```
Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_motion_learn.py -v` → PASS. CLI 구문: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m scripts.motion_learn --help` → collect/analyze/merge/candidates 표시. 전체 스위트 `... -m pytest -q`.

- [ ] **Step 5: 커밋**
```bash
git add scripts/motion_learn/__main__.py .gitignore tests/test_motion_learn.py
git commit -m "feat(motion-learn): CLI(collect/analyze/candidates/merge) + refs gitignore

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 6: 수동 E2E 안내(사용자)** — `refs/urls.txt`에 좋은 모션그래픽 URL 작성 → `python -m scripts.motion_learn collect --urls refs/urls.txt` → `analyze --slug <slug>` → `candidates --slug <slug>`로 후보 검토 → `merge --slug <slug> --approve <name>...`로 라이브러리 확장.

---

## 자기 검토 결과 (Self-Review)

- **스펙 커버리지**: §3.2 수집(Task 2), §3.3 분석(Task 4), §3.4 기법화 머지(Task 3), §3.5 상태(Task 1), CLI/체크포인트(Task 5). §3.6 테스트 각 Task 포함. B/C는 범위 밖(스펙 §4·5).
- **플레이스홀더**: 없음 — 모든 코드 실제 구현.
- **타입 일관성**: `state.set_stage(ref_dir, stage, extra)`/`get_state`(Task 1) → collect/analyze에서 동일 호출. `collect.collect(urls, refs_dir)→[{slug,...}]`, `analyze.analyze(slug, refs_dir, lib_path)→{cuts,new_preset_count}`, `merge_presets.merge(lib_path, candidates, approved)→{added,skipped_duplicate,needs_builder}`, `list_candidates(path)`·`is_builder_supported(preset)` 시그니처가 Task 정의 → Task 5 CLI에서 동일 사용. `_gemini_analyze(mp4, lib_keys)` monkeypatch 지점 일치.
- **미해결**: gemini/yt-dlp는 외부 호출이라 단위테스트는 monkeypatch. 실제 동작은 Task 5 Step 6 수동 E2E. BUILDER_PROPS는 P1 applyPreset 지원 props와 일치(opacity/scale/position/rotationY/trimEnd/textOffset).
