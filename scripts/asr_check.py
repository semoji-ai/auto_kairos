"""TTS 전사 대조(영어=단어, 중국어=간체 글자 단위).  usage: asr_check.py <EP> <lang>  → tts/<lang>/asr.json, 유사도 0.85 미만 목록"""
import difflib, json, os, re, subprocess, sys, tempfile
ep, lang = sys.argv[1], sys.argv[2]
M = os.path.expanduser("~/LocalProjects/auto_kairos/artifacts/benchmarks/lg_ep01_tts_audit_20260916/ggml-small.bin")
L = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
d = os.path.join(ep, "tts", lang)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.asrnorm import tokens
_prof = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", f"{lang}.json")))
_cjk = _prof["subs"].get("cjk", False)
norm = lambda s: tokens(s, cjk=_cjk)
res, bad = {}, []
for i, v in sorted(L["segments"].items()):
    mp3 = os.path.join(d, f"{i}.mp3")
    if not os.path.exists(mp3):
        continue
    with tempfile.NamedTemporaryFile(suffix=".wav") as w:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "16000", w.name], check=True)
        heard = subprocess.run(["whisper-cli", "-m", M, "-l", lang, "-nt", "-f", w.name], capture_output=True, text=True).stdout.strip()
    sim = difflib.SequenceMatcher(None, norm(v.get("tts") or v["text"]), norm(heard)).ratio()
    res[i] = {"sim": round(sim, 3), "heard": heard}
    if sim < 0.85:
        bad.append(i)
json.dump(res, open(os.path.join(d, "asr.json"), "w"), ensure_ascii=False, indent=1)
print("checked", len(res), "low", len(bad), bad)
