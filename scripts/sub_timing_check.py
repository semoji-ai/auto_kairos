#!/usr/bin/env python3
"""말자막 바뀜 타이밍 검수(필수) — 렌더 영상의 실제 발화 시각(whisper 단어 시각)과 자막 큐 시작을 견준다.
    python3 scripts/sub_timing_check.py <video.mp4> <semoji_plan.json|subtitles.json> <ko|zh> [--fix out.json] [--lead 0.1]
보고: 큐마다 첫 낱말이 실제로 들리기 시작한 시각과의 차(+면 자막이 늦음). 중앙값·|차|>0.3초 개수.
발화 시각은 두 가지로 잰다 — 쉼 뒤에 시작하는 큐는 침묵 끝(silencedetect, 정확), 말 중간에서 바뀌는 큐는
whisper 단어 시각. whisper는 -dtw 없이 쓰면 단어 시각이 1~2초씩 틀린다(B148 실측 — 그걸 믿고 "0.19초 늦다"로 오판했다).
반드시 -dtw large.v3.turbo 로, 24초 토막으로 재고(120초 토막이면 dtw여도 1초씩 밀린다), 남는 편향은 둘 다 잡힌 큐로 재서 뺀다.
(whisper만 믿고 고치면 쉼 뒤 큐가 오히려 앞서 나온다. 실제로 어긋난 것은 말 중간에서 바뀌는 큐였다.)
--fix: 큐 시작을 실제 발화 시작 - lead 로 옮기고, 앞 큐 끝은 다음 큐 시작에 붙인 큐 목록을 쓴다(못 찾은 큐는 그대로)."""
import json, re, statistics, subprocess, sys, tempfile, unicodedata
from pathlib import Path

MODEL = Path.home() / "LocalProjects/realtime-transcriber/models/ggml-large-v3-turbo.bin"


def local_onset(video, lang, t0, text, win=3.0):
    """t0 앞뒤 win초만 잘라 whisper(dtw)로 재고, 큐 첫 낱말과 맞는 단어 중 t0에 가장 가까운 시작 시각.
    whisper 단어 시각은 앞뒤 문맥에 따라 1초씩 흔들린다(긴 토막일수록). 짧은 토막 세 개가 같은 값을 냈다."""
    k = norm(text)[:2]
    if not k:
        return None
    s0 = max(0.0, t0 - win)
    with tempfile.TemporaryDirectory() as d:
        w = f"{d}/a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{2 * win:.3f}", "-i", video, "-ar", "16000", "-ac", "1", w], check=True)
        r = subprocess.run(["whisper-cli", "-m", str(MODEL), "-l", lang, "-f", w, "-ml", "1"] + ([] if lang == "zh" else ["-sow"])
                           + ["-np", "-dtw", "large.v3.turbo"], capture_output=True, text=True).stdout
    toks = []
    for l in r.splitlines():
        m = re.match(r"\[(\d+):(\d+):([\d.]+) --> [^\]]+\]\s*(.+)", l)
        if m:
            toks.append((s0 + int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), norm(m[4])))
    best = None
    for i, (t, w) in enumerate(toks):
        joined = "".join(x for _, x in toks[i:i + 3])           # zh는 토큰이 한두 글자라 이어 붙여 본다
        if joined.startswith(k) and (best is None or abs(t - t0) < abs(best - t0)):
            best = t
    return best


def silence_ends(video):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", video, "-af", "highpass=f=200,silencedetect=n=-40dB:d=0.12", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]


def norm(s):
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"[\s\"'“”‘’,.!?…:;，。！？：；、()（）\[\]《》「」·-]", "", s)


def main():
    a = sys.argv
    video, cues_p, lang = a[1], a[2], a[3]
    lead = float(a[a.index("--lead") + 1]) if "--lead" in a else 0.05
    d = json.load(open(cues_p))
    cues = d["cues"]
    key0 = "t0" if "t0" in cues[0] else "start"
    SE = silence_ends(video)
    from concurrent.futures import ThreadPoolExecutor
    so, need = [], []
    for i, c in enumerate(cues):
        near = [e for e in SE if abs(e - c[key0]) < 0.25]
        so.append(c[key0] - min(near, key=lambda e: abs(e - c[key0])) if near else None)
        if so[-1] is None:
            need.append(i)
    with ThreadPoolExecutor(4) as ex:
        got_w = dict(zip(need, ex.map(lambda i: local_onset(video, lang, cues[i][key0], cues[i]["text"]), need)))
    offs = [round(x, 3) if x is not None else (round(cues[i][key0] - got_w[i], 3) if got_w.get(i) is not None else None)
            for i, x in enumerate(so)]
    print(f"쉼 뒤 큐(침묵 끝으로 잼) {len(cues) - len(need)} · 말 중간 큐(앞뒤 3초 whisper) {len(need)}")
    got = [o for o in offs if o is not None]
    med = statistics.median(got) if got else 0
    late = [(i, cues[i][key0], o, cues[i]["text"][:20]) for i, o in enumerate(offs) if o is not None and abs(o) > 0.3]
    print(f"큐 {len(cues)} · 찾음 {len(got)} · 중앙값 {med:+.2f}s (+면 자막이 늦음) · |차|>0.3초 {len(late)}")
    for x in late[:30]:
        print("  ", x)
    if "--fix" in a:
        new = []
        for c, o in zip(cues, offs):
            c = dict(c); c[key0] = round(c[key0] - (o + lead if o is not None and abs(o) > 0.25 else 0), 3); new.append(c)   # 측정 잡음(±0.2)은 따라가지 않는다
        k1 = "t1" if "t1" in new[0] else "end"
        for x, y in zip(new, new[1:]):
            if y[key0] < x[key0] + 0.3:
                y[key0] = round(x[key0] + 0.3, 3)
            x[k1] = y[key0]
        d["cues"] = new
        json.dump(d, open(a[a.index("--fix") + 1], "w"), ensure_ascii=False, indent=1)
        print("고친 큐 →", a[a.index("--fix") + 1])
    return 0 if abs(med) <= 0.15 and len(late) <= len(cues) * 0.05 else 1


if __name__ == "__main__":
    sys.exit(main())
