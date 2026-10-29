# 계획 1: 언어 중립 마스터 + 타임 워프 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코스트코(B209)의 한국어 원본에서 언어 중립 마스터(`master/edl.json`, `master/source.json`)를 만들고, 구간별 시간 변환표(타임 워프)를 AE 파트 컴프에 적용하는 엔진을 완성해, 인위적 변환으로 AE 결과가 정확히 늘고 줄어드는 것을 영상 대조로 증명한다.

**Architecture:** 순수 파이썬 패키지 `sg/`(시간 변환·EDL·그래프 순회·무음 분할)를 pytest로 TDD하고, CLI 스크립트(`scripts/master.py`, `scripts/timewarp.py`)가 B209 데이터를 만든다. AE 쪽은 `scripts/ae/localize.jsx` 하나가 파트 컴프마다 앵커 표를 받아 레이어 시간·키프레임·프리컴프를 재귀적으로 옮긴다. 검증은 aerender 렌더 + `scripts/compare_warped.py`(변환표로 시간을 맞춰 프레임 대조).

**Tech Stack:** Python 3(시스템 `python3`, numpy·PIL 사용자 site-packages), pytest 8, ffmpeg, After Effects 2026 ExtendScript, aerender.

**Spec:** `docs/superpowers/specs/2026-10-19-semoji-global-localization-design.md` (개정 2)

## Global Constraints

- 작업 폴더 `~/Projects/semoji_global` (git). 편 데이터 `episodes/B209/` — `src/`·`render/`·`build/`·영상 파일은 git 제외(.gitignore).
- NAS 원본은 절대 수정 금지. 모든 AE 작업은 `episodes/B209/src/B209_main_ko.aep`(로컬 사본, 파트 컴프 `MAIN_KO`/`MAIN_GAYOUNG`/`MAIN_GAEUL`, 폰트 매핑 완료)에서 하고 결과는 `build/`에 save_as.
- 마스터 시간 = 컷 적용 후(= 유튜브 시간). `pr_*` = 프리미어 시퀀스 시간(컷 적용 전). 유튜브 컷: `pr_in 914.3 ~ pr_out 923.3`.
- fps 29.97(30000/1001), 1920x1080.
- AE 실행은 `scripts/ae/run.sh <jsx 절대경로>`(잠금·정상 종료·캐시 정리), 렌더는 `scripts/ae/render.sh <aep> <comp> <in> <out> <out.mp4> 29.97 "H.264 - Match Render Settings - 15 Mbps"`. 한 번에 하나, 백그라운드 `&` 금지(도구의 백그라운드 실행은 가능).
- JSX: UTF-8 BOM, 객체 키 `in`/`out`은 따옴표, 직렬화는 `lib.jsx`의 `S()`, 메인 스크립트 첫 줄에서 `var SELF=$.fileName;`, 전체 try/catch 후 로그 JSON 기록.
- AE 작업 중 화면보호기 방지: `caffeinate -d -u -t 21600 &`(이미 떠 있으면 생략).
- 디스크 여유 10GB 미만이면 렌더 중단(render.sh가 검사).
- 테스트 실행: 저장소 루트에서 `python3 -m pytest -q`.
- 사용자에게 보이는 보고는 한글.

## Review Focus

1. 컷이 내레이션 구간 중간을 자르는 경우 — 조용히 틀린 앵커를 만들지 말고 `ValueError`로 멈춰야 함 (Task 2 테스트).
2. 한 파트가 프리미어에서 여러 클립으로 나뉘고 사이 소스가 건너뛰어진 경우(가을 파트) — 건너뛴 소스 구간은 길이 0으로 접혀야 함 (Task 3 테스트).
3. 같은 프리컴프가 여러 번 쓰이는 경우 — 한 번 쓰인 곳의 변환이 다른 곳에 새면 안 됨(복제 후 각각 변환) (Task 6 AE 검증 항목).
4. 레이어가 0초 이전에 시작하거나 컴프 끝을 넘는 경우, 변환 후 길이가 1프레임 미만이 되는 경우 — 기울기 1로 외삽하고, 0길이 레이어는 끔 (Task 1 외삽 테스트, Task 6 규칙).
5. 무음이 거의 없는 연속 내레이션(문장 사이 0.25초 미만) — 하나의 긴 구간으로 묶이더라도 자막 텍스트가 빠짐없이 붙어야 함 (Task 5 테스트).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `pytest.ini` | pytest가 저장소 루트를 import 경로로 쓰게 함 |
| `sg/__init__.py` | 패키지 표시 |
| `sg/timemap.py` | `PiecewiseMap` — 단조 구간별 선형 시간 변환, 자식 컴프 변환 유도, JSON 입출력 |
| `sg/warp.py` | `build_warp()` — 내레이션 구간·새 길이·컷 → `PiecewiseMap` |
| `sg/prproj.py` | 프리미어 XML 파싱(중첩 시퀀스 포함) — 기존 `scripts/parse_prproj.py` 로직 이전 |
| `sg/edl.py` | EDL 생성, 프리미어↔마스터↔파트 시간 변환, 파트별 앵커 유도 |
| `sg/graph.py` | AE 그래프(graph.jsx 출력) 순회 — 루트 컴프 기준 모든 레이어의 시간 구간 |
| `sg/audio.py` | wav 디코드, 무음 기준 말 구간 분할 |
| `sg/segments.py` | 말 구간 + 자막 텍스트 레이어 → 내레이션 구간(`segments`), 화면 문자열(`strings`) |
| `scripts/parse_prproj.py` | CLI 래퍼(sg.prproj 사용) |
| `scripts/reach.py` | CLI 래퍼(sg.graph 사용) |
| `scripts/master.py` | B209 마스터 생성 CLI |
| `scripts/timewarp.py` | 변환표 생성 CLI(`--test-pattern` 포함) → `build/<tag>/warp.json` + 파트 job |
| `scripts/compare_warped.py` | 변환표로 시간을 맞춘 두 영상 프레임 대조 |
| `scripts/ae/localize.jsx` | AE 타임 워프 엔진 |
| `tests/test_*.py` | 단위 테스트 |
| `docs/RUNBOOK.md` | 실행 순서 기록 |

---

### Task 1: 패키지 골격 + `PiecewiseMap`

**Files:**
- Create: `pytest.ini`, `sg/__init__.py`, `sg/timemap.py`
- Test: `tests/test_timemap.py`

**Interfaces:**
- Produces: `sg.timemap.PiecewiseMap(anchors: list[tuple[float,float]])`; `__call__(t: float) -> float`; `ratio(a: float, b: float) -> float`; `child(st_old: float, st_new: float, sx: float) -> PiecewiseMap`; `to_list() -> list[list[float]]`; `PiecewiseMap.identity() -> PiecewiseMap`. 앵커의 old는 순증가, new는 비감소(같아도 됨 = 접힘). 범위 밖은 기울기 1로 외삽.

- [ ] **Step 1: 실패하는 테스트 작성**

`pytest.ini`
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`tests/test_timemap.py`
```python
import pytest
from sg.timemap import PiecewiseMap


def test_identity():
    m = PiecewiseMap.identity()
    assert m(0) == 0 and m(12.5) == 12.5 and m(-3) == -3


def test_interpolation_and_extrapolation():
    m = PiecewiseMap([(0, 0), (10, 15), (20, 20)])
    assert m(5) == pytest.approx(7.5)
    assert m(15) == pytest.approx(17.5)
    assert m(-2) == pytest.approx(-2)      # 앞쪽 기울기 1
    assert m(25) == pytest.approx(25)      # 뒤쪽 기울기 1


def test_collapsed_segment_is_allowed():
    m = PiecewiseMap([(0, 0), (10, 10), (19, 10), (30, 21)])
    assert m(14) == pytest.approx(10)
    assert m(30) == pytest.approx(21)


def test_rejects_non_monotonic():
    with pytest.raises(ValueError):
        PiecewiseMap([(0, 0), (10, 8), (5, 9)])
    with pytest.raises(ValueError):
        PiecewiseMap([(0, 0), (10, 8), (20, 7)])


def test_ratio():
    m = PiecewiseMap([(0, 0), (10, 12)])
    assert m.ratio(0, 10) == pytest.approx(1.2)


def test_child_map_for_precomp_layer():
    # 부모 시간 t = st + u*sx. 레이어 startTime 2→3, stretch 50%
    m = PiecewiseMap([(0, 0), (10, 20)])
    c = m.child(st_old=2.0, st_new=3.0, sx=0.5)
    # 자식 u=4 → 부모 old 4 → new 8 → 자식 new (8-3)/0.5 = 10
    assert c(4) == pytest.approx(10)


def test_to_list_roundtrip():
    a = [(0.0, 0.0), (1.0, 2.0)]
    assert PiecewiseMap(a).to_list() == [[0.0, 0.0], [1.0, 2.0]]
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_timemap.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg'`

- [ ] **Step 3: 구현**

`sg/__init__.py`
```python
"""세모지 글로벌화 파이프라인 공용 모듈."""
```

