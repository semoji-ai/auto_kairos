"""parse_prproj.py 결과의 비디오 트랙 하나를 로컬 파일로 바꿔 ffmpeg로 이어 붙인다(검증용, 영상만).

  python3 scripts/assemble_pr.py <pr_timeline.json> <sequence uid 앞부분> <map.json> <out.mp4> [--track 0]

map.json: {"프리미어 클립 이름": "로컬 파일 경로", ...}  (없는 클립은 검은 화면)
"""
import json, subprocess, sys

tl, uid, mp, out = sys.argv[1:5]
track = int(sys.argv[sys.argv.index("--track") + 1]) if "--track" in sys.argv else 0
seq = [s for s in json.load(open(tl)) if s["uid"].startswith(uid)][0]
items = [t for t in seq["tracks"] if t["kind"] == "video"][track]["items"]
M = json.load(open(mp))

inputs, parts, t = [], [], 0.0
for it in items:
    if it["start"] > t + 0.01:  # 빈 구간 → 검은 화면
        parts.append(("black", it["start"] - t)); t = it["start"]
    dur = it["end"] - it["start"]
    src = M.get(it["name"])
    parts.append((src, dur, it["in"] or 0.0) if src else ("black", dur))
    t = it["end"]

args, filt, k = ["ffmpeg", "-v", "error", "-y"], [], 0
for p in parts:
    if p[0] == "black":
        filt.append(f"color=c=black:s=1920x1080:r=30000/1001:d={p[1]:.4f},format=yuv420p[v{k}]")
    else:
        args += ["-i", p[0]]
        idx = sum(1 for q in parts[:parts.index(p)] if q[0] != "black")
        filt.append(f"[{idx}:v]trim=start={p[2]:.4f}:duration={p[1]:.4f},setpts=PTS-STARTPTS,"
                    f"fps=30000/1001,scale=1920:1080,format=yuv420p[v{k}]")
    k += 1
filt.append("".join(f"[v{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[out]")
args += ["-filter_complex", ";".join(filt), "-map", "[out]", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", out]
subprocess.run(args, check=True)
print(out, f"{t:.2f}s", len(parts), "parts")
