# 계획 3b: 효과음·BGM 워프 믹스 + "Semoji" 인트로·아웃트로 + 감정 영상 영어판 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코스트코(B209) 영어판을 "올릴 수 있는 완성본"으로 만든다. 프리미어 층의 효과음·BGM을 영어 길이에 맞춰 옮겨 원래 상대 레벨로 섞고, 남은 한글(인트로 로고·구독/좋아요, 감정 영상의 ㅋ, 아웃트로 로고)을 "Semoji" 영어판 에셋으로 바꾼다.

**Architecture:**
- 오디오: 프리미어 XML에서 클립 볼륨(Level, 키프레임)까지 읽는다(`sg/prproj.py`). BGM은 중첩 시퀀스를 풀어 마스터 시각 조각으로 만들고, 효과음 wav는 무음 기준 덩어리로 자른다(`sg/audiomix.py`). 둘 다 타임 워프 `T`로 옮겨 ffmpeg로 섞는다(`scripts/audio_mix.py`).
- 믹서가 맞는지는 **한국어 항등 믹스**(워프 없이 원래 재료로 다시 섞기)를 유튜브 원본 오디오와 대조해 먼저 증명한다.
- 영상 에셋: 공용 에셋을 언어별로 한 번만 만들고(`assets/global/<lang>/`), 대체 표 `assets/global/swap_<lang>.json`으로 모든 편에 적용한다.
  - 감정 영상 ㅋ: 원본에서 글자 덩어리 위치·각도·크기·투명도를 프레임마다 추적해, AE 텍스트 레이어 키프레임으로 다시 만든다.
  - 인트로 타이틀: 원본 위에 바탕색 판과 새 로고 글자를 얹고, 버튼은 셰이프+텍스트 레이어로 다시 만든다.
  - 아웃트로: 카드 위 손글씨 자리에 판과 텍스트를 얹는다.

**Tech Stack:** Python 3(numpy, opencv-python-headless, PIL), ffmpeg/ffprobe(loudnorm·ebur128), AE 2026 ExtendScript + aerender, macOS Vision OCR(`tools/ocr`).

**Spec:** `docs/superpowers/specs/2026-10-19-semoji-global-localization-design.md` §4.3, §7.3, §8, §9 (+ 사용자 결정 2026-10-20: 글로벌 채널 영문명 **"Semoji"**, 공용 감정 영상은 **영어판 에셋을 새로 제작**해 언어별 대체 표로 전 편 적용)

## Global Constraints
- 이미지 생성 금지 경로 없음: 이 계획의 에셋은 전부 AE(셰이프·텍스트·원본 영상 + 판)로 만든다. 이미지 생성이 필요해지면 코덱스 `$imagegen`만 쓴다(OpenAI API·image_gen.py 금지).
- NAS 원본 수정 금지. NAS 파일은 `episodes/<EP>/src/audio/`로 **복사**해서 쓴다. 디스크 여유 10GB 미만이면 중단(run.sh 규칙과 같음).
- AE 규칙(계획 1·2·3a와 같음): `run.sh`로만 실행, JSX는 실행 전 `node --check`, JSX 안 `//` 주석은 줄 끝 코드 뒤에 쓰지 않는다(괄호를 삼킨 사고), 결과 로그는 실행 전에 지우고 없으면 실패.
- 폰트: 고딕 `OTSBAggroB`(`~/Library/Fonts/SBAggroOTF-B.otf`), 손글씨 `Noteworthy-Bold`.
- 오디오 기준: 최종 mp4는 48kHz 스테레오 AAC 192k. 영어 내레이션은 한국어 원본 내레이션 wav와 같은 적분 라우드니스(LUFS)로 맞춘 뒤 다른 소리는 프리미어 상대 레벨 그대로.
- 대체 에셋은 원본과 **길이·해상도·프레임레이트가 같아야** 한다(워프·타이밍 불변). 다르면 빌드 실패.

## Review Focus
1. **BGM 볼륨 키프레임의 시간 기준**(클립 시작 기준인지 미디어 시각 기준인지) — 틀리면 페이드가 엉뚱한 곳에 생긴다. 한국어 항등 믹스 대조(Task 3)로 두 기준 중 맞는 쪽을 고르고, 그 값을 테스트로 고정한다.
2. **컷(유튜브에서 잘린 9초)에 걸친 BGM·효과음 조각** — 컷 안 부분은 사라지고, 컷 앞뒤는 이어져야 한다. 컷을 가로지르는 조각 테스트(Task 2).
3. **영어가 더 길어진 BGM 조각** — 같은 곡을 더 재생하되 소스 파일 끝을 넘으면 거기서 페이드로 끝난다. 소스 끝 초과 테스트(Task 2).
4. **감정 영상에서 ㅋ 덩어리가 겹치거나 잠깐 사라지는 프레임** — 추적이 다른 글자로 건너뛰면 "ha"가 튄다. 사라짐·재등장 테스트(Task 4).
5. **대체 표의 파일 이름이 NFD/NFC로 다르게 들어오는 경우**(NAS 경로는 NFD) — 매칭이 조용히 실패해 한글이 남는다. 정규화 테스트(Task 6)와 최종 한글 검사(Task 7).

---

### Task 1: 프리미어 오디오 클립 볼륨 파싱

**Files:**
- Modify: `sg/prproj.py` (`parse`의 audio item에 `gain`, `gain_keys`, `oid` 추가)
- Test: `tests/test_prproj.py`, Create fixture `tests/fixtures/level.prproj.xml`