`sg/timemap.py`
```python
"""구간별 선형 시간 변환. old 시각 → new 시각."""
from bisect import bisect_right


class PiecewiseMap:
    def __init__(self, anchors):
        pts = [(float(a), float(b)) for a, b in anchors]
        if not pts:
            raise ValueError("anchors empty")
        for (o0, n0), (o1, n1) in zip(pts, pts[1:]):
            if o1 <= o0:
                raise ValueError(f"old not strictly increasing: {o0} -> {o1}")
            if n1 < n0:
                raise ValueError(f"new decreasing: {n0} -> {n1}")
        self.pts = pts
        self._old = [p[0] for p in pts]

    @classmethod
    def identity(cls):
        return cls([(0.0, 0.0)])

    def __call__(self, t):
        p = self.pts
        if t <= p[0][0]:
            return p[0][1] + (t - p[0][0])
        if t >= p[-1][0]:
            return p[-1][1] + (t - p[-1][0])
        i = bisect_right(self._old, t) - 1
        (o0, n0), (o1, n1) = p[i], p[i + 1]
        return n0 + (n1 - n0) * (t - o0) / (o1 - o0)

    def ratio(self, a, b):
        return (self(b) - self(a)) / (b - a)

    def child(self, st_old, st_new, sx):
        """프리컴프 레이어(startTime st, stretch sx[배수])의 자식 컴프 시간 변환."""
        return PiecewiseMap([((o - st_old) / sx, (n - st_new) / sx) for o, n in self.pts])

    def to_list(self):
        return [[o, n] for o, n in self.pts]
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_timemap.py`
Expected: `7 passed`

- [ ] **Step 5: 커밋**
```bash
git add pytest.ini sg/__init__.py sg/timemap.py tests/test_timemap.py
git commit -m "feat: PiecewiseMap 시간 변환"
```

---

### Task 2: `build_warp` — 구간·새 길이·컷 → 변환표

**Files:**
- Create: `sg/warp.py`
- Test: `tests/test_warp.py`

**Interfaces:**
- Consumes: `PiecewiseMap` (Task 1)
- Produces: `sg.warp.build_warp(segments: list[dict], new_durs: dict[str,float], cuts: list[tuple[float,float]], length: float) -> PiecewiseMap`. `segments` 원소는 `{"id","in","out"}`(마스터 시간). `new_durs`에 없는 구간은 원래 길이 유지. 컷 안에 완전히 들어간 구간은 무시, 컷이 구간을 걸치면 `ValueError`. 구간 사이 간격은 원래 길이 유지.

- [ ] **Step 1: 실패하는 테스트**

`tests/test_warp.py`
```python
import pytest
from sg.warp import build_warp

SEG = [{"id": "a", "in": 1.0, "out": 4.0}, {"id": "b", "in": 5.0, "out": 9.0}]


def test_no_change_is_identity():
    m = build_warp(SEG, {}, [], 12.0)
    for t in (0, 1, 3, 4.5, 9, 12):
        assert m(t) == pytest.approx(t)


def test_longer_segment_shifts_rest():
    m = build_warp(SEG, {"a": 4.5}, [], 12.0)   # a: 3초 → 4.5초
    assert m(1.0) == pytest.approx(1.0)
    assert m(4.0) == pytest.approx(5.5)
    assert m(5.0) == pytest.approx(6.5)          # 간격 1초 유지
    assert m(9.0) == pytest.approx(10.5)
    assert m(12.0) == pytest.approx(13.5)


def test_cut_collapses_region():
    m = build_warp(SEG, {}, [(4.2, 4.8)], 12.0)
    assert m(4.2) == pytest.approx(m(4.8))
    assert m(12.0) == pytest.approx(11.4)


def test_segment_inside_cut_is_dropped():
    m = build_warp(SEG, {"b": 10.0}, [(4.5, 9.5)], 12.0)
    assert m(12.0) == pytest.approx(7.0)


def test_cut_crossing_segment_raises():
    with pytest.raises(ValueError):
        build_warp(SEG, {}, [(3.0, 4.5)], 12.0)


def test_overlapping_segments_raise():
    with pytest.raises(ValueError):
        build_warp([{"id": "a", "in": 1, "out": 4}, {"id": "b", "in": 3, "out": 6}], {}, [], 10)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_warp.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg.warp'`

- [ ] **Step 3: 구현**

`sg/warp.py`
```python
"""내레이션 구간의 새 길이와 컷으로 마스터 시간 변환표를 만든다."""
from sg.timemap import PiecewiseMap


def build_warp(segments, new_durs, cuts, length):
    cuts = sorted((float(a), float(b)) for a, b in cuts)
    segs = sorted(segments, key=lambda s: s["in"])
    for s0, s1 in zip(segs, segs[1:]):
        if s1["in"] < s0["out"]:
            raise ValueError(f"segments overlap: {s0['id']} / {s1['id']}")
    live = []
    for s in segs:
        inside = any(a <= s["in"] and s["out"] <= b for a, b in cuts)
        crossing = any(a < s["out"] and s["in"] < b for a, b in cuts) and not inside
        if crossing:
            raise ValueError(f"cut crosses segment {s['id']} [{s['in']},{s['out']}]")
        if not inside:
            live.append(s)
    # 이벤트: ('seg', in, out, newdur) / ('cut', a, b, 0)
    ev = [("seg", s["in"], s["out"], float(new_durs.get(s["id"], s["out"] - s["in"]))) for s in live]
    ev += [("cut", a, b, 0.0) for a, b in cuts]
    ev.sort(key=lambda e: e[1])
    anchors = [(0.0, 0.0)]
    old, new = 0.0, 0.0
    for kind, a, b, nd in ev:
        if a > old:                       # 사이 간격 유지
            new += a - old
            old = a
            anchors.append((old, new))
        if b <= old:
            continue
        new += nd if kind == "seg" else 0.0
        old = b
        anchors.append((old, new))
    if length > old:
        anchors.append((float(length), new + (length - old)))
    dedup = []
    for o, n in anchors:
        if dedup and o == dedup[-1][0]:
            dedup[-1] = (o, n)
        else:
            dedup.append((o, n))
    return PiecewiseMap(dedup)
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_warp.py`
Expected: `6 passed`

- [ ] **Step 5: 커밋**
```bash
git add sg/warp.py tests/test_warp.py
git commit -m "feat: build_warp 구간 길이·컷 → 시간 변환표"
```

---

### Task 3: 프리미어 파싱(중첩 시퀀스) + EDL

**Files:**
- Create: `sg/prproj.py`, `sg/edl.py`, `tests/fixtures/mini.prproj.xml`
- Modify: `scripts/parse_prproj.py` (sg.prproj 사용하는 얇은 CLI로 교체)
- Test: `tests/test_prproj.py`, `tests/test_edl.py`

**Interfaces:**
- Consumes: `PiecewiseMap` (Task 1)
- Produces:
  - `sg.prproj.parse(path) -> list[dict]` — 시퀀스 목록 `{"sequence","uid","tracks":[{"kind","index","items":[{"start","end","in","out","name","file","seq_uid","speed"}]}]}`. 중첩 시퀀스 클립은 `file=None`, `seq_uid="<uid>"`.
  - `sg.edl.build_edl(seq: dict, part_clips: dict[str,str], outro_clip: str|None, cuts_pr: list[dict]) -> dict` — `{"parts":[{"id","clip","pr_in","src_in","dur"}],"cuts":[...],"outro":{...}|None,"pr_length","length"}`
  - `sg.edl.pr_to_master(edl, p: float, clamp=True) -> float|None`
  - `sg.edl.master_to_pr(edl, m: float) -> float`
  - `sg.edl.part_to_master(edl, part_id: str, u: float) -> float|None`
  - `sg.edl.part_anchors(edl, warp: PiecewiseMap, part_id: str) -> tuple[PiecewiseMap, float]` — 파트 로컬 old→new 변환과 새 파트 길이.

- [ ] **Step 1: 테스트 픽스처와 실패하는 테스트**

`tests/fixtures/mini.prproj.xml` (프리미어 XML 구조를 축약한 최소 예. 실제 B209 XML과 같은 태그·참조 방식)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<PremiereData>
  <Sequence ObjectUID="seq-main"><Name>MAIN</Name><TrackGroups><TrackGroup><Second ObjectRef="10"/></TrackGroup></TrackGroups></Sequence>
  <VideoTrackGroup ObjectID="10"><TrackGroup><Tracks><Track ObjectURef="trk-v1"/></Tracks></TrackGroup></VideoTrackGroup>
  <VideoClipTrack ObjectUID="trk-v1"><ClipTrack><ClipItems><TrackItems><TrackItem ObjectRef="20"/><TrackItem ObjectRef="21"/></TrackItems></ClipItems></ClipTrack></VideoClipTrack>
  <VideoClipTrackItem ObjectID="20"><ClipTrackItem><TrackItem><Start>0</Start><End>2540160000000</End></TrackItem><SubClip ObjectRef="30"/></ClipTrackItem></VideoClipTrackItem>
  <VideoClipTrackItem ObjectID="21"><ClipTrackItem><TrackItem><Start>2540160000000</Start><End>3810240000000</End></TrackItem><SubClip ObjectRef="31"/></ClipTrackItem></VideoClipTrackItem>
  <SubClip ObjectID="30"><Clip ObjectRef="40"/><Name>part_a.mp4</Name></SubClip>
  <SubClip ObjectID="31"><Clip ObjectRef="41"/><Name>BGM_nest</Name></SubClip>
  <VideoClip ObjectID="40"><Clip><Source ObjectRef="50"/><InPoint>254016000000</InPoint><OutPoint>2794176000000</OutPoint></Clip></VideoClip>
  <RemixClip ObjectID="41"><Clip><Source ObjectRef="51"/><InPoint>0</InPoint><OutPoint>1270080000000</OutPoint></Clip></RemixClip>
  <VideoMediaSource ObjectID="50"><MediaSource><Media ObjectURef="media-a"/></MediaSource></VideoMediaSource>
  <Media ObjectUID="media-a"><FilePath>C:\work\part_a.mp4</FilePath></Media>
  <AudioSequenceSource ObjectID="51"><SequenceSource><Sequence ObjectURef="seq-nest"/></SequenceSource></AudioSequenceSource>
  <Sequence ObjectUID="seq-nest"><Name>NEST</Name></Sequence>
