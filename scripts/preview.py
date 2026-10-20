"""영어 미리보기 조립.  usage: preview.py <EP> <lang>"""
import json, os, subprocess, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.preview import plan_audio, part_to_wav
from sg.graph import walk
from sg.timemap import PiecewiseMap
from sg.edl import master_to_part

ep, lang = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(ep, "master_config.json")))
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
W = json.load(open(os.path.join(ep, "build", lang, "warp.json")))
warp = PiecewiseMap(W["master"])
out_dir = os.path.join(ep, "render", lang)
order = []
for c in edl["parts"]:
    if c["id"] not in order:
        order.append(c["id"])
# 아웃트로: 언어별 공용 에셋 대체 표에 있으면 그 파일(예: Semoji 영어판), 없으면 편 폴더의 원본
_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_swap = os.path.join(_root, "assets", "global", f"swap_{lang}.json")
_tbl = {unicodedata.normalize("NFC", k): v for k, v in (json.load(open(_swap)).items() if os.path.exists(_swap) else [])}
_oc = unicodedata.normalize("NFC", (edl.get("outro") or {}).get("clip", ""))
outro_file = os.path.join(_root, _tbl[_oc]) if _oc in _tbl else os.path.join(ep, "assets", "outro.mov")
vids = [os.path.join(out_dir, f"part_{p}.mp4") for p in order] + [outro_file]
outro_dur = edl["outro"]["dur"] if edl.get("outro") else None   # 프리미어에서 쓴 길이만큼만(원본 파일은 더 김)
filt = "".join(f"[{i}:v]" + (f"trim=duration={outro_dur},setpts=PTS-STARTPTS," if i == len(vids) - 1 and outro_dur else "")
               + f"scale=1920:1080,fps=30000/1001,format=yuv420p,setsar=1[v{i}];" for i in range(len(vids)))
filt += "".join(f"[v{i}]" for i in range(len(vids))) + f"concat=n={len(vids)}:v=1:a=0[v]"
video = os.path.join(out_dir, "video_only.mp4")
args = ["ffmpeg", "-v", "error", "-y"]
for v in vids:
    args += ["-i", v]
subprocess.run(args + ["-filter_complex", filt, "-map", "[v]", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", video], check=True)

# 오디오: TTS + nonverbal 원래 녹음 조각 (파트 시각 → 내레이션 wav 시각: 프리컴프 안 레이어 startTime 반영)
G = json.load(open(os.path.join(ep, cfg["graph"])))
nar = {}
for pid, P in cfg["parts"].items():
    r = [x for x in walk(G, P["comp_id"], 0, P["dur"]) if x["src"] is not None
         and G["items"].get(str(x["src"]), {}).get("name") == P["narration"]][0]
    Lw = [x for x in G["comps"][r["comp_id"]]["layers"] if x["i"] == r["layer"]][0]
    rel = os.path.relpath(unicodedata.normalize("NFC", G["items"][str(Lw["src"])]["file"]), unicodedata.normalize("NFC", cfg["nas_ep"]))
    nar[pid] = (os.path.join(ep, "src", rel), Lw, r["occ"])
plan = plan_audio(src["segments"], warp, os.path.join(ep, "tts", lang))
ins, flt = [], []
for k, p in enumerate(plan):
    if p.get("kind") == "nonverbal":
        loc = master_to_part(edl, p["src_in"])
        if loc is None:
            raise ValueError(f"nonverbal {p['id']} outside parts")
        f_w, Lw, occ = nar[loc[0]]
        wt = part_to_wav(loc[1], Lw, occ)
        if wt is None:
            raise ValueError(f"nonverbal {p['id']} not inside narration layer")
        ins += ["-ss", f"{wt:.3f}", "-t", f"{p['src_out'] - p['src_in']:.3f}", "-i", f_w]
    else:
        ins += ["-i", p["file"]]
    flt.append(f"[{k}:a]aresample=48000,adelay={int(p['t'] * 1000)}|{int(p['t'] * 1000)}[a{k}]")
mix = ";".join(flt) + ";" + "".join(f"[a{k}]" for k in range(len(plan))) + f"amix=inputs={len(plan)}:normalize=0[a]"
audio = os.path.join(out_dir, "narration.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", mix, "-map", "[a]", "-ac", "2", audio], check=True)
final = os.path.join(out_dir, f"{os.path.basename(os.path.abspath(ep))}_{lang.upper()}_preview.mp4")
vdur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                      capture_output=True, text=True).stdout.strip()
# 프리미어 층까지 섞은 믹스(audio_mix.py)가 있으면 그것을 최종 오디오로
mix = os.path.join(out_dir, "mix.wav")
if os.path.exists(mix) and "--narration-only" not in sys.argv:
    from sg.preview import mix_is_fresh
    deps = [os.path.join(out_dir, f"part_{p}.mp4") for p in order] + [os.path.join(ep, "build", lang, "warp.json")]
    if not mix_is_fresh(mix, deps):
        sys.exit("mix.wav가 파트 렌더·워프보다 오래됨 — audio_mix.py를 다시 돌리거나 --narration-only로")
    audio = mix
# 아웃트로 구간엔 내레이션이 없으므로 -shortest 대신 오디오를 무음으로 채워 영상 길이에 맞춘다
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-af", "apad", "-t", vdur, "-c:a", "aac", "-b:a", "192k", final], check=True)
print(final)