**Interfaces:**
- Produces: `parse(path)` 의 audio item 딕셔너리에 `"gain": float`(선형 진폭, 기본 1.0), `"gain_keys": [[sec, lin], ...]`(키프레임 시각은 XML 값 그대로 초 단위로, 기준 해석은 Task 3에서), `"oid": str`(TrackItem ObjectID).

연결 구조(실측, `B_코스트코_음악작업.xml`): `AudioClipTrackItem` → `.//Components`(ObjectRef) → `AudioComponentChain` → `.//Component`(ObjectRef들) → `AudioFilterComponent` → `.//Param`(ObjectRef) → `AudioComponentParam` 중 `<Name>Level</Name>`. 값: `<CurrentValue>`(선형), `<Keyframes>` = `"ticks,value,...;ticks,value,...;"`(ticks/254016000000 = 초).

- [ ] **Step 1: 실제 XML에서 최소 픽스처 만들기** — `B_코스트코_음악작업.xml`에서 Level 키프레임이 있는 AudioClipTrackItem 하나와 그 참조 사슬(Track, TrackGroup, Sequence, SubClip, Clip, Source/Media, Components 사슬)만 남긴 XML을 `tests/fixtures/level.prproj.xml`로 저장(작은 스크립트로 ObjectRef를 따라가며 필요한 최상위 요소만 복사). 기존 `tests/fixtures/mini.prproj.xml` 형식과 같게.

- [ ] **Step 2: 실패하는 테스트**

```python
def test_audio_item_has_level_and_keyframes():
    seqs = parse(os.path.join(FIX, "level.prproj.xml"))
    items = [i for s in seqs for t in s["tracks"] if t["kind"] == "audio" for i in t["items"]]
    it = [i for i in items if i["gain_keys"]][0]
    assert abs(it["gain"] - 0.1412537) < 1e-4
    assert it["gain_keys"][0] == [round(2196171694198 / 254016000000.0, 4), 0.141253754497]
    assert it["gain_keys"][-1][1] == 0.0


def test_audio_item_without_level_defaults_to_unity():
    seqs = parse(os.path.join(FIX, "mini.prproj.xml"))
    a = [i for s in seqs for t in s["tracks"] if t["kind"] == "audio" for i in t["items"]]
    assert all(i["gain"] == 1.0 and i["gain_keys"] == [] for i in a)
```

- [ ] **Step 3:** `python3 -m pytest -q tests/test_prproj.py` → Expected: 2 FAIL (KeyError 'gain_keys')

- [ ] **Step 4: 구현** — `parse`의 item 루프에서 audio일 때:

```python
def level_of(item):
    """AudioClipTrackItem → (선형 gain, [[초, 선형], ...]). 없으면 (1.0, [])."""
    chain = ref(item.find(".//Components"))
    if chain is None:
        return 1.0, []
    for c in chain.iter("Component"):
        comp = ref(c)
        if comp is None:
            continue
        for p in comp.iter("Param"):
            prm = ref(p)
            if prm is None or prm.findtext("Name") != "Level":
                continue
            g = float(prm.findtext("CurrentValue") or 1.0)
            keys = []
            for kf in (prm.findtext("Keyframes") or "").split(";"):
                f = kf.split(",")
                if len(f) >= 2 and f[0]:
                    keys.append([round(int(f[0]) / TICKS, 4), float(f[1] or 0.0)])
            return g, keys
    return 1.0, []
```
  items 딕셔너리에 `"gain": g, "gain_keys": keys, "oid": item.get("ObjectID")` 추가(video는 `gain=1.0, gain_keys=[]`).

- [ ] **Step 5:** `python3 -m pytest -q` → Expected: 전부 PASS. `python3 scripts/parse_prproj.py episodes/B209/B_코스트코_음악작업.prproj > episodes/B209/pr_timeline.json` 재생성 후 BGM 트랙(audio 2·3)과 중첩 시퀀스 항목에 gain이 채워졌는지 출력으로 확인(최소 1개는 1.0이 아님).

- [ ] **Step 6: 커밋** `feat(prproj): 오디오 클립 Level·키프레임 파싱`

---

### Task 2: 오디오 조각 계산(`sg/audiomix.py`)

**Files:**
- Create: `sg/audiomix.py`, `tests/test_audiomix.py`

**Interfaces:**
- Consumes: `pr_timeline.json`(Task 1 형식), `sg.edl.pr_to_master(edl, p, clamp)`, `sg.timemap.PiecewiseMap`(호출 `T(m)`), `sg.audio.decode(path, sr)`.
- Produces:
  - `flatten(timeline, main_uid, track_indices) -> list[dict]` — 메인 시퀀스의 지정 audio 트랙을 중첩 시퀀스까지 풀어 `{"name","file","pr_in","pr_out","src_in","gain","gain_keys"}` 목록(프리미어 시각).
  - `to_master(pieces, edl) -> list[dict]` — 컷을 빼고 `m_in`, `m_out`, `src_in`(컷 뒤 조각은 src_in을 컷 길이만큼 이동) 부여. 컷에 완전히 들어간 조각은 버림, 걸친 조각은 둘로 나눔.
  - `warp_piece(p, T, src_len) -> {"t","dur","src_in","fade_out"}` — `t=T(m_in)`, `dur=T(m_out)-T(m_in)`; 소스 남은 길이 `src_len - src_in`보다 길면 그 길이로 줄이고 `fade_out=0.33`; 원래보다 짧아졌으면 `fade_out=0.33`(10프레임), 아니면 0.
  - `sound_chunks(x, sr, thresh_db=-45.0, min_silence=0.15) -> list[[a,b]]` — 효과음 wav 무음 기준 덩어리(초).
  - `place_chunk(a, b, file_pr_in, file_src_in, edl, T) -> {"t","src_in","dur"} | None` — wav 시각 [a,b] → 프리미어 → 마스터 → `T`; 덩어리 길이 유지, 컷 안이면 None.