</PremiereData>
```

`tests/test_prproj.py`
```python
from pathlib import Path
from sg.prproj import parse

FIX = Path(__file__).parent / "fixtures" / "mini.prproj.xml"


def test_parse_main_sequence_items():
    seqs = {s["uid"]: s for s in parse(FIX)}
    v = seqs["seq-main"]["tracks"][0]
    assert v["kind"] == "video"
    a, b = v["items"]
    assert (a["start"], a["end"], a["in"]) == (0.0, 10.0, 1.0)
    assert a["file"] == "C:\\work\\part_a.mp4" and a["seq_uid"] is None
    assert (b["start"], b["end"]) == (10.0, 15.0)
    assert b["file"] is None and b["seq_uid"] == "seq-nest"
```

`tests/test_edl.py`
```python
import pytest
from sg.edl import build_edl, pr_to_master, master_to_pr, part_to_master, part_anchors
from sg.timemap import PiecewiseMap


def seq_fixture():
    # 프리미어 V1: A 0~10(src 0), B 10~14(src 0), B 14~20(src 6: src 4~6 건너뜀), OUTRO 20~22
    it = lambda s, e, i, n: {"start": s, "end": e, "in": i, "out": None, "name": n, "file": None, "seq_uid": None, "speed": 1.0}
    return {"tracks": [{"kind": "video", "index": 0, "items": [
        it(0, 10, 0, "A.mp4"), it(10, 14, 0, "B.mp4"), it(14, 20, 6, "B.mp4"), it(20, 22, 0, "OUT.mov")]}]}


def edl():
    return build_edl(seq_fixture(), {"A.mp4": "a", "B.mp4": "b"}, "OUT.mov",
                     [{"pr_in": 16.0, "pr_out": 17.0, "reason": "yt"}])


def test_build_edl_parts_and_length():
    e = edl()
    assert [(p["id"], p["pr_in"], p["src_in"], p["dur"]) for p in e["parts"]] == [
        ("a", 0, 0, 10), ("b", 10, 0, 4), ("b", 14, 6, 6)]
    assert e["outro"] == {"clip": "OUT.mov", "pr_in": 20, "dur": 2}
    assert e["pr_length"] == 22 and e["length"] == 21


def test_pr_master_conversion():
    e = edl()
    assert pr_to_master(e, 15.0) == 15.0
    assert pr_to_master(e, 16.5) == 16.0                 # 컷 안 → 컷 시작으로
    assert pr_to_master(e, 16.5, clamp=False) is None
    assert pr_to_master(e, 18.0) == 17.0
    assert master_to_pr(e, 17.0) == 18.0


def test_part_to_master_skips_unused_source():
    e = edl()
    assert part_to_master(e, "b", 2.0) == 12.0
    assert part_to_master(e, "b", 5.0) is None           # 건너뛴 소스
    assert part_to_master(e, "b", 8.0) == 16.0


def test_part_anchors_identity_warp_collapses_skipped_source():
    e = edl()
    m, dur = part_anchors(e, PiecewiseMap.identity(), "b")
    assert m(0) == pytest.approx(0) and m(4) == pytest.approx(4)
    assert m(6) == pytest.approx(4)                      # src 4~6 접힘
    assert m(8) == pytest.approx(6)
    assert m(12) == pytest.approx(9)                     # 컷 1초 빠짐(pr 16~17)
    assert dur == pytest.approx(9)


def test_part_anchors_follow_master_warp():
    e = edl()
    w = PiecewiseMap([(0, 0), (10, 10), (12, 14), (21, 23)])   # 마스터 10~12가 2초 → 4초
    m, dur = part_anchors(e, w, "b")
    assert m(2) == pytest.approx(4)
    assert dur == pytest.approx(11)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_prproj.py tests/test_edl.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg.prproj'`

- [ ] **Step 3: 구현**

`sg/prproj.py`
```python
"""프리미어 .prproj(gzip XML) 시퀀스 타임라인 파서. 시간 단위: 초."""
import gzip
import xml.etree.ElementTree as ET

TICKS = 254016000000.0


def _load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)


def parse(path):
    root = _load(path)
    ids = {e.get("ObjectID"): e for e in root if e.get("ObjectID")}
    uids = {e.get("ObjectUID"): e for e in root if e.get("ObjectUID")}

    def ref(e):
        if e is None:
            return None
        if e.get("ObjectRef"):
            return ids.get(e.get("ObjectRef"))
        if e.get("ObjectURef"):
            return uids.get(e.get("ObjectURef"))
        return None

    def num(e, tag):
        x = e.find(".//" + tag) if e is not None else None
        try:
            return float(x.text) / TICKS if x is not None and x.text else None
        except ValueError:
            return None

    def source_of(clip):
        """(file, seq_uid)"""
        src = ref(clip.find(".//Source")) if clip is not None else None
        for _ in range(4):
            if src is None:
                return None, None
            seq = src.find(".//SequenceSource/Sequence")
            if seq is not None:
                return None, seq.get("ObjectURef")
            m = src.find(".//Media")
            med = ref(m) if m is not None else None
            if med is not None:
                fp = med.find("ActualMediaFilePath")
                if fp is None or not fp.text or fp.text.isdigit():
                    fp = med.find("FilePath")
                return (fp.text if fp is not None else None), None
            src = ref(src.find(".//OriginalClip")) or ref(src.find(".//Source"))
        return None, None

    out = []
    for seq in [e for e in root if e.tag == "Sequence"]:
        tracks = []
        for tg in seq.iter("TrackGroup"):
            grp = ref(tg.find("Second"))
            if grp is None:
                continue
            for tr in grp.iter("Track"):
                track = ref(tr)
                if track is None:
                    continue
                kind = "video" if "Video" in track.tag else "audio"
                items = []
                for ti in track.iter("TrackItem"):
                    item = ref(ti)
                    if item is None or "Transition" in item.tag:
                        continue
                    t = item.find(".//TrackItem")
                    sub = ref(item.find(".//SubClip"))
                    clip = ref(sub.find("Clip")) if sub is not None else None
                    f, su = source_of(clip)
                    sp = clip.find(".//PlaybackSpeed") if clip is not None else None
                    items.append({"start": round(num(t, "Start") or 0.0, 3), "end": round(num(t, "End") or 0.0, 3),
                                  "in": round(num(clip, "InPoint") or 0.0, 3),
                                  "out": round(num(clip, "OutPoint") or 0.0, 3),
                                  "name": sub.findtext("Name") if sub is not None else None,
                                  "file": f, "seq_uid": su,
                                  "speed": float(sp.text) if sp is not None and sp.text else 1.0})
                items.sort(key=lambda x: x["start"])
                idx = len([x for x in tracks if x["kind"] == kind])
                tracks.append({"kind": kind, "index": idx, "items": items})
        out.append({"sequence": (seq.findtext("Name") or "").strip(), "uid": seq.get("ObjectUID"), "tracks": tracks})
    return out
```

`sg/edl.py`
```python
"""마스터 EDL: 프리미어 V1 → 파트/컷/아웃트로, 그리고 시간 변환."""
from sg.timemap import PiecewiseMap


def build_edl(seq, part_clips, outro_clip, cuts_pr):
    v1 = [t for t in seq["tracks"] if t["kind"] == "video"][0]["items"]
    parts, outro = [], None
    for it in v1:
        dur = round(it["end"] - it["start"], 3)
        if it["name"] == outro_clip:
            outro = {"clip": it["name"], "pr_in": it["start"], "dur": dur}
        elif it["name"] in part_clips:
            parts.append({"id": part_clips[it["name"]], "clip": it["name"],
                          "pr_in": it["start"], "src_in": it["in"] or 0.0, "dur": dur})
        else:
            raise ValueError(f"V1 clip not mapped: {it['name']}")
    by = {}
    for p in parts:
        prev = by.get(p["id"])
        if prev and p["src_in"] < prev["src_in"] + prev["dur"] - 1e-3:
            raise ValueError(f"part {p['id']} clips overlap or go backwards in source")
        by[p["id"]] = p
    pr_len = max(it["end"] for it in v1)
    cuts = sorted(cuts_pr, key=lambda c: c["pr_in"])
    cut_total = sum(c["pr_out"] - c["pr_in"] for c in cuts)
    return {"parts": parts, "cuts": cuts, "outro": outro,
            "pr_length": pr_len, "length": round(pr_len - cut_total, 3)}


def pr_to_master(edl, p, clamp=True):
    removed = 0.0
    for c in edl["cuts"]:
        if p >= c["pr_out"]:
            removed += c["pr_out"] - c["pr_in"]
        elif p > c["pr_in"]:
            return (c["pr_in"] - removed) if clamp else None
    return p - removed


def master_to_pr(edl, m):
    p = m
    for c in edl["cuts"]:
        if p >= c["pr_in"]:
            p += c["pr_out"] - c["pr_in"]
    return p


def part_to_master(edl, part_id, u):
    for c in edl["parts"]:
        if c["id"] == part_id and c["src_in"] <= u < c["src_in"] + c["dur"] + 1e-9:
            return pr_to_master(edl, c["pr_in"] + (u - c["src_in"]), clamp=False)
    return None


def part_anchors(edl, warp, part_id):
    clips = [c for c in edl["parts"] if c["id"] == part_id]
    if not clips:
        raise KeyError(part_id)
    first_m = pr_to_master(edl, clips[0]["pr_in"])
    base = warp(first_m) - clips[0]["src_in"]
    pts = []
    for c in clips:
        a, b = c["pr_in"], c["pr_in"] + c["dur"]
        bps = {a, b}
        for cut in edl["cuts"]:
            for x in (cut["pr_in"], cut["pr_out"]):
                if a < x < b:
                    bps.add(x)
        for o, _ in warp.pts:
            x = master_to_pr(edl, o)
            if a < x < b:
                bps.add(x)
        for p in sorted(bps):
            u = c["src_in"] + (p - a)
            n = warp(pr_to_master(edl, p)) - base
            if pts and u <= pts[-1][0] + 1e-9:
                pts[-1] = (pts[-1][0], max(pts[-1][1], n))
            else:
                pts.append((u, n))
    for i in range(1, len(pts)):   # 부동소수 오차로 new가 줄어드는 것 방지
        if pts[i][1] < pts[i - 1][1]:
            pts[i] = (pts[i][0], pts[i - 1][1])
    m = PiecewiseMap(pts)
    end = clips[-1]["src_in"] + clips[-1]["dur"]
    return m, m(end) - m(clips[0]["src_in"])
```

