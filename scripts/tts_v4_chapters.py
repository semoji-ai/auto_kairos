#!/usr/bin/env python3
"""챕터마다 나레이션을 ElevenLabs v4 로 한 번에 생성하고, 글자 타임스탬프로 씬 경계를 잘라 낸다.

씬마다 따로 생성하면 문장 사이 호흡이 끊긴다. 챕터를 한 덩어리로 읽히고 씬 경계는
편집용으로만 쓴다(마이디어편 방식). 설정은 2026-09-30 v4 비교 실험과 같다 —
`eleven_v4`, stability 0.5, similarity 0.9, language_code ko, 정규화 auto, 전처리 없음.

    <out>/ch{N}.mp3          챕터 나레이션
    <out>/ch{N}.json         요청·응답 원본(alignment 포함)
    <out>/timing.json        {"chapters": [{chapter, audio, duration,
                               scenes: [{n, start, end, speech_end, words: [{w, start, end}]}]}]}

`words` 는 씬 안 어절(띄어쓰기 단위)마다 챕터 음성 기준 시작·끝 초다 — 연출 키를
단어 시점에 맞출 때 쓴다(`auto_agent/tools/word_timing.find_cue`).
이미 만든 챕터의 timing.json 은 `--rebuild-timing` 으로 ch{N}.json 에서 다시 만든다
(API 호출 없음 — 과금 없음).

제작 메모는 넣지 않는다 — v4 는 어떤 메모는 읽어 버린다(실험: `(타이틀)` 발화).
원고의 각주 표시 `[1]` 같은 것은 발화문에서 걷어낸다.

    python3 scripts/tts_v4_chapters.py <project_dir> -o <out_dir> [--only 0,3]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.tools import tts_config  # noqa: E402  모델별 설정의 단일 출처
from auto_agent.tools.word_timing import scene_spans, words_from_alignment  # noqa: E402

VOICE_ID = tts_config.STYLE_VOICES["semoji"]     # 세모지
MODEL = tts_config.V4
SETTINGS = tts_config.voice_settings_for(MODEL)  # stability 0.5 · similarity 0.9


def api_key(root: Path) -> str:
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k:
        return k
    for line in (root / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("ELEVENLABS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"\'')
    raise SystemExit("ELEVENLABS_API_KEY 없음")


def spoken(text: str) -> str:
    """발화문 — 각주 표시만 걷어낸다. 원고 문장은 그대로 둔다."""
    return tts_config.strip_footnotes(text)


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def chapter_timing(ch: int, scenes: list, text: str, al: dict, audio: Path, dur: float) -> dict:
    """챕터 텍스트·alignment 로 씬 경계와 씬별 어절 시각을 만든다."""
    texts = [spoken(s["narration"]) for s in scenes]
    built, spans = scene_spans(texts)
    if built != text:
        # 원고가 생성 뒤에 바뀌었으면 씬 문장을 저장된 텍스트에서 차례로 찾는다
        spans, pos = [], 0
        for t in texts:
            a = text.find(t, pos)
            if a < 0:
                raise ValueError(f"챕터 {ch}: 씬 문장을 저장된 텍스트에서 못 찾음 — {t[:30]}")
            spans.append((a, a + len(t)))
            pos = a + len(t)
    chars = al.get("characters") or list(text)
    starts = al.get("character_start_times_seconds") or []
    ends = al.get("character_end_times_seconds") or []
    if len(starts) != len(text):
        print(f"  ! 챕터 {ch}: 타임스탬프 글자 수 {len(starts)} ≠ 원문 {len(text)} — 경계 확인 필요", flush=True)
    sc = []
    for i, (s, (a, b)) in enumerate(zip(scenes, spans)):
        st = starts[a] if a < len(starts) else 0.0
        if i == 0:
            st = 0.0
        en = starts[spans[i + 1][0]] if i + 1 < len(spans) and spans[i + 1][0] < len(starts) else dur
        words = [{"w": w["w"], "start": w["start"], "end": w["end"]}
                 for w in words_from_alignment(chars, starts, ends, a, b)]
        sc.append({"n": s["sceneNumber"], "start": round(st, 3), "end": round(en, 3),
                   "speech_end": round(ends[b - 1], 3) if 0 < b <= len(ends) else None,
                   "words": words})
    return {"chapter": ch, "audio": str(audio), "duration": round(dur, 3), "chars": len(text), "scenes": sc}


def run_chapter(ch: int, scenes: list, out: Path, key: str) -> dict:
    text, _ = scene_spans([spoken(s["narration"]) for s in scenes])
    body = tts_config.request_body(text, MODEL)   # + language_code ko · 정규화 auto
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
    for attempt in range(3):
        r = requests.post(url, params={"output_format": "mp3_44100_128"},
                          headers={"xi-api-key": key, "Content-Type": "application/json"},
                          json=body, timeout=600)
        if r.ok:
            break
        time.sleep(5 * (attempt + 1))
    if not r.ok:
        return {"chapter": ch, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    data = r.json()
    mp3 = out / f"ch{ch}.mp3"
    mp3.write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or {}
    dur = duration(mp3)
    (out / f"ch{ch}.json").write_text(json.dumps({"chapter": ch, "text": text, "request": {k: v for k, v in body.items() if k != "text"},
                                                  "request_id": r.headers.get("request-id"), "alignment": al,
                                                  "normalized_alignment": data.get("normalized_alignment")},
                                                 ensure_ascii=False), encoding="utf-8")
    return chapter_timing(ch, scenes, text, al, mp3, dur)


def rebuild_chapter(ch: int, scenes: list, out: Path, old: dict | None) -> dict:
    """저장된 ch{N}.json·mp3 로 timing 을 다시 만든다 — API 를 부르지 않는다."""
    raw = json.loads((out / f"ch{ch}.json").read_text(encoding="utf-8"))
    mp3 = out / f"ch{ch}.mp3"
    dur = (old or {}).get("duration") or duration(mp3)
    return chapter_timing(ch, scenes, raw["text"], raw.get("alignment") or {}, mp3, float(dur))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--only")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--rebuild-timing", action="store_true",
                    help="생성하지 않고 기존 ch{N}.json 으로 timing.json(어절 시각 포함)만 다시 만든다")
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    key = None if a.rebuild_timing else api_key(root)
    specs = json.loads((a.project / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    chapters: dict[int, list] = {}
    for s in specs:
        chapters.setdefault(s["chapter"], []).append(s)
    want = sorted(chapters) if not a.only else [int(x) for x in a.only.split(",")]
    a.out.mkdir(parents=True, exist_ok=True)
    tf = a.out / "timing.json"
    timing = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {"model": MODEL, "voice": VOICE_ID, "chapters": []}
    keep = {c["chapter"]: c for c in timing["chapters"]}
    if a.rebuild_timing:
        want = [c for c in want if (a.out / f"ch{c}.json").exists()]
        res = [rebuild_chapter(c, chapters[c], a.out, keep.get(c)) for c in want]
    else:
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            res = list(ex.map(lambda c: run_chapter(c, chapters[c], a.out, key), want))
    for r in res:
        if r.get("error"):
            print(f"  ✗ 챕터 {r['chapter']}: {r['error']}")
            continue
        keep[r["chapter"]] = r
        print(f"  ✓ 챕터 {r['chapter']}: {r['duration']}초 · {r['chars']}자 · 씬 {len(r['scenes'])}")
    timing["chapters"] = [keep[c] for c in sorted(keep)]
    tf.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(c["duration"] for c in timing["chapters"])
    print(f"합계 {total/60:.1f}분")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
