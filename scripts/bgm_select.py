#!/usr/bin/env python3
"""챕터별 BGM 선곡·정리 — 세모지 통합보고 §7-3 을 스크립트 사양으로 옮긴 것.

사양
  1. 챕터 하나에 곡 하나. 곡을 이어 붙이지 않는다(곡이 바뀌는 게 들린다).
  2. 곡 길이는 **실제로 디코드한 길이**로 잰다 — 파일 크기로 추정 금지(VBR).
     (브레이크를 잘라 낸 뒤의 길이)가 챕터 길이 이상인 곡만 후보.
  3. 곡 안의 브레이크(1~2마디 동안 −8dB 이상 빠짐)는 끊김으로 들린다 → 0.1초 단위로
     찾아(0.5초 단위는 놓친다) 그 구간을 잘라 내고 0.25초 크로스페이드로 잇는다.
     마디 길이는 파일 이름 `카테고리_분위기_BPM_번호` 의 BPM(없으면 120)으로 잡는다.
  4. 챕터 길이로 자르고 페이드 인 0.6초·아웃 1.2초.
  5. −14.4 LUFS 로 정규화(ebur128 측정 → 이득) 후 **다시 측정해 기록**한다
     (정규화 실수로 12dB 작게 들어간 사고). AE 에서는 레이어 −25dB 로 깐다.
  6. 같은 곡을 두 챕터에 쓰지 않는다. 분위기 낱말(--mood)이 파일 이름에 맞는 곡 우선,
     그다음 자를 브레이크가 적은 곡, 그다음 길이가 챕터에 가까운 곡.

출력: <out>/bgm_ch{N}.wav 와 <out>/bgm_manifest.json
     (chapter, track, 디코드 길이, bpm, 브레이크·자른 구간, LUFS 전/후, 이득, 페이드, 레이어 −25dB)

    python3 scripts/bgm_select.py --library <곡 폴더> --timing <timing.json> -o <out_dir>
                                  [--chapters chapters.json] [--mood 1:cinematic,3:calm] [--dry-run]

--chapters 는 [{"chapter": 1, "start": 0.0, "end": 118.9, "mood": "cinematic"}] — 마스터에서
챕터 카드 시작 ~ 다음 카드 시작 구간을 줄 때 쓴다. 없으면 timing.json 의 챕터 음성 길이.
ffmpeg 가 없으면 아무것도 하지 않고 끝낸다(사양만).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

TARGET_LUFS = -14.4
LAYER_DB = -25.0
FADE_IN, FADE_OUT = 0.6, 1.2
XFADE = 0.25
HOP = 0.1            # 레벨 검사 해상도(초)
DROP_DB = 8.0
SR = 8000            # 분석용 디코드 샘플레이트
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg"))


def bpm_from_name(name: str, default: int = 120) -> int:
    for part in reversed(Path(name).stem.split("_")):
        if part.isdigit() and 50 <= int(part) <= 220:
            return int(part)
    return default


def decode_mono(path: Path, sr: int = SR) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                        "-f", "s16le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0


def levels_db(x: np.ndarray, sr: int = SR, hop: float = HOP) -> np.ndarray:
    n = int(round(sr * hop))
    k = len(x) // n
    if k == 0:
        return np.zeros(0)
    rms = np.sqrt(np.mean(x[:k * n].reshape(k, n) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def detect_breaks(lv: np.ndarray, bpm: int = 120, hop: float = HOP, drop_db: float = DROP_DB,
                  ref_sec: float = 4.0, edge_sec: float = 3.0) -> list[tuple[float, float]]:
    """레벨이 앞 ref_sec 중앙값보다 drop_db 이상 빠진 구간 중 길이가 1~2마디인 것.

    곡의 처음·끝 edge_sec 은 보지 않는다(인트로·아웃트로). 반환 [(시작초, 끝초)]."""
    bar = 4 * 60.0 / bpm
    lo, hi = 0.75 * bar, 2.25 * bar
    n, ref_n, edge = len(lv), int(ref_sec / hop), int(edge_sec / hop)
    out, i = [], max(edge, ref_n)
    while i < n - edge:
        ref = float(np.median(lv[i - ref_n:i]))
        if lv[i] < ref - drop_db:
            j = i
            while j < n and lv[j] < ref - drop_db:
                j += 1
            dur = (j - i) * hop
            if lo <= dur <= hi and j < n - edge:
                out.append((round(i * hop, 2), round(j * hop, 2)))
            i = j + ref_n // 2        # 빠진 구간 직후는 기준이 흔들리므로 조금 건너뛴다
            continue
        i += 1
    return out


def analyze(path: Path, cache: dict) -> dict:
    st = path.stat()
    key = f"{path}|{st.st_size}|{int(st.st_mtime)}"
    if key in cache:
        return cache[key]
    x = decode_mono(path)
    bpm = bpm_from_name(path.name)
    br = detect_breaks(levels_db(x), bpm)
    dur = round(len(x) / SR, 3)
    usable = dur - sum(b - a for a, b in br) - XFADE * len(br)
    info = {"track": str(path), "duration": dur, "bpm": bpm, "breaks": br, "usable": round(usable, 3)}
    cache[key] = info
    return info


def _mood_hit(track: str, mood: str | None) -> bool:
    if not mood:
        return False
    name = Path(track).stem.lower()
    return any(w and w in name for w in re.split(r"[\s,/]+", mood.lower()))


def choose(chapters: list[dict], library: list[dict]) -> list[dict]:
    """챕터마다 곡 하나. 같은 곡을 두 번 쓰지 않는다. 못 고르면 track=None."""
    used, plan = set(), []
    for ch in chapters:
        need = ch["duration"]
        cands = [t for t in library if t["usable"] >= need and t["track"] not in used]
        cands.sort(key=lambda t: (not _mood_hit(t["track"], ch.get("mood")), len(t["breaks"]), t["usable"] - need))
        pick = cands[0] if cands else None
        if pick:
            used.add(pick["track"])
        plan.append({**ch, "pick": pick})
    return plan


def measure_lufs(path: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)
    return float(m[-1]) if m else None


def _graph(breaks: list, need: float) -> str:
    """브레이크를 잘라 0.25초 크로스페이드로 잇고, 챕터 길이로 자르고 페이드."""
    segs, prev = [], 0.0
    for a, b in breaks:
        segs.append((prev, a))      # 브레이크 앞 끝 0.25초와 뒤 첫 0.25초가 겹친다
        prev = b
    segs.append((prev, None))
    parts, labels = [], []
    for k, (a, b) in enumerate(segs):
        tr = f"atrim=start={a:.3f}" + (f":end={b:.3f}" if b is not None else "")
        parts.append(f"[0:a]{tr},asetpts=PTS-STARTPTS[s{k}]")
        labels.append(f"[s{k}]")
    cur = labels[0]
    for k in range(1, len(labels)):
        parts.append(f"{cur}{labels[k]}acrossfade=d={XFADE}:c1=tri:c2=tri[x{k}]")
        cur = f"[x{k}]"
    fo = max(0.0, need - FADE_OUT)
    parts.append(f"{cur}atrim=end={need:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d={FADE_IN},afade=t=out:st={fo:.3f}:d={FADE_OUT}[pre]")
    return ";".join(parts)


def render(pick: dict, need: float, out: Path) -> dict:
    tmp = out.with_suffix(".pre.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pick["track"], "-filter_complex",
                    _graph(pick["breaks"], need), "-map", "[pre]", "-ar", "48000", "-ac", "2", str(tmp)],
                   check=True)
    before = measure_lufs(tmp)
    gain = round(TARGET_LUFS - before, 2) if before is not None else 0.0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af",
                    f"volume={gain}dB,alimiter=limit=0.891:level=false", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    after = measure_lufs(out)
    return {"lufs_before": before, "gain_db": gain, "lufs_after": after,
            "lufs_ok": after is not None and abs(after - TARGET_LUFS) <= 1.0}


def load_chapters(timing: Path | None, chapters: Path | None, moods: dict) -> list[dict]:
    if chapters:
        rows = json.loads(chapters.read_text(encoding="utf-8"))
        out = [{"chapter": r["chapter"], "start": r.get("start"),
                "duration": round(float(r["end"]) - float(r["start"]), 3), "mood": r.get("mood")} for r in rows]
    else:
        doc = json.loads(timing.read_text(encoding="utf-8"))
        out = [{"chapter": c["chapter"], "start": None, "duration": float(c["duration"]), "mood": None}
               for c in doc["chapters"]]
    for r in out:
        r["mood"] = moods.get(r["chapter"], r.get("mood"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library", type=Path, required=True)
    ap.add_argument("--timing", type=Path)
    ap.add_argument("--chapters", type=Path)
    ap.add_argument("--mood", default="", help="1:cinematic,3:calm — 챕터별 분위기 낱말(파일 이름과 비교)")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="고르기·브레이크 검사만, 파일은 안 만든다")
    a = ap.parse_args()
    if not (a.timing or a.chapters):
        ap.error("--timing 또는 --chapters 가 필요하다")
    if not have_ffmpeg():
        print("ffmpeg 없음 — 사양(이 파일 머리말)만 있고 실행은 하지 않는다.")
        return 2
    moods = {}
    for part in filter(None, a.mood.split(",")):
        k, _, v = part.partition(":")
        moods[int(k)] = v
    chapters = load_chapters(a.timing, a.chapters, moods)
    a.out.mkdir(parents=True, exist_ok=True)
    cache_f = a.out / ".bgm_cache.json"
    cache = json.loads(cache_f.read_text(encoding="utf-8")) if cache_f.exists() else {}
    files = sorted(p for p in a.library.rglob("*") if p.suffix.lower() in AUDIO_EXT)
    lib = []
    for p in files:
        try:
            lib.append(analyze(p, cache))
        except subprocess.CalledProcessError:
            print(f"  ? 디코드 실패: {p.name}")
    cache_f.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    plan = choose(chapters, lib)
    rows = []
    for ch in plan:
        pick = ch.pop("pick")
        row = {**ch, "track": pick and pick["track"], "track_duration": pick and pick["duration"],
               "bpm": pick and pick["bpm"], "cuts": pick and pick["breaks"], "crossfade": XFADE,
               "fade_in": FADE_IN, "fade_out": FADE_OUT, "target_lufs": TARGET_LUFS, "layer_gain_db": LAYER_DB}
        if not pick:
            row["error"] = f"챕터 길이 {ch['duration']}초 이상인 곡 없음(브레이크 잘라 낸 뒤 기준)"
        elif not a.dry_run:
            out = a.out / f"bgm_ch{ch['chapter']}.wav"
            row.update(render(pick, ch["duration"], out), out=str(out))
        rows.append(row)
        mark = "✗" if row.get("error") else "✓"
        print(f"  {mark} 챕터 {ch['chapter']} {ch['duration']:.1f}s ← {Path(row['track']).name if row['track'] else '-'}"
              f" 자름 {len(row['cuts'] or [])} {row.get('lufs_after', '')}")
    man = a.out / "bgm_manifest.json"
    man.write_text(json.dumps({"target_lufs": TARGET_LUFS, "layer_gain_db": LAYER_DB, "chapters": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {man}")
    return 1 if any(r.get("error") for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