- [ ] **Step 1: 실패하는 테스트**

```python
from sg.audiomix import flatten, to_master, warp_piece, sound_chunks, place_chunk
from sg.timemap import PiecewiseMap
import numpy as np

EDL = {"parts": [], "cuts": [{"pr_in": 100.0, "pr_out": 109.0}], "outro": None, "pr_length": 200.0, "length": 191.0}

def tl():
    return [{"sequence": "main", "uid": "M", "tracks": [
                {"kind": "audio", "index": 2, "items": [
                    {"start": 10.0, "end": 20.0, "in": 5.0, "out": 15.0, "name": "a.mp3", "file": "a.mp3", "seq_uid": None, "speed": 1.0, "gain": 0.5, "gain_keys": []},
                    {"start": 50.0, "end": 60.0, "in": 0.0, "out": 10.0, "name": "nest", "file": None, "seq_uid": "N", "speed": 1.0, "gain": 1.0, "gain_keys": []}]}]},
            {"sequence": "nest", "uid": "N", "tracks": [
                {"kind": "audio", "index": 0, "items": [
                    {"start": 2.0, "end": 8.0, "in": 30.0, "out": 36.0, "name": "b.mp3", "file": "b.mp3", "seq_uid": None, "speed": 1.0, "gain": 0.25, "gain_keys": []}]}]}]

def test_flatten_expands_nested_sequence_with_offsets_and_gain():
    p = flatten(tl(), "M", [2])
    assert [(x["name"], x["pr_in"], x["pr_out"], x["src_in"]) for x in p] == [("a.mp3", 10.0, 20.0, 5.0), ("b.mp3", 52.0, 58.0, 30.0)]
    assert p[1]["gain"] == 0.25          # 중첩 안 클립 gain × 바깥 클립 gain(1.0)

def test_to_master_splits_piece_across_cut():
    p = to_master([{"name": "c", "file": "c", "pr_in": 95.0, "pr_out": 115.0, "src_in": 0.0, "gain": 1.0, "gain_keys": []}], EDL)
    assert [(x["m_in"], x["m_out"], x["src_in"]) for x in p] == [(95.0, 100.0, 0.0), (100.0, 106.0, 14.0)]

def test_warp_piece_longer_than_source_is_capped_with_fade():
    T = PiecewiseMap([[0, 0], [100, 150]])
    w = warp_piece({"m_in": 10.0, "m_out": 30.0, "src_in": 5.0}, T, src_len=30.0)
    assert w["t"] == 15.0 and w["dur"] == 25.0 and w["fade_out"] > 0   # 원래 30 > 남은 소스 25

def test_warp_piece_shorter_gets_fade_and_longer_has_none():
    T = PiecewiseMap([[0, 0], [100, 80]])
    assert warp_piece({"m_in": 0.0, "m_out": 10.0, "src_in": 0.0}, T, 100.0)["fade_out"] > 0
    T = PiecewiseMap([[0, 0], [100, 120]])
    assert warp_piece({"m_in": 0.0, "m_out": 10.0, "src_in": 0.0}, T, 100.0)["fade_out"] == 0

def test_sound_chunks_splits_on_silence():
    sr = 16000
    x = np.zeros(sr * 3, np.float32); x[sr // 2: sr] = 0.5; x[2 * sr: 2 * sr + sr // 4] = 0.5
    c = sound_chunks(x, sr)
    assert len(c) == 2 and abs(c[0][0] - 0.5) < 0.05 and abs(c[1][1] - 2.25) < 0.05

def test_place_chunk_inside_cut_is_dropped():
    T = PiecewiseMap([[0, 0], [200, 200]])
    assert place_chunk(101.0, 102.0, 0.0, 0.0, EDL, T) is None
    assert place_chunk(110.0, 111.0, 0.0, 0.0, EDL, T)["t"] == 101.0
```

- [ ] **Step 2:** `python3 -m pytest -q tests/test_audiomix.py` → Expected: FAIL (ModuleNotFoundError sg.audiomix)

- [ ] **Step 3: 구현** `sg/audiomix.py`