`scripts/parse_prproj.py` (전체 교체)
```python
"""usage: python3 -I scripts/parse_prproj.py <file.prproj> > timeline.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.prproj import parse

json.dump(parse(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=1)
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_prproj.py tests/test_edl.py`
Expected: `6 passed`

- [ ] **Step 5: B209 실제 데이터로 확인**

Run:
```bash
cd ~/Projects/semoji_global && python3 scripts/parse_prproj.py "episodes/B209/B_코스트코_음악작업.prproj" > episodes/B209/pr_timeline.json && python3 - <<'EOF'
import json
from sg.edl import build_edl
s=[x for x in json.load(open('episodes/B209/pr_timeline.json')) if x['uid'].startswith('54a2a221')][0]
e=build_edl(s,{"B209_코스트코_음악전_미나.mp4":"mina","B209_코스트코_음악전_가영.mp4":"gayoung","B209_코스트코_음악전_가을.mp4":"gaeul"},
            "세모지 아웃트로_최종.mov",[{"pr_in":914.3,"pr_out":923.3,"reason":"유튜브 업로드본에서 잘림"}])
print(len(e['parts']), e['pr_length'], e['length'])
bgm=[i for t in s['tracks'] if t['kind']=='audio' for i in t['items'] if i['seq_uid']]
print('nested', [(i['name'], i['seq_uid'][:8]) for i in bgm])
EOF
```
Expected: `7 988.354 979.354` 이고, nested 목록에 `146468_High Energy…`, `252509_sometimes…`, `146021_Horse…` 3개가 `seq_uid`와 함께 나온다.

- [ ] **Step 6: 커밋**
```bash
git add sg/prproj.py sg/edl.py scripts/parse_prproj.py tests/fixtures/mini.prproj.xml tests/test_prproj.py tests/test_edl.py
git commit -m "feat: 프리미어 파서(중첩 시퀀스)와 EDL 시간 변환"
```

---

### Task 4: AE 그래프 순회 (`sg/graph.py`)

**Files:**
- Create: `sg/graph.py`
- Modify: `scripts/reach.py` (sg.graph를 쓰는 CLI로 교체)
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: graph.jsx 출력 형식 `{"comps":{id:{"name","dur","layers":[{"i","name","src","in","out","st","sx","en","au","vid","tr","matte"}]}},"items":{id:{...}}}`
- Produces: `sg.graph.walk(graph: dict, root_id: str, t0: float, t1: float) -> list[dict]` — 도달하는 모든 레이어(텍스트 포함) `{"comp_id","layer","src","spans":[[a,b],...],"path":[컴프 이름...]}`, spans는 루트 컴프 시간. 같은 (comp_id, layer)는 하나로 합치고 구간 병합. `sg.graph.reach_items(graph, root_id, t0, t1) -> dict[item_id, dict]`(기존 reach.py 출력과 같은 형식).

- [ ] **Step 1: 실패하는 테스트**

`tests/test_graph.py`
```python
from sg.graph import walk, reach_items


def L(i, src, a, b, st=0.0, sx=100, en=True, au=False, tr=False, matte=False, name=""):
    return {"i": i, "name": name, "src": src, "in": a, "out": b, "st": st, "sx": sx,
            "en": en, "au": au, "vid": True, "tr": tr, "matte": matte}


G = {"comps": {
        "1": {"name": "ROOT", "dur": 100, "layers": [L(1, 2, 10, 20, st=10), L(2, None, 0, 5), L(3, 2, 50, 60, st=45, sx=200), L(4, 9, 0, 3, en=False)]},
        "2": {"name": "PRE", "dur": 30, "layers": [L(1, 7, 0, 4), L(2, None, 2, 8)]}},
     "items": {"7": {"name": "pic.png", "file": "/x/pic.png", "missing": False},
               "9": {"name": "off.png", "file": "/x/off.png", "missing": False}}}


def spans(res, comp_id, layer):
    return [r["spans"] for r in res if r["comp_id"] == comp_id and r["layer"] == layer][0]


def test_walk_maps_child_times_to_root():
    res = walk(G, "1", 0, 100)
    assert spans(res, "1", 2) == [[0, 5]]               # 텍스트(소스 없음)도 포함
    # PRE 레이어2(2~8): 첫 사용 st=10 → 12~18, 두 번째 사용 st=45, sx=2 → 49~61 이지만 레이어 50~60으로 잘림
    assert spans(res, "2", 2) == [[12, 18], [50, 60]]


def test_disabled_layers_are_skipped():
    res = walk(G, "1", 0, 100)
    assert not [r for r in res if r["src"] == 9]


def test_reach_items():
    r = reach_items(G, "1", 0, 100)
    assert set(r) == {"7"}
    assert r["7"]["spans"] == [[10, 14], [50, 53]]
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_graph.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg.graph'`

- [ ] **Step 3: 구현**

`sg/graph.py`
```python
"""graph.jsx 출력 순회: 루트 컴프 시간 구간에 실제로 도달하는 레이어."""


def _merge(spans):
    m = []
    for a, b in sorted(spans):
        if m and a <= m[-1][1] + 0.05:
            m[-1][1] = max(m[-1][1], b)
        else:
            m.append([a, b])
    return [[round(a, 3), round(b, 3)] for a, b in m]


def walk(graph, root_id, t0, t1):
    comps = graph["comps"]
    acc = {}

    def rec(cid, a, b, k, off, path, depth):
        if depth > 30:
            return
        for L in comps[cid]["layers"]:
            if not (L["en"] or L["matte"] or L["au"]):
                continue
            lo = max(a, min(L["in"], L["out"]))
            hi = min(b, max(L["in"], L["out"]))
            if lo >= hi:
                continue
            key = (cid, L["i"])
            e = acc.setdefault(key, {"comp_id": cid, "layer": L["i"], "src": L["src"], "spans": [], "path": path})
            e["spans"].append([lo * k + off, hi * k + off])
            sid = str(L["src"]) if L["src"] is not None else None
            if sid in comps:
                sx = (L["sx"] or 100) / 100.0
                if L["tr"]:
                    rec(sid, 0, comps[sid]["dur"], 0.0, lo * k + off, path + [comps[sid]["name"]], depth + 1)
                    continue
                ca, cb = (lo - L["st"]) / sx, (hi - L["st"]) / sx
                if sx < 0:
                    ca, cb = cb, ca
                rec(sid, ca, cb, k * sx, off + L["st"] * k, path + [comps[sid]["name"]], depth + 1)

    rec(root_id, t0, t1, 1.0, 0.0, [comps[root_id]["name"]], 0)
    out = []
    for e in acc.values():
        e["spans"] = _merge(e["spans"])
        out.append(e)
    return out


def reach_items(graph, root_id, t0, t1):
    items = graph["items"]
    res = {}
    for r in walk(graph, root_id, t0, t1):
        sid = str(r["src"]) if r["src"] is not None else None
        if sid in items:
            e = res.setdefault(sid, {**items[sid], "spans": [], "via": r["path"]})
            e["spans"] += r["spans"]
    for e in res.values():
        e["spans"] = _merge(e["spans"])
    return res
```

`scripts/reach.py` (전체 교체)
```python
"""usage: python3 -I scripts/reach.py <graph.json> <root_comp_id> [t0 t1] > reach.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.graph import reach_items

g = json.load(open(sys.argv[1]))
root = sys.argv[2]
t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else tuple(g["comps"][root]["wa"])
json.dump(reach_items(g, root, t0, t1), sys.stdout, ensure_ascii=False, indent=1)
```

- [ ] **Step 4: 통과 확인 + 기존 결과와 회귀 비교**

Run:
```bash
python3 -m pytest -q tests/test_graph.py && python3 -I scripts/reach.py episodes/B209/graph_nas.json 14989 0 534.133 | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), sum(1 for v in d.values() if v['missing']))"
```
Expected: `3 passed`, 그리고 `415 0` (기존 reach.py 결과와 같은 개수, 누락 0).

- [ ] **Step 5: 커밋**
```bash
git add sg/graph.py scripts/reach.py tests/test_graph.py
git commit -m "feat: AE 그래프 순회 모듈(텍스트 레이어 포함)"
```

---

### Task 5: 무음 분할 + 내레이션 구간·화면 문자열 → `master/source.json`, `master/edl.json`

