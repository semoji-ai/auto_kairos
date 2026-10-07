"""script.json(순서: 세그먼트·카드) + TTS 정렬 → video/src/timeline.json
세그먼트마다 전역 시작 시각, 글자별 시작 시각, 자막 청크를 만든다."""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
VO = ROOT / "video/public/audio/vo"
items = json.loads(Path(sys.argv[1]).read_text())
MAXC = 25

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))

def chunks(text):
    # 문장부호 뒤에서 끊고, 길면 가운데 가까운 공백에서 한 번 더 끊는다
    parts, cur = [], ""
    for i, ch in enumerate(text):
        cur += ch
        if ch in ".?!," and (i + 1 == len(text) or text[i + 1] == " "):
            parts.append(cur); cur = ""
    if cur.strip():
        parts.append(cur)
    # 너무 짧은 조각은 앞뒤와 합친다
    merged = []
    for p in parts:
        if merged and (len(p.strip()) < 7 or len(merged[-1].strip()) < 7) and len(merged[-1]) + len(p) <= MAXC + 2:
            merged[-1] += p
        else:
            merged.append(p)
    out = []
    for p in merged:
        while len(p.strip()) > MAXC:
            mid = len(p) // 2
            sp = [m.start() for m in re.finditer(" ", p)]
            k = min(sp, key=lambda s: abs(s - mid)) if sp else mid
            out.append(p[:k + 1]); p = p[k + 1:]
        out.append(p)
    return out

t = 0.0
segs, subs, blocks = {}, [], []
for it in items:
    if it["type"] == "block":             # 카드·스팅처럼 나레이션 없는 구간
        blocks.append({"id": it["id"], "t0": round(t, 3), "t1": round(t + it["dur"], 3)})
        t += it["dur"]; continue
    t += it.get("pre", 0.25)
    al = json.loads((VO / f"{it['id']}.json").read_text())
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    text = "".join(chars)
    d = dur(VO / f"{it['id']}.mp3")
    segs[it["id"]] = {"t0": round(t, 3), "dur": round(d, 3), "text": text, "cs": [round(x, 3) for x in st]}
    pos = 0
    for c in chunks(text):
        a, b = pos, pos + len(c); pos = b
        body = c.strip().rstrip(",")
        if not body:
            continue
        # 앞뒤 공백 글자를 건너뛴 실제 발화 구간
        ia = a + (len(c) - len(c.lstrip()))
        ib = max(ia, b - 1 - (len(c) - len(c.rstrip())))
        subs.append({"t0": round(t + st[ia], 3), "t1": round(t + en[ib] + 0.12, 3), "text": body.strip("'")
                     if False else body})
    t += d + it.get("post", 0.0)
# 자막 사이 잔틈 메우기(0.35s 이하 간격은 이어 붙임) + 겹침 제거(끝 여유 0.12s가 다음 자막을 침범하면 자름)
# — Remotion은 겹쳐도 하나만 그려 티가 안 나지만 AE는 두 레이어가 동시에 보인다
for a, b in zip(subs, subs[1:]):
    if 0 < b["t0"] - a["t1"] < 0.35 or a["t1"] > b["t0"]:
        a["t1"] = b["t0"]
total = round(t + 1.8, 3)
(ROOT / "video/src/timeline.json").write_text(json.dumps({"total": total, "segs": segs, "subs": subs, "blocks": blocks}, ensure_ascii=False, indent=1))
print("total", total)
for s in subs:
    print(f"{s['t0']:6.2f}-{s['t1']:6.2f} {s['text']}")