```python
"""프리미어 층 오디오(효과음 wav·BGM) → 마스터 시각 조각 → 워프 배치."""
import numpy as np
from sg.edl import pr_to_master

FADE = 10 / 29.97


def flatten(timeline, main_uid, track_indices, _off=0.0, _gain=1.0, _win=None):
    seqs = {s["uid"]: s for s in timeline}
    out = []
    for t in seqs[main_uid]["tracks"]:
        if t["kind"] != "audio" or (track_indices is not None and t["index"] not in track_indices):
            continue
        for it in t["items"]:
            a, b = it["start"], it["end"]
            if _win is not None:                       # 중첩 시퀀스: 바깥 클립이 보여 주는 구간만
                a, b = max(a, _win[0]), min(b, _win[1])
                if b <= a:
                    continue
            if it["seq_uid"]:
                shift = _off + it["start"] - it["in"]
                out += flatten(timeline, it["seq_uid"], None, shift, _gain * it.get("gain", 1.0), (it["in"], it["out"]))
                continue
            out.append({"name": it["name"], "file": it["file"], "pr_in": round(_off + a, 4), "pr_out": round(_off + b, 4),
                        "src_in": round(it["in"] + (a - it["start"]), 4), "gain": _gain * it.get("gain", 1.0),
                        "gain_keys": it.get("gain_keys", [])})
    return sorted(out, key=lambda x: x["pr_in"])


def to_master(pieces, edl):
    out = []
    for p in pieces:
        segs, a = [], p["pr_in"]
        for c in sorted(edl["cuts"], key=lambda c: c["pr_in"]):
            if c["pr_out"] <= a or c["pr_in"] >= p["pr_out"]:
                continue
            if c["pr_in"] > a:
                segs.append((a, c["pr_in"]))
            a = max(a, c["pr_out"])
        if a < p["pr_out"]:
            segs.append((a, p["pr_out"]))
        for s, e in segs:
            out.append({**p, "m_in": round(pr_to_master(edl, s), 4), "m_out": round(pr_to_master(edl, e), 4),
                        "src_in": round(p["src_in"] + (s - p["pr_in"]), 4)})
    return out


def warp_piece(p, T, src_len):
    t0, t1 = T(p["m_in"]), T(p["m_out"])
    dur, orig = t1 - t0, p["m_out"] - p["m_in"]
    room = src_len - p["src_in"]
    fade = FADE if (dur < orig - 1e-6 or dur > room + 1e-6) else 0.0
    return {"t": round(t0, 4), "dur": round(min(dur, room), 4), "src_in": p["src_in"], "fade_out": round(fade, 4)}


def sound_chunks(x, sr, thresh_db=-45.0, min_silence=0.15):
    hop = int(sr * 0.01)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    loud = 20 * np.log10(rms) > thresh_db
    chunks, start, quiet = [], None, 0
    for i, v in enumerate(loud):
        if v:
            start = i if start is None else start
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet * 0.01 >= min_silence:
                chunks.append([round(start * 0.01, 3), round((i - quiet + 1) * 0.01, 3)]); start, quiet = None, 0
    if start is not None:
        chunks.append([round(start * 0.01, 3), round(n * 0.01, 3)])
    return chunks


def place_chunk(a, b, file_pr_in, file_src_in, edl, T):
    pa = file_pr_in + (a - file_src_in)
    m = pr_to_master(edl, pa, clamp=False)
    if m is None:
        return None
    return {"t": round(T(m), 4), "src_in": a, "dur": round(b - a, 4)}
```

- [ ] **Step 4:** `python3 -m pytest -q` → Expected: 전부 PASS

- [ ] **Step 5: 커밋** `feat(audio): 프리미어 오디오 조각 펼치기·컷 처리·워프 배치`

---

### Task 3: 오디오 재료 가져오기 + 한국어 항등 믹스 검증 + 영어 믹스

**Files:**
- Create: `scripts/audio_fetch.py`, `scripts/audio_mix.py`, `sg/mixgraph.py`, `tests/test_mixgraph.py`
- Modify: `scripts/preview.py`(있으면 `render/<lang>/mix.wav`를 오디오로 사용), `episodes/B209/master_config.json`(`"audio": {...}` 추가)