**Files:**
- Create: `sg/audio.py`, `sg/segments.py`, `scripts/master.py`, `episodes/B209/master_config.json`
- Test: `tests/test_audio.py`, `tests/test_segments.py`

**Interfaces:**
- Consumes: `walk` (Task 4), `build_edl`/`part_to_master` (Task 3)
- Produces:
  - `sg.audio.decode(path, sr=16000) -> numpy.ndarray`(float32 mono)
  - `sg.audio.speech_spans(x, sr, thresh_db=-40.0, min_silence=0.25, min_speech=0.15, pad=0.05) -> list[tuple[float,float]]`
  - `sg.segments.attach_text(spans: list[tuple[float,float]], subs: list[dict]) -> list[dict]` — subs 원소 `{"text","in","out"}`(같은 시간축). 반환 `{"in","out","ko","subs":[...]}`; 자막 하나는 겹침이 가장 큰 구간 하나에만 붙고, 어느 구간과도 겹치지 않는 자막은 가장 가까운 구간에 붙인다(누락 없음).
  - `scripts/master.py <EP 폴더>` → `master/edl.json`, `master/source.json`(`segments`,`strings`)
  - `source.json` segments 원소: `{"id":"n001","part","in","out","ko","subs":[...]}` (마스터 시간), strings 원소: `{"id":"s<comp_id>_<layer>","comp","comp_id","layer","ko","font","size","spans":[[a,b]]}`

- [ ] **Step 1: 실패하는 테스트**

`tests/test_audio.py`
```python
import numpy as np
from sg.audio import speech_spans

SR = 16000


def tone(sec, amp=0.3):
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def sil(sec):
    return np.zeros(int(sec * SR), np.float32)


def test_two_phrases():
    x = np.concatenate([sil(0.5), tone(1.0), sil(0.6), tone(0.7), sil(0.3)])
    s = speech_spans(x, SR)
    assert len(s) == 2
    assert abs(s[0][0] - 0.45) < 0.05 and abs(s[0][1] - 1.55) < 0.05
    assert abs(s[1][0] - 2.05) < 0.05 and abs(s[1][1] - 2.85) < 0.05


def test_short_gap_merges():
    x = np.concatenate([tone(1.0), sil(0.1), tone(1.0)])
    assert len(speech_spans(x, SR)) == 1
```

`tests/test_segments.py`
```python
from sg.segments import attach_text


def test_each_subtitle_attached_exactly_once():
    spans = [(0.0, 3.0), (3.6, 8.0)]
    subs = [{"text": "가", "in": 0.1, "out": 1.5}, {"text": "나", "in": 1.5, "out": 3.4},
            {"text": "다", "in": 3.4, "out": 6.0}, {"text": "라", "in": 9.0, "out": 9.5}]
    segs = attach_text(spans, subs)
    assert [s["ko"] for s in segs] == ["가 나", "다 라"]
    assert sum(len(s["subs"]) for s in segs) == 4


def test_long_merged_span_keeps_all_texts():
    segs = attach_text([(0.0, 10.0)], [{"text": f"문장{i}", "in": i, "out": i + 1} for i in range(10)])
    assert segs[0]["ko"].split() == [f"문장{i}" for i in range(10)]
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_audio.py tests/test_segments.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg.audio'`

- [ ] **Step 3: 구현**

`sg/audio.py`
```python
"""오디오 디코드와 무음 기준 말 구간 분할."""
import subprocess
import numpy as np


def decode(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def speech_spans(x, sr, thresh_db=-40.0, min_silence=0.25, min_speech=0.15, pad=0.05):
    hop = int(sr * 0.01)
    n = len(x) // hop
    if n == 0:
        return []
    fr = x[: n * hop].reshape(n, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    voiced = db > thresh_db
    spans, start, last = [], None, None
    for i, v in enumerate(voiced):
        t = i * 0.01
        if v:
            if start is None:
                start = t
            elif last is not None and t - last > min_silence:
                spans.append((start, last))
                start = t
            last = t + 0.01
    if start is not None:
        spans.append((start, last))
    dur = len(x) / sr
    out = []
    for a, b in spans:
        if b - a < min_speech:
            continue
        out.append((max(0.0, round(a - pad, 3)), min(dur, round(b + pad, 3))))
    return out
```

`sg/segments.py`
```python
"""말 구간에 자막 텍스트를 붙여 내레이션 구간을 만든다."""


def attach_text(spans, subs):
    segs = [{"in": a, "out": b, "ko": "", "subs": []} for a, b in spans]
    if not segs:
        return segs
    for s in sorted(subs, key=lambda x: x["in"]):
        best, score = None, -1e9
        for i, g in enumerate(segs):
            ov = min(g["out"], s["out"]) - max(g["in"], s["in"])
            if ov <= 0:
                ov = -min(abs(g["in"] - s["out"]), abs(s["in"] - g["out"]))
            if ov > score:
                best, score = i, ov
        segs[best]["subs"].append(s)
    for g in segs:
        g["subs"].sort(key=lambda x: x["in"])
        g["ko"] = " ".join(x["text"].replace("\r", " ").strip() for x in g["subs"])
    return segs
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_audio.py tests/test_segments.py`
Expected: `4 passed`

- [ ] **Step 5: B209 설정 파일과 master CLI**

`episodes/B209/master_config.json`
```json
{
  "episode": "B209",
  "nas_ep": "/Volumes/jleavens/002_intra/001_세상의모든지식/◆브랜드백과사전/B209_코스트코_미나_편집완",
  "prproj_timeline": "pr_timeline.json",
  "sequence_uid": "54a2a221",
  "outro_clip": "세모지 아웃트로_최종.mov",
  "cuts_pr": [{"pr_in": 914.3, "pr_out": 923.3, "reason": "유튜브 업로드본에서 잘림"}],
  "graph": "graph_nas.json",
  "inventory": "inventory_nas.json",
  "parts": {
    "mina":    {"clip": "B209_코스트코_음악전_미나.mp4", "comp_id": "14989", "comp": "MAIN_KO", "dur": 534.133, "narration": "B209_코스트코_오디오편집완_미나.wav"},
    "gayoung": {"clip": "B209_코스트코_음악전_가영.mp4", "comp_id": "2370", "comp": "MAIN_GAYOUNG", "dur": 217.317, "narration": "B209_코스트코_오디오가영.wav"},
    "gaeul":   {"clip": "B209_코스트코_음악전_가을.mp4", "comp_id": "5848", "comp": "MAIN_GAEUL", "dur": 226.626, "narration": "B209_코스트코_오디오가을편집완.wav"}
  },
  "subtitle_comp_prefix": "#자막"
}
```

