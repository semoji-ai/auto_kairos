"""완성본 끝에 언어별 아웃트로(소리 포함 완성 클립)를 이어 붙임.  usage: append_outro.py <EP> <lang>
master_config "append_outro": {"<lang>": "assets/global/<lang>/build/….mp4"} 가 있을 때만(원래 아웃트로가 없는 편 — 예: KFC).
입력: render/<lang>/<EP>_<LANG>_final.mp4 (없으면 _preview.mp4) → render/<lang>/<EP>_<LANG>_outro.mp4. 자막은 아웃트로 앞에서 끝나 그대로."""
import json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
code = os.path.basename(ep); rd = os.path.join(ep, "render", lang)
cfg = json.load(open(os.path.join(ep, "master_config.json")))
clip = cfg.get("append_outro", {}).get(lang)
if not clip:
    sys.exit(0)
src = os.path.join(rd, f"{code}_{lang.upper()}_final.mp4")
if not os.path.exists(src):
    src = os.path.join(rd, f"{code}_{lang.upper()}_preview.mp4")
out = os.path.join(rd, f"{code}_{lang.upper()}_outro.mp4")
fc = ("[0:v]scale=1920:1080,fps=30000/1001,format=yuv420p,setsar=1[v0];[1:v]scale=1920:1080,fps=30000/1001,format=yuv420p,setsar=1[v1];"
      "[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", os.path.join(ROOT, clip), "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", out], check=True)
d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout)
print(out, round(d, 3))