**Interfaces:**
- Consumes: Task 1 `pr_timeline.json`, Task 2 함수들, `build/<lang>/warp.json`, `render/<lang>/narration.wav`(preview.py가 만드는 내레이션 트랙), `render/<lang>/part_*.mp4`의 오디오(AE 효과음).
- Produces:
  - `scripts/audio_fetch.py <EP>` → `episodes/<EP>/src/audio/` 에 효과음 wav 3개, BGM mp3 8개, `Sand_Castle.mp3` 복사. 파일 위치: prproj `file` 경로를 NAS(`/Volumes/jleavens/...`, `\\jleavens_NAS\jleavens\` → `/Volumes/jleavens/`)로 바꿔 찾고, `C:\Users\niceg\Documents\Epidemic Sound\Music\<이름>` 이거나 경로가 없으면(중첩 시퀀스) `/Volumes/jleavens/002_intra/2.edit_source/유투브용 무료음악/epidemic_sound/Music/` 아래에서 파일명(NFC 비교)으로 찾음. 못 찾으면 목록 출력 후 실패.
  - `sg/mixgraph.py`: `volume_expr(gain, keys, key_base, clip_src_in, clip_t)` → ffmpeg `volume` 필터 표현식 문자열(키프레임 사이 선형 보간, 출력 타임라인 기준 `t`), `entry(file, t, src_in, dur, gain, keys, key_base, fade_out)` → 입력 인자 목록과 필터 문자열 한 쌍.
  - `scripts/audio_mix.py <EP> ko-identity [--key-base media|clip]` → `render/ko/identity_mix.wav` + 유튜브 원본(`yt_master.mp4`) 오디오와 대조 출력: 0.5초 창 RMS 포락선 상관계수(전체, 구간별 30초 창 최솟값).
  - `scripts/audio_mix.py <EP> <lang>` → `render/<lang>/mix.wav`(내레이션 + AE 효과음(파트 mp4 오디오 이어붙임) + 효과음 wav 덩어리 + BGM 조각 + 아웃트로 BGM), 내레이션은 한국어 원본 내레이션 wav와 같은 LUFS로 맞춤.

- [ ] **Step 1: 실패하는 테스트**(`tests/test_mixgraph.py`)

```python
from sg.mixgraph import volume_expr, entry

def test_volume_expr_constant_gain():
    assert volume_expr(0.5, [], "clip", 0.0, 10.0) == "0.5"

def test_volume_expr_keyframes_clip_base_are_offset_by_placement():
    e = volume_expr(1.0, [[2.0, 1.0], [4.0, 0.0]], "clip", 0.0, 10.0)
    # 출력 시각 12~14초에서 1→0 선형
    assert "between(t,12.0,14.0)" in e and "gte(t,14.0)" in e

def test_volume_expr_media_base_subtracts_src_in():
    e = volume_expr(1.0, [[7.0, 1.0], [9.0, 0.0]], "media", 5.0, 10.0)
    assert "between(t,12.0,14.0)" in e

def test_entry_trims_source_and_delays():
    args, flt = entry("x.mp3", 3.0, 1.5, 2.0, 0.5, [], "clip", 0.0)
    assert args == ["-ss", "1.5", "-t", "2.0", "-i", "x.mp3"]
    assert "adelay=3000|3000" in flt and "volume=" in flt
```

- [ ] **Step 2:** `python3 -m pytest -q tests/test_mixgraph.py` → Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 구현** `sg/mixgraph.py`

```python
"""ffmpeg 오디오 믹스 조각: 소스 자르기·지연·볼륨(키프레임 선형)·페이드."""


def volume_expr(gain, keys, key_base, clip_src_in, clip_t):
    if not keys:
        return f"{gain:g}"
    pts = [((k - clip_src_in if key_base == "media" else k) + clip_t, v) for k, v in keys]
    pts.sort()
    expr = f"{pts[-1][1]:g}"
    for (t0, v0), (t1, v1) in reversed(list(zip(pts, pts[1:]))):
        lin = f"({v0:g}+({v1:g}-{v0:g})*(t-{t0})/{max(1e-6, t1 - t0)})"
        expr = f"if(between(t,{t0},{t1}),{lin},if(gte(t,{t1}),{expr},{expr}))"
    return f"if(lt(t,{pts[0][0]}),{pts[0][1]:g},{expr})"


def entry(file, t, src_in, dur, gain, keys, key_base, fade_out, k=0):
    args = ["-ss", f"{src_in}", "-t", f"{dur}", "-i", file]
    ms = int(round(t * 1000))
    flt = f"aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}"
    flt += f",volume='{volume_expr(gain, keys, key_base, src_in, t)}':eval=frame"
    if fade_out > 0:
        flt += f",afade=t=out:st={t + dur - fade_out:.3f}:d={fade_out:.3f}"
    return args, flt
```

- [ ] **Step 4:** `python3 -m pytest -q` → Expected: 전부 PASS

- [ ] **Step 5: 재료 가져오기** — `scripts/audio_fetch.py` 작성(위 Produces 규칙) → `python3 scripts/audio_fetch.py episodes/B209` → Expected: `copied 12, missing 0`. `episodes/B209/master_config.json`에 추가:

```json
"audio": {"main_seq_uid": "54a2a221-da6d-4036-aa04-acd3eea793c1", "sfx_track": 1, "bgm_tracks": [2, 3],
          "outro_bgm": "Sand_Castle.mp3", "narration_ref": "B209_코스트코_오디오원본.wav"}
```

- [ ] **Step 6: 한국어 항등 믹스** — `scripts/audio_mix.py`의 `ko-identity` 모드: 워프 = 항등(`PiecewiseMap.identity()`), 내레이션·AE 효과음 = 프리미어 audio 0트랙 그대로(파트 "음악전" mp4 오디오 + 원본 녹음 wav + Sand_Castle; `/Volumes/jleavens/...`에서 직접 읽기), 효과음 = audio 1트랙, BGM = audio 2·3(+중첩). 실행:
  `python3 scripts/audio_mix.py episodes/B209 ko-identity --key-base clip` 와 `--key-base media` 둘 다.
  Expected: 둘 중 한쪽이 전체 상관 ≥ 0.95 이고 30초 창 최솟값 ≥ 0.85. 높은 쪽을 `master_config.json` `audio.key_base`에 기록하고, Task 1 픽스처 키프레임에 대해 그 기준으로 계산한 페이드 위치를 `tests/test_mixgraph.py`에 테스트로 하나 더 고정(Review Focus 1). 둘 다 미달이면 원인(트랙 볼륨, 패닝, 누락 클립)을 출력으로 찾고 고친 뒤 다시 — 통과 전에는 다음 단계로 가지 않는다.

- [ ] **Step 7: 영어 믹스** — `python3 scripts/audio_mix.py episodes/B209 en` → `render/en/mix.wav`.
  - 내레이션: `render/en/narration.wav`에 gain을 곱해 적분 LUFS를 한국어 원본 녹음 wav(`narration_ref`)의 LUFS와 같게(ffmpeg `ebur128`로 측정).
  - AE 효과음: `part_*.mp4` 오디오를 파트 순서대로 이어붙인 트랙(영상과 같은 시각).
  - 효과음 wav: 파일별 `sound_chunks` → 각 덩어리 `place_chunk` → `entry`.
  - BGM: `flatten`→`to_master`→`warp_piece`→`entry`(gain·키프레임·fade_out).
  - 아웃트로 BGM: 프리미어 위치 그대로(마스터 끝 기준 `T(length)` 뒤).
  Expected: 길이 = 미리보기 영상 길이 ±0.05초, 클리핑(샘플 |x|≥1.0) 0, 출력 마지막 줄에 각 층 개수(`sfx_chunks N, bgm_pieces M`).

- [ ] **Step 8:** `scripts/preview.py` 수정 — `render/<lang>/mix.wav`가 있으면 그것을 최종 오디오로(없으면 지금처럼 내레이션만). `python3 scripts/preview.py episodes/B209 en` → 미리보기 재생성. 30초 클립 3개(오프닝 0–30, 컷 직후 900–930(마스터 시각을 새 시각으로 바꿔서), 아웃트로 직전)를 `render/en/review/`에 잘라 사용자 검수용으로 둠.

- [ ] **Step 9: 커밋** `feat(audio): 효과음·BGM 워프 믹스, 한국어 항등 믹스 검증`

---

### Task 4: 감정 영상 영어판(ㅋ → "ha") 

**Files:**
- Create: `sg/blobs.py`, `tests/test_blobs.py`, `scripts/build_global_assets.py`, `scripts/ae/build_emotion_en.jsx`, `assets/global/swap_en.json`

**Interfaces:**
- Produces:
  - `track_blobs(frames) -> list[list[dict|None]]` — `frames`: RGBA numpy 배열 목록. 결과 `tracks[k][f]` = k번째 덩어리의 프레임 f 상태 `{"cx","cy","w","h","angle","alpha"}` 또는 사라졌으면 None. 덩어리 = 알파>20 연결 성분(면적 ≥ 50px), 프레임 간 매칭은 직전 위치 최근접(거리 < 덩어리 크기의 1.5배), 새로 나타나면 새 트랙.
  - `assets/global/en/세모지감정14_킥킥.mov` — 원본과 같은 1920×1080, 같은 길이·fps, 알파 포함(AE "High Quality with Alpha").
  - `assets/global/swap_en.json`: `{"세모지감정14_킥킥.mov": "assets/global/en/세모지감정14_킥킥.mov", ...}` (키는 NFC 파일명)

- [ ] **Step 1: 실패하는 테스트**

```python
import numpy as np
from sg.blobs import track_blobs

def frame(points):
    a = np.zeros((200, 300, 4), np.uint8)
    for x, y in points:
        a[y - 8:y + 8, x - 8:x + 8] = (40, 40, 160, 255)
    return a

def test_two_blobs_tracked_across_motion():
    fr = [frame([(50, 50), (200, 100)]), frame([(55, 52), (196, 104)]), frame([(60, 54), (192, 108)])]
    tr = track_blobs(fr)
    assert len(tr) == 2
    a = [s for s in tr if s[0]["cx"] < 100][0]
    assert [round(s["cx"]) for s in a] == [50, 55, 60]

def test_blob_disappears_and_returns_on_same_track():
    fr = [frame([(50, 50)]), frame([]), frame([(53, 51)])]
    tr = track_blobs(fr)
    assert len(tr) == 1 and tr[0][1] is None and round(tr[0][2]["cx"]) == 53
```

- [ ] **Step 2:** `python3 -m pytest -q tests/test_blobs.py` → Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 구현** `sg/blobs.py`

```python
"""투명 배경 애니메이션의 글자 덩어리 추적(위치·크기·각도·투명도)."""
import cv2
import numpy as np


def _blobs(rgba, min_area=50):
    a = rgba[:, :, 3]
    n, lab, st, cen = cv2.connectedComponentsWithStats((a > 20).astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_area:
            continue
        ys, xs = np.where(lab == i)
        (cx, cy), (w, h), ang = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
        out.append({"cx": float(cen[i][0]), "cy": float(cen[i][1]), "w": float(max(w, h)), "h": float(min(w, h)),
                    "angle": float(ang), "alpha": float(a[lab == i].max()) / 255.0})
    return out


def track_blobs(frames):
    tracks, last = [], []          # last[k] = 마지막으로 본 상태
    for f, rgba in enumerate(frames):
        for t in tracks:
            t.append(None)
        for b in _blobs(rgba):
            best, bd = None, None
            for k, l in enumerate(last):
                if tracks[k][f] is not None:
                    continue
                d = np.hypot(b["cx"] - l["cx"], b["cy"] - l["cy"])
                if d < 1.5 * max(l["w"], 8) and (bd is None or d < bd):
                    best, bd = k, d
            if best is None:
                tracks.append([None] * f + [b]); last.append(b)
            else:
                tracks[best][f] = b; last[best] = b
    return tracks
```

- [ ] **Step 4:** `python3 -m pytest -q` → Expected: 전부 PASS

- [ ] **Step 5: AE 빌드** — `scripts/build_global_assets.py en emotion`:
  1) 원본 `세모지감정14_킥킥.mov`(B209 `src/(Footage)` 안)에서 전 프레임을 RGBA PNG로 추출(`ffmpeg -i … -pix_fmt rgba`) → `track_blobs` → 트랙별 프레임 키 목록.
  2) 각 덩어리 색(채움=알파>200 중앙값, 외곽선=가장자리 색)과 원본 ㅋ의 획 굵기에서 글자 크기 = 덩어리 짧은 변 × 1.1.
  3) `scripts/ae/build_emotion_en_job.json` = `{"w","h","fps","dur","out","tracks":[[{"t","cx","cy","angle","scale","alpha"}|null...]], "text":"ha", "font":"OTSBAggroB", "fill":[r,g,b], "stroke":[r,g,b], "stroke_w"}`.
  4) `build_emotion_en.jsx`: 새 컴프(원본과 같은 크기·fps·길이), 트랙마다 텍스트 레이어 "ha" — 위치·회전·스케일·불투명도 키프레임(None 구간은 불투명도 0), 렌더 큐 "High Quality with Alpha" → 저장 `assets/global/en/build/emotion_en.aep` → `aerender`.
  Expected: `assets/global/en/세모지감정14_킥킥.mov` 생성, ffprobe 길이·크기·fps가 원본과 같음, 원본/영어판 4프레임 비교 시트 `assets/global/en/review_emotion.png`에서 "ha" 3개가 ㅋ 자리를 따라 움직임(눈으로 확인).

- [ ] **Step 6:** `assets/global/swap_en.json`에 항목 추가, `.gitignore`에 `assets/global/*/*.mov`, `assets/global/*/build/` 추가(레시피 jsx·json과 swap 표는 커밋). 커밋 `feat(assets): 감정 영상 ㅋ 영어판(ha) — 덩어리 추적 + AE 텍스트 키프레임`

---

### Task 5: "Semoji" 인트로 타이틀·아웃트로

**Files:**
- Create: `scripts/ae/build_title_outro_en.jsx`, `sg/regions.py`, `tests/test_regions.py`
- Modify: `scripts/build_global_assets.py`(`title`, `outro` 모드), `assets/global/swap_en.json`

**Interfaces:**
- Produces:
  - `static_from(frames, box, tol=6.0) -> float` — 영역 `box=[x,y,w,h]`이 그 시각 이후 계속 같은(평균 절대차 < tol) 첫 프레임 시각(초 = 인덱스/fps). 판을 언제부터 덮을지 정하는 데 씀.
  - `appear_time(frames, box, bg, tol=12.0) -> float` — 영역이 바탕색과 처음 달라지는 시각(버튼 등장 시각).
  - `assets/global/en/세모지타이틀.mov`(3.8038초, 1920×1080, 원본 오디오 포함), `assets/global/en/outro.mov`(원본과 같은 길이 19.9866초).

- [ ] **Step 1: 실패하는 테스트**

```python
import numpy as np
from sg.regions import static_from, appear_time

def test_static_from_finds_when_region_stops_changing():
    fr = [np.full((50, 50, 3), v, np.uint8) for v in (0, 40, 80, 120, 120, 120)]
    assert static_from(fr, [10, 10, 20, 20], fps=1.0) == 3.0

def test_appear_time_detects_first_difference_from_background():
    bg = (250, 250, 250)
    fr = [np.full((50, 50, 3), bg, np.uint8) for _ in range(5)]
    fr[3][10:30, 10:30] = (120, 120, 120); fr[4][10:30, 10:30] = (120, 120, 120)
    assert appear_time(fr, [10, 10, 20, 20], bg, fps=1.0) == 3.0
```

- [ ] **Step 2:** `python3 -m pytest -q tests/test_regions.py` → Expected: FAIL

- [ ] **Step 3: 구현** `sg/regions.py`

```python
"""영상 프레임에서 영역이 고정되는 시각·나타나는 시각."""
import numpy as np


def _crop(f, box):
    x, y, w, h = box
    return f[y:y + h, x:x + w].astype(np.float32)


def static_from(frames, box, tol=6.0, fps=29.97):
    last = _crop(frames[-1], box)
    k = len(frames) - 1
    while k > 0 and np.abs(_crop(frames[k - 1], box) - last).mean() < tol:
        k -= 1
    return round(k / fps, 4)


def appear_time(frames, box, bg, tol=12.0, fps=29.97):
    for k, f in enumerate(frames):
        if np.abs(_crop(f, box) - np.array(bg, np.float32)).mean() > tol:
            return round(k / fps, 4)
    return None
```

- [ ] **Step 4:** `python3 -m pytest -q` → Expected: 전부 PASS

- [ ] **Step 5: 영역 측정** — `scripts/build_global_assets.py en title`가 원본 타이틀 mov 전 프레임에서 OCR(`tools/ocr`, 마지막 프레임)로 다음 상자를 얻는다: 로고 글자 영역(세상의/모 든/지 식 6글자를 감싸는 상자 + 여백 8px), "구독" 버튼 전체(체크 아이콘 포함 회색 사각형: OCR 상자를 왼쪽으로 버튼 높이×1.4만큼, 위아래 6px 넓힘), "좋아요" 영역(엄지 아이콘 포함). 각 상자의 `static_from`, `appear_time`과 바탕색(상자 밖 둘레 중앙값)을 job에 기록. Expected 출력: 상자 3개와 시각 3개(로고 글자는 0~0.5초 사이에 고정, 버튼은 0.5초 이후 등장 — 실제 값 출력).

- [ ] **Step 6: AE 빌드** — `build_title_outro_en.jsx`(job: `{mode, src, w, h, fps, dur, out, plates:[{box, color, from}], texts:[{text, font, size, color, cx, cy, from, pop}], buttons:[...]}`):
  - **타이틀**: 원본 mov 레이어(오디오 켬) → 판(솔리드, 바탕색) 3개: 로고 글자 상자(시각 0부터), 버튼 두 상자(시각 0부터 끝까지 — 원래 버튼을 완전히 가림).
    - 로고 텍스트 "Semoji": 로고 글자 상자 가운데, 원본 글자색(회색, 상자 안 어두운 픽셀 중앙값), OTSBAggroB, 크기는 상자 폭의 90%에 맞춤, `from`=로고 글자 `static_from`.
    - 버튼 재구성: 원래 위치·크기의 둥근 사각형 셰이프(회색 테두리, 안쪽 체크 칸) + "Subscribe" 텍스트, 엄지 아이콘 대신 원본 엄지 영역 프리컴프(원본 mov를 마스크로 잘라 쓰고 "좋아요" 글자 부분만 판으로 덮음) + "Like" 텍스트. 등장은 `appear_time`에 0.2초 스케일 팝(0→110→100%).
  - **아웃트로**: 원본 outro.mov 레이어 → 카드 위 "세상의 모든지식" 상자(OCR)에 판(카드 색, `from`=0) → "Semoji" 텍스트(Noteworthy-Bold, 원본 글자색 녹색 계열 = 상자 안 진한 픽셀 중앙값, 상자 폭 80%).
  - 렌더 → `assets/global/en/세모지타이틀.mov`(오디오는 ffmpeg로 원본 오디오 다시 입힘: `-map 0:v -map 1:a -c copy`), `assets/global/en/outro.mov`.
  Expected: 두 파일 길이·크기·fps가 원본과 같음, 비교 시트 `assets/global/en/review_title.png`, `review_outro.png`(원본/영어판 4프레임)에서 한글 0, 버튼 등장 타이밍이 원본과 같음(눈으로 확인), `tools/ocr`로 두 영상 1초 간격 검사 시 한글 0.

- [ ] **Step 7:** `swap_en.json`에 `"세모지타이틀.mov"`, `"세모지 아웃트로_최종.mov": "assets/global/en/outro.mov"` 추가. 커밋 `feat(assets): Semoji 인트로 타이틀·아웃트로 영어판`

---

### Task 6: 대체 표 적용(AE footage 교체) + 미리보기 아웃트로 교체

**Files:**
- Create: `scripts/ae/swap_assets.jsx`, `scripts/swap_assets.py`, `tests/test_swap.py`, `scripts/rebuild_lang.sh`
- Modify: `scripts/preview.py`(아웃트로 = `swap_<lang>.json`에 있으면 그 파일)

**Interfaces:**
- Consumes: `assets/global/swap_<lang>.json`, `build/<lang>/<EP>_<lang>_text_raster.aep`
- Produces:
  - `swap_targets(names, table) -> dict[name, path]` — AE footage 파일명 목록과 대체 표를 NFC로 정규화해 매칭.
  - `scripts/swap_assets.py <EP> <lang>` → AE에서 매칭 footage를 `item.replace(new File(path))` → `build/<lang>/<EP>_<lang>_swapped.aep`, 로그 `{replaced:[...], missing:[...], mismatch:[...]}`(대체 파일 길이·크기가 원본과 다르면 mismatch → 실패).
  - `scripts/rebuild_lang.sh <EP> <lang>`: raster_apply → swap_assets → timewarp(`--aep …_swapped.aep`) → localize → subtitles → 파트 렌더 → preview → audio_mix → preview(믹스 반영) → qa_hangul(scratchpad의 rebuild 스크립트를 저장소로 옮겨 정식화).

- [ ] **Step 1: 실패하는 테스트**

```python
import unicodedata
from scripts.swap_assets import swap_targets

def test_nfd_footage_name_matches_nfc_table_key():
    nfd = unicodedata.normalize("NFD", "세모지감정14_킥킥.mov")
    t = swap_targets([nfd, "other.mov"], {"세모지감정14_킥킥.mov": "/x/en.mov"})
    assert t == {nfd: "/x/en.mov"}
```

- [ ] **Step 2:** `python3 -m pytest -q tests/test_swap.py` → Expected: FAIL

- [ ] **Step 3: 구현** — `swap_targets`:

```python
def swap_targets(names, table):
    norm = {unicodedata.normalize("NFC", k): v for k, v in table.items()}
    return {n: norm[unicodedata.normalize("NFC", n)] for n in names if unicodedata.normalize("NFC", n) in norm}
```
  `swap_assets.py`: 인벤토리(`inventory_nas.json`의 footage 이름)로 대상 계산 → job(`{aep, save_as, out, items:[{id, path, w, h, dur}]}`) → `run.sh swap_assets.jsx`(로그 삭제 후 실행, 없으면 실패). `swap_assets.jsx`: id로 FootageItem 찾고 `item.replace(new File(path))`, 교체 후 `item.duration`·`width`·`height`가 job 값과 다르면 mismatch. `preview.py`: 아웃트로 경로를 `swap_<lang>.json`의 `edl.outro.clip` 항목으로(있을 때).

- [ ] **Step 4:** `python3 -m pytest -q` → Expected: 전부 PASS. JSX `node --check` 통과.

- [ ] **Step 5:** `scripts/rebuild_lang.sh episodes/B209 en` 실행 → Expected: swap 로그 replaced ≥ 2(타이틀·감정14), missing 0, mismatch 0; 미리보기 길이 886.15±0.1초.

- [ ] **Step 6: 커밋** `feat(assets): 언어별 에셋 대체 표 적용 + 재빌드 스크립트 정식화`

---

### Task 7: 최종 검수 게이트

**Files:**
- Modify: `scripts/qa_hangul.py`(`--step` 기본 0.5초로), `docs/RUNBOOK.md`(계획 3a·3b 절차 추가)

- [ ] **Step 1:** `python3 scripts/qa_hangul.py episodes/B209 en --gate --step 0.5` → Expected: 신뢰도 1.0 또는 한글 2자 이상 항목 0건(브랜드 예외 외). 남으면 시트로 원인 분류 후 Task 2~6 보완 또는 사용자 보고.
- [ ] **Step 2:** 오디오 확인 — `ffmpeg -i render/en/B209_EN_preview.mp4 -af ebur128 -f null -` 로 통합 LUFS 출력, 클리핑 0, 컷 직후·아웃트로 30초 클립을 `render/en/review/`에 두고 사용자에게 들어볼 구간 안내.
- [ ] **Step 3:** `docs/RUNBOOK.md`에 `rebuild_lang.sh`, 에셋 빌드(`build_global_assets.py en emotion|title|outro`), 오디오(`audio_fetch.py`, `audio_mix.py ko-identity|<lang>`) 절차와 B209 검증 수치 기록. 커밋 `docs: 런북 — 래스터·오디오·글로벌 에셋`