`scripts/master.py`
```python
"""편 마스터 생성: master/edl.json, master/source.json.  usage: python3 scripts/master.py episodes/B209"""
import json, os, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.audio import decode, speech_spans
from sg.edl import build_edl, part_to_master
from sg.graph import walk
from sg.segments import attach_text

NFC = lambda s: unicodedata.normalize("NFC", s)


def local_file(nas_file, nas_ep, ep_dir):
    rel = os.path.relpath(NFC(nas_file), NFC(nas_ep))
    p = os.path.join(ep_dir, "src", rel)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    return p


def main(ep_dir):
    C = json.load(open(os.path.join(ep_dir, "master_config.json")))
    tl = json.load(open(os.path.join(ep_dir, C["prproj_timeline"])))
    seq = [s for s in tl if s["uid"].startswith(C["sequence_uid"])][0]
    edl = build_edl(seq, {p["clip"]: pid for pid, p in C["parts"].items()}, C["outro_clip"], C["cuts_pr"])
    G = json.load(open(os.path.join(ep_dir, C["graph"])))
    inv = json.load(open(os.path.join(ep_dir, C["inventory"])))
    texts = {(str(t["comp_id"]), t["layer"]): t for t in inv["texts"]}

    segments, strings = [], {}
    for pid, P in C["parts"].items():
        layers = walk(G, P["comp_id"], 0, P["dur"])

        def to_master(spans):
            out = []
            for a, b in spans:
                ma, mb = part_to_master(edl, pid, a), part_to_master(edl, pid, max(a, b - 1e-3))
                if ma is not None and mb is not None and mb > ma:
                    out.append([round(ma, 3), round(mb, 3)])
            return out

        subs = []
        for r in layers:
            t = texts.get((r["comp_id"], r["layer"]))
            if not t:
                continue
            ms = to_master(r["spans"])
            if not ms:
                continue
            if t["comp"].startswith(C["subtitle_comp_prefix"]):
                for a, b in ms:
                    subs.append({"text": t["text"], "in": a, "out": b, "layer": f"{t['comp']}:{t['layer']}"})
            else:
                sid = f"s{r['comp_id']}_{r['layer']}"
                e = strings.setdefault(sid, {"id": sid, "comp": t["comp"], "comp_id": int(r["comp_id"]), "layer": r["layer"],
                                             "ko": t["text"], "font": t["font"], "size": t["size"], "keys": len(t["keys"]), "spans": []})
                e["spans"] += ms
        # 내레이션: 파트 컴프의 내레이션 레이어 → 파트 시간 → 마스터 시간
        nar = [L for L in G["comps"][P["comp_id"]]["layers"]
               if L["src"] is not None and G["items"].get(str(L["src"]), {}).get("name") == P["narration"]]
        if len(nar) != 1:
            raise ValueError(f"{pid}: narration layer count {len(nar)}")
        L = nar[0]
        wav = local_file(G["items"][str(L["src"])]["file"], C["nas_ep"], ep_dir)
        x = decode(wav)
        spans = []
        for a, b in speech_spans(x, 16000):
            ua, ub = L["st"] + a, L["st"] + b
            if ub <= L["in"] or ua >= L["out"]:
                continue
            ms = to_master([[max(ua, L["in"]), min(ub, L["out"])]])
            spans += [tuple(m) for m in ms]
        part_subs = [s for s in subs]
        for g in attach_text(spans, part_subs):
            g["part"] = pid
            segments.append(g)
    segments.sort(key=lambda g: g["in"])
    for i, g in enumerate(segments, 1):
        g["id"] = f"n{i:03d}"
    os.makedirs(os.path.join(ep_dir, "master"), exist_ok=True)
    json.dump(edl, open(os.path.join(ep_dir, "master/edl.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"segments": segments, "strings": sorted(strings.values(), key=lambda s: s["spans"][0][0])},
              open(os.path.join(ep_dir, "master/source.json"), "w"), ensure_ascii=False, indent=1)
    empty = [g["id"] for g in segments if not g["ko"]]
    print(f"segments {len(segments)}  strings {len(strings)}  length {edl['length']}  no-text {len(empty)} {empty[:10]}")


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 6: B209 마스터 생성·검증**

Run: `cd ~/Projects/semoji_global && python3 scripts/master.py episodes/B209`
Expected: `segments` 100~300개, `strings` 20~80개, `length 979.354`. `no-text`가 10개를 넘으면 `speech_spans`의 `thresh_db`를 −45로 낮춰 다시 실행하고 숫자를 보고서에 기록한다.

추가 검증(눈으로): 
```bash
python3 -c "
import json; d=json.load(open('episodes/B209/master/source.json'))
for g in d['segments'][:8]: print(g['id'], g['part'], g['in'], g['out'], g['ko'][:50])
for s in d['strings'][:8]: print(s['id'], s['spans'][:2], s['ko'][:40])"
```
Expected: 첫 구간이 유튜브 0초 근처 오프닝 문장과 같은 한글이고, 문자열에 "Chapter 2. 최초의 회원제 창고형매장…"(약 309초)이 있다.

- [ ] **Step 7: 커밋**
```bash
git add sg/audio.py sg/segments.py scripts/master.py episodes/B209/master_config.json tests/test_audio.py tests/test_segments.py
git -c core.quotepath=off add -f episodes/B209/master/edl.json episodes/B209/master/source.json
git commit -m "feat: 마스터 생성(EDL·내레이션 구간·화면 문자열) — B209"
```

---

### Task 6: AE 타임 워프 엔진 `localize.jsx` + 변환표 CLI

**Files:**
- Create: `scripts/ae/localize.jsx`, `scripts/timewarp.py`
- Test: `tests/test_timewarp_cli.py`

**Interfaces:**
- Consumes: `build_warp` (Task 2), `part_anchors` (Task 3), `master/edl.json`·`source.json` (Task 5)
- Produces:
  - `scripts/timewarp.py <EP 폴더> <tag> (--durs durs.json | --test-pattern)` → `build/<tag>/warp.json`(`{"master": [[old,new]...], "length_new": float, "parts": {pid: {"anchors": [[u_old,u_new]...], "dur_new": float, "comp": "MAIN_KO"}}}`) + `scripts/ae/localize_job.json`
  - `--test-pattern`: 구간 순번이 짝수면 ×1.15, 홀수면 ×0.9인 새 길이(실제 번역 길이 흉내).
  - `localize.jsx` job 형식: `{"aep","save_as","out","mute_sources":[파일 이름],"hide_comp_prefix":"#자막","parts":[{"comp","anchors","dur_new"}]}` → 로그 `{"parts":[{"comp","layers","keys","dups","holds","dur_new"}],"warnings":[...],"errors":[...]}`

- [ ] **Step 1: 실패하는 테스트 (CLI 순수 로직)**

`tests/test_timewarp_cli.py`
```python
import json, subprocess, sys
from pathlib import Path


def make_ep(tmp):
    ep = Path(tmp) / "EP"
    (ep / "master").mkdir(parents=True)
    edl = {"parts": [{"id": "a", "clip": "A", "pr_in": 0, "src_in": 0, "dur": 10},
                     {"id": "b", "clip": "B", "pr_in": 10, "src_in": 0, "dur": 10}],
           "cuts": [], "outro": None, "pr_length": 20, "length": 20}
    src = {"segments": [{"id": "n001", "part": "a", "in": 1, "out": 4, "ko": "x", "subs": []},
                        {"id": "n002", "part": "b", "in": 12, "out": 16, "ko": "y", "subs": []}], "strings": []}
    json.dump(edl, open(ep / "master/edl.json", "w"))
    json.dump(src, open(ep / "master/source.json", "w"))
    json.dump({"parts": {"a": {"comp": "CA", "narration": "na.wav"}, "b": {"comp": "CB", "narration": "nb.wav"}}},
              open(ep / "master_config.json", "w"))
    return ep


def test_test_pattern_writes_warp(tmp_path):
    ep = make_ep(tmp_path)
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/timewarp.py"), str(ep), "t1", "--test-pattern",
                    "--job", str(tmp_path / "job.json")], check=True)
    w = json.load(open(ep / "build/t1/warp.json"))
    # n001 3초 ×0.9(홀수 순번=1) = 2.7, n002 4초 ×1.15 = 4.6 → 전체 20 - 0.3 + 0.6
    assert abs(w["length_new"] - 20.3) < 1e-6
    assert abs(w["parts"]["a"]["dur_new"] - 9.7) < 1e-6
    assert w["parts"]["b"]["comp"] == "CB"
    job = json.load(open(tmp_path / "job.json"))
    assert job["mute_sources"] == ["na.wav", "nb.wav"]
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_timewarp_cli.py`
Expected: FAIL — `scripts/timewarp.py` 없음(파일 없음 오류)

- [ ] **Step 3: `scripts/timewarp.py` 구현**

```python
"""변환표 생성.  usage: timewarp.py <EP> <tag> (--durs durs.json | --test-pattern) [--job path]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.warp import build_warp
from sg.edl import part_anchors

ep, tag = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
cfg = json.load(open(os.path.join(ep, "master_config.json")))
segs = src["segments"]
if "--test-pattern" in args:
    durs = {g["id"]: (g["out"] - g["in"]) * (0.9 if (i % 2 == 1) else 1.15) for i, g in enumerate(segs, 1)}
else:
    durs = json.load(open(args[args.index("--durs") + 1]))
cuts = [(c["in"], c["out"]) for c in src.get("korea_only", [])]
warp = build_warp(segs, durs, cuts, edl["length"])
out = {"master": warp.to_list(), "length_new": warp(edl["length"]), "parts": {}}
for pid, P in cfg["parts"].items():
    m, dur = part_anchors(edl, warp, pid)
    out["parts"][pid] = {"comp": P["comp"], "anchors": m.to_list(), "dur_new": dur}
bd = os.path.join(ep, "build", tag)
os.makedirs(bd, exist_ok=True)
json.dump(out, open(os.path.join(bd, "warp.json"), "w"), indent=1)
job_path = args[args.index("--job") + 1] if "--job" in args else os.path.join(os.path.dirname(__file__), "ae/localize_job.json")
abs_ep = os.path.abspath(ep)
json.dump({"aep": os.path.join(abs_ep, "src", f"{os.path.basename(abs_ep)}_main_ko.aep"),
           "save_as": os.path.join(abs_ep, "build", tag, f"{os.path.basename(abs_ep)}_{tag}.aep"),
           "out": os.path.join(abs_ep, "build", tag, "localize_log.json"),
           "mute_sources": [P["narration"] for P in cfg["parts"].values()],
           "hide_comp_prefix": "#자막",
           "parts": [{"comp": v["comp"], "anchors": v["anchors"], "dur_new": v["dur_new"]} for v in out["parts"].values()]},
          open(job_path, "w"), ensure_ascii=False, indent=1)
print(f"length {edl['length']:.2f} -> {out['length_new']:.2f}; parts " +
      ", ".join(f"{k} {v['dur_new']:.2f}" for k, v in out["parts"].items()))
```
(테스트 패턴: 순번 1부터 홀수 구간 ×0.9, 짝수 구간 ×1.15.)

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_timewarp_cli.py`
Expected: `1 passed`

- [ ] **Step 5: `scripts/ae/localize.jsx` 작성** (저장 후 BOM 추가: `printf '\xef\xbb\xbf' | cat - scripts/ae/localize.jsx > t && mv t scripts/ae/localize.jsx`)

```javascript
// 타임 워프 엔진. 설정 localize_job.json (scripts/timewarp.py가 생성)
// 파트 컴프마다 앵커 [[old,new],...]로 레이어 in/out·startTime·stretch·키프레임을 옮기고, 프리컴프는 재귀(여러 번 쓰이면 복제).
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={parts:[], warnings:[], errors:[]}, ST=null;
var FR=1/29.97;

function Map(a){ this.a=a; }
Map.prototype.f=function(t){ var a=this.a,n=a.length;
  if(t<=a[0][0]) return a[0][1]+(t-a[0][0]);
  if(t>=a[n-1][0]) return a[n-1][1]+(t-a[n-1][0]);
  var lo=0,hi=n-1; while(hi-lo>1){ var m=(lo+hi)>>1; if(a[m][0]<=t) lo=m; else hi=m; }
  return a[lo][1]+(a[hi][1]-a[lo][1])*(t-a[lo][0])/(a[hi][0]-a[lo][0]); };
Map.prototype.child=function(stOld,stNew,sx){ var b=[]; for(var i=0;i<this.a.length;i++) b.push([(this.a[i][0]-stOld)/sx,(this.a[i][1]-stNew)/sx]); return new Map(b); };

function isSpatial(p){ return p.propertyValueType===PropertyValueType.TwoD_SPATIAL||p.propertyValueType===PropertyValueType.ThreeD_SPATIAL; }

// 1) 키프레임 기록(레이어 시간 변경 전)
function recordKeys(group, out){
  for(var i=1;i<=group.numProperties;i++){
    var p=group.property(i);
    if(p.matchName==="ADBE Marker") continue;
    if(p.propertyType===PropertyType.PROPERTY){
      if(p.numKeys>0){
        var K=[], sp=isSpatial(p);
        for(var k=1;k<=p.numKeys;k++){
          var o={t:p.keyTime(k), v:p.keyValue(k), ii:p.keyInInterpolationType(k), oi:p.keyOutInterpolationType(k)};
          try{ o.ie=p.keyInTemporalEase(k); o.oe=p.keyOutTemporalEase(k); o.tc=p.keyTemporalContinuous(k); o.ta=p.keyTemporalAutoBezier(k);}catch(e){}
          if(sp){ try{ o.ist=p.keyInSpatialTangent(k); o.ost=p.keyOutSpatialTangent(k); o.sc=p.keySpatialContinuous(k); o.sa=p.keySpatialAutoBezier(k); o.rv=p.keyRoving(k);}catch(e){} }
          K.push(o);
        }
        out.push({p:p, K:K, sp:sp});
      }
    } else { recordKeys(p, out); }
  }
}
// 2) 키프레임 재생성(절대 컴프 시간 = map(원래 시각))
function rewriteKeys(rec, map){
  var p=rec.p, K=rec.K, n=0;
  for(var k=p.numKeys;k>=1;k--) p.removeKey(k);
  var keep=[];
  for(var i=0;i<K.length;i++){ K[i].nt=map.f(K[i].t); }
  for(var i=0;i<K.length;i++){ if(i+1<K.length && Math.abs(K[i+1].nt-K[i].nt)<FR/4) continue; keep.push(K[i]); }
  for(var i=0;i<keep.length;i++){ p.setValueAtTime(keep[i].nt, keep[i].v); n++; }
  for(var i=0;i<keep.length;i++){
    var o=keep[i], idx=p.nearestKeyIndex(o.nt);
    try{ p.setInterpolationTypeAtKey(idx,o.ii,o.oi);}catch(e){}
    try{ if(o.ie) p.setTemporalEaseAtKey(idx,o.ie,o.oe);}catch(e){}
    try{ if(o.tc!==undefined){ p.setTemporalContinuousAtKey(idx,o.tc); p.setTemporalAutoBezierAtKey(idx,o.ta);} }catch(e){}
    if(rec.sp){ try{ p.setSpatialTangentsAtKey(idx,o.ist,o.ost); p.setSpatialContinuousAtKey(idx,o.sc); p.setSpatialAutoBezierAtKey(idx,o.sa); p.setRovingAtKey(idx,o.rv);}catch(e){} }
  }
  return n;
}
function setInOut(L,a,b){ if(a>=L.outPoint){ L.outPoint=b; L.inPoint=a; } else { L.inPoint=a; L.outPoint=b; } }
function srcName(L){ try{ return L.source?L.source.name:""; }catch(e){ return ""; } }
function muted(L){ var n=srcName(L); for(var i=0;i<C.mute_sources.length;i++) if(n===C.mute_sources[i]) return true; return false; }
function usesIn(parent, item){ var c=0; for(var j=1;j<=parent.numLayers;j++){ try{ if(parent.layer(j).source===item) c++; }catch(e){} } return c; }

function warpComp(comp, map, depth){
  if(depth>25){ LOG.warnings.push("depth>25 "+comp.name); return; }
  // 프리컴프는 stNew=map(ost)로 잡으므로 자식 시간 0 → 0 이 유지된다
  var oldDur=comp.duration, newDur=Math.max(map.f(oldDur), FR);
  if(Math.abs(map.f(0))>FR) LOG.warnings.push("child start shifted "+map.f(0).toFixed(3)+" in "+comp.name);
  if(newDur>comp.duration) comp.duration=newDur;
  for(var j=1;j<=comp.numLayers;j++){
    var L=comp.layer(j);
    try{
      var oin=L.inPoint, oout=L.outPoint, ost=L.startTime, sx=L.stretch/100;
      var nin=map.f(oin), nout=map.f(oout);
      if(muted(L)){ L.audioEnabled=false; continue; }
      if(L.source instanceof CompItem && String(L.source.name).indexOf(C.hide_comp_prefix)===0){ L.enabled=false; L.audioEnabled=false; continue; }
      var recs=[]; recordKeys(L, recs);
      if(nout-nin<FR){ L.enabled=false; try{L.audioEnabled=false;}catch(e){} continue; }
      if(sx<0){ LOG.warnings.push("reversed layer skipped "+comp.name+"/"+L.name); continue; }
      var stNew;
      if(L.source instanceof CompItem && !L.timeRemapEnabled){
        var child=L.source;
        if(child.usedIn.length>1 || usesIn(comp, child)>1 || ST.done[child.id]){ child=child.duplicate(); L.replaceSource(child,false); ST.dups++; }
        stNew=map.f(ost);
        L.startTime=stNew; setInOut(L,nin,nout);
        ST.done[child.id]=true;
        warpComp(child, map.child(ost, stNew, sx), depth+1);
      } else if(L.source instanceof FootageItem && L.hasVideo && !L.source.mainSource.isStill && !L.timeRemapEnabled){
        var r=(nout-nin)/(oout-oin), u=(oin-ost)/sx;
        if(r>=0.8 && r<=1.25){ L.stretch=L.stretch*r; stNew=nin-u*sx*r; L.startTime=stNew; setInOut(L,nin,nout); }
        else if(r<0.8){ L.stretch=L.stretch*0.8; stNew=nin-u*sx*0.8; L.startTime=stNew; setInOut(L,nin,nout); LOG.warnings.push("clip squeezed+trimmed r="+r.toFixed(2)+" "+comp.name+"/"+L.name); }
        else {
          stNew=nin-(oin-ost); L.startTime=stNew;
          var natEnd=stNew+L.source.duration*sx;
          if(nout<=natEnd+1e-6){ setInOut(L,nin,nout); }
          else { L.timeRemapEnabled=true; setInOut(L,nin,nout);
                 var tr=L.property("ADBE Time Remapping"); var lastSrc=L.source.duration-FR;
                 tr.setValueAtTime(natEnd-FR,lastSrc); tr.setValueAtTime(nout,lastSrc); ST.holds++; }
        }
      } else if(!L.hasVideo && L.hasAudio){
        stNew=ost+(nin-oin); L.startTime=stNew; setInOut(L,nin,nin+(oout-oin));
      } else {
        stNew=nin-(oin-ost); L.startTime=stNew; setInOut(L,nin,nout);
      }
      for(var q=0;q<recs.length;q++) ST.keys+=rewriteKeys(recs[q], map);
      ST.layers++;
    }catch(e){ LOG.errors.push(comp.name+"/"+L.name+": "+String(e)+" line "+e.line); }
  }
  comp.duration=newDur;
  try{ comp.workAreaStart=0; comp.workAreaDuration=newDur; }catch(e){}
}

app.beginSuppressDialogs();
try{
  var P=openProject(C.aep);
  for(var k=0;k<C.parts.length;k++){
    var part=C.parts[k], comp=null;
    for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===part.comp) comp=it; }
    if(!comp){ LOG.errors.push("comp not found "+part.comp); continue; }
    ST={layers:0, keys:0, dups:0, holds:0, done:{}};
    warpComp(comp, new Map(part.anchors), 0);
    LOG.parts.push({comp:part.comp, layers:ST.layers, keys:ST.keys, dups:ST.dups, holds:ST.holds, dur_new:comp.duration, dur_expected:part.dur_new});
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
```

- [ ] **Step 6: 항등 변환 검증(AE)**

항등 변환(새 길이 = 원래 길이)을 만들어 적용 → 원본 파트 렌더와 같아야 한다.

```bash
cd ~/Projects/semoji_global
python3 -c "
import json; s=json.load(open('episodes/B209/master/source.json'))
json.dump({g['id']: g['out']-g['in'] for g in s['segments']}, open('episodes/B209/build_identity_durs.json','w'))"
python3 scripts/timewarp.py episodes/B209 identity --durs episodes/B209/build_identity_durs.json
pgrep -x caffeinate >/dev/null || (caffeinate -d -u -t 21600 &)
scripts/ae/run.sh "$PWD/scripts/ae/localize.jsx"
cat episodes/B209/build/identity/localize_log.json
scripts/ae/render.sh "$PWD/episodes/B209/build/identity/B209_identity.aep" MAIN_KO 0 120 "$PWD/episodes/B209/build/identity/mina_0_120.mp4" 29.97 "H.264 - Match Render Settings - 15 Mbps"
ffmpeg -v error -y -i episodes/B209/render/part_mina.mp4 -t 120 -c copy episodes/B209/build/identity/orig_0_120.mp4
python3 scripts/compare_video.py episodes/B209/build/identity/mina_0_120.mp4 episodes/B209/build/identity/orig_0_120.mp4 episodes/B209/build/identity/cmp
```
Expected: 로그 `errors: []`, 파트마다 `dur_new`가 `dur_expected`와 ±0.05초(가을 파트는 유튜브 컷 9초가 빠져 217.6 근처). 비교 결과 `offset_sec 0.0`, `mean_sim ≥ 0.98`, 연속 차이 구간 없음(0.5초 단발만 허용). 실패하면 `cmp/diff_*.jpg`를 보고 원인 레이어 유형(프리컴프·영상·키프레임)을 찾아 규칙을 고친 뒤 이 단계를 다시 실행한다.

- [ ] **Step 7: 커밋**
```bash
git add scripts/timewarp.py scripts/ae/localize.jsx tests/test_timewarp_cli.py
git commit -m "feat: AE 타임 워프 엔진(localize.jsx)과 변환표 CLI — 항등 변환 검증"
```

---

### Task 7: 변환 영상 대조 도구 + 테스트 패턴 검증

**Files:**
- Create: `scripts/compare_warped.py`, `sg/vcompare.py`
- Test: `tests/test_vcompare.py`

**Interfaces:**
- Consumes: `PiecewiseMap` (Task 1), `build/<tag>/warp.json` (Task 6)
- Produces: `sg.vcompare.sample_pairs(part_map: PiecewiseMap, t0: float, t1: float, step: float) -> list[tuple[float,float]]` — 원본 시각 t와 변환 후 시각 `part_map(t)` 쌍. 접힌 구간(원본 길이>0인데 새 길이 0)과 앵커 ±0.2초는 제외. `scripts/compare_warped.py <orig.mp4> <warped.mp4> <warp.json> <part_id> <out_dir> [--t0 --t1]` → `out_dir/compare.json` `{"pairs","mean_sim","bad":[...]}`

- [ ] **Step 1: 실패하는 테스트**

`tests/test_vcompare.py`
```python
from sg.timemap import PiecewiseMap
from sg.vcompare import sample_pairs


def test_pairs_follow_map_and_skip_collapsed_and_anchor_edges():
    m = PiecewiseMap([(0, 0), (10, 12), (14, 12), (20, 18)])
    pr = sample_pairs(m, 0, 20, 1.0)
    ts = [a for a, _ in pr]
    assert 5.0 in ts and dict(pr)[5.0] == 6.0
    assert not any(10.0 <= a <= 14.0 for a in ts)       # 접힘 + 경계 제외
    assert 0.0 not in ts                                  # 앵커 경계 ±0.2 제외
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_vcompare.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'sg.vcompare'`

- [ ] **Step 3: 구현**

`sg/vcompare.py`
```python
"""변환표로 시각을 맞춘 프레임 대조."""
import subprocess
import numpy as np

W, H = 160, 90


def sample_pairs(part_map, t0, t1, step):
    anchors = [o for o, _ in part_map.pts]
    out, t = [], t0
    while t <= t1 + 1e-9:
        near = any(abs(t - a) <= 0.2 for a in anchors)
        collapsed = False
        for (o0, n0), (o1, n1) in zip(part_map.pts, part_map.pts[1:]):
            if o0 <= t <= o1 and n1 - n0 < 1e-6:
                collapsed = True
        if not near and not collapsed:
            out.append((round(t, 3), round(part_map(t), 3)))
        t += step
    return out


def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W).astype(np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    if d < 1e-6:
        return 1.0 if abs(a.mean() - b.mean()) < 8 else 0.0
    return float((a * b).sum() / d)
```

`scripts/compare_warped.py`
```python
"""usage: compare_warped.py <orig.mp4> <warped.mp4> <warp.json> <part_id> <out_dir> [--t0 0 --t1 120] [--step 1]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.timemap import PiecewiseMap
from sg.vcompare import sample_pairs, frame, ncc

orig, warped, wj, pid, out = sys.argv[1:6]
a = sys.argv[6:]
opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d
t0, t1, step = opt("--t0", 0.0), opt("--t1", 120.0), opt("--step", 1.0)
m = PiecewiseMap(json.load(open(wj))["parts"][pid]["anchors"])
os.makedirs(out, exist_ok=True)
pairs = sample_pairs(m, t0, t1, step)
sims = [(t, n, ncc(frame(orig, t), frame(warped, n))) for t, n in pairs]
bad = [{"t": t, "t_new": n, "sim": round(s, 3)} for t, n, s in sims if s < 0.85]
res = {"pairs": len(sims), "mean_sim": sum(s for _, _, s in sims) / max(len(sims), 1), "bad": bad}
json.dump(res, open(os.path.join(out, "compare.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "bad"}), "bad", len(bad), bad[:10])
```

- [ ] **Step 4: 단위 테스트 통과 확인**

Run: `python3 -m pytest -q tests/test_vcompare.py`
Expected: `1 passed`

- [ ] **Step 5: 테스트 패턴(×1.15/×0.9) AE 검증**

```bash
cd ~/Projects/semoji_global
python3 scripts/timewarp.py episodes/B209 pattern --test-pattern
scripts/ae/run.sh "$PWD/scripts/ae/localize.jsx"
cat episodes/B209/build/pattern/localize_log.json
python3 -c "
import json; w=json.load(open('episodes/B209/build/pattern/warp.json'))
from sg.timemap import PiecewiseMap
print(PiecewiseMap(w['parts']['mina']['anchors'])(120))"   # → 렌더 끝 시각 E
scripts/ae/render.sh "$PWD/episodes/B209/build/pattern/B209_pattern.aep" MAIN_KO 0 <E> "$PWD/episodes/B209/build/pattern/mina_0_120.mp4" 29.97 "H.264 - Match Render Settings - 15 Mbps"
python3 scripts/compare_warped.py episodes/B209/render/part_mina.mp4 episodes/B209/build/pattern/mina_0_120.mp4 episodes/B209/build/pattern/warp.json mina episodes/B209/build/pattern/cmp --t0 0 --t1 120
ffmpeg -v error -y -i episodes/B209/build/pattern/mina_0_120.mp4 -vf "fps=1/4,scale=320:-1,tile=6x6" -frames:v 1 episodes/B209/build/pattern/sheet.png
```
(`<E>`는 위 python 출력값을 그대로 넣는다.)
Expected: 로그 `errors: []`, `mean_sim ≥ 0.90`, `bad`는 전환 효과·wiggle 구간의 단발만(연속 3개 이상 없음). `sheet.png`를 열어 장면 순서가 원본과 같고 빈 화면·잘린 레이어가 없는지 눈으로 확인한다. 연속 bad가 있으면 해당 시각 프레임을 원본/변환본으로 뽑아 비교하고(`ffmpeg -ss <t> -frames:v 1`) 원인 규칙을 Task 6 `localize.jsx`에서 고친 뒤 Task 6 Step 6(항등)과 이 단계를 모두 다시 통과시킨다.

- [ ] **Step 6: 커밋**
```bash
git add sg/vcompare.py scripts/compare_warped.py tests/test_vcompare.py
git commit -m "feat: 변환 영상 대조 도구 — 테스트 패턴 워프 검증"
```

---

### Task 8: 런북 + 전체 테스트

**Files:**
- Create: `docs/RUNBOOK.md`

- [ ] **Step 1: 전체 테스트**

Run: `python3 -m pytest -q`
Expected: 모든 테스트 통과(Task 1~7 합계 28개).

- [ ] **Step 2: 런북 작성** — `docs/RUNBOOK.md`

```markdown
# 세모지 글로벌화 런북 (계획 1 범위)

## 0. 준비
- `caffeinate -d -u -t 21600 &` (AE 작업 중 화면보호기 방지)
- 디스크 여유 10GB 이상 (`df -h /System/Volumes/Data`)

## 1. 편 가져오기 (B209 기준, 이미 완료)
1. 기준본: `yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 -o episodes/<EP>/yt_master.mp4 <url>`
2. NAS aep 그래프: `scripts/ae/graph.jsx` (job: graph_job.json {aep: NAS 경로, out}) → `graph_nas.json`; 인벤토리 `inventory_full.jsx` → `inventory_nas.json`
3. 사용 파일만 복사: `python3 -I scripts/reach.py graph_nas.json <part comp id> 0 <dur>` → 파일 목록 → `episodes/<EP>/src/`(NFC)
4. `prep_main.jsx`(파트 컴프 고유 이름) → `fontmap.jsx`(SBAggroM→OTSBAggroM 등)
5. 프리미어: `python3 scripts/parse_prproj.py <prproj> > pr_timeline.json`
6. 재구성 검증: 파트 렌더(render.sh) → `assemble_pr.py` → `compare_video.py`(유튜브·NAS 최종본)

## 2. 마스터
- `episodes/<EP>/master_config.json` 작성(파트·컴프 id·내레이션 파일·유튜브 컷)
- `python3 scripts/master.py episodes/<EP>` → `master/edl.json`, `master/source.json`

## 3. 타임 워프
- `python3 scripts/timewarp.py episodes/<EP> <tag> --durs <구간별 새 길이 json>` (검증용 `--test-pattern`)
- `scripts/ae/run.sh $PWD/scripts/ae/localize.jsx` → `build/<tag>/<EP>_<tag>.aep`, `localize_log.json`
- 파트 렌더: `scripts/ae/render.sh <aep> <MAIN_*> 0 <dur_new> <out.mp4> 29.97 "H.264 - Match Render Settings - 15 Mbps"`
- 대조: `python3 scripts/compare_warped.py <원본 파트 렌더> <변환 렌더> build/<tag>/warp.json <part> <out_dir>`
```

- [ ] **Step 3: 커밋**
```bash
git add docs/RUNBOOK.md
git commit -m "docs: 런북(가져오기·마스터·타임 워프)"
```
