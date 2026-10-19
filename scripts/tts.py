"""구간 TTS.  usage: tts.py <EP> <lang> [--only id,…] [--model m] [--out-dir tts/<lang>] [--rewrite-loop]"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.budget import fit_status
from sg.tts import speech_bounds, synthesize, trim, load_key

ep, lang = sys.argv[1], sys.argv[2]
a = sys.argv[3:]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
model = a[a.index("--model") + 1] if "--model" in a else prof["tts_model"]
out_dir = os.path.join(ep, a[a.index("--out-dir") + 1] if "--out-dir" in a else f"tts/{lang}")
os.makedirs(out_dir, exist_ok=True)
key = load_key(os.path.expanduser("~/LocalProjects/auto_kairos/.env"))
src = {g["id"]: g for g in json.load(open(os.path.join(ep, "master/source.json")))["segments"]}
lp = os.path.join(ep, "l10n", f"{lang}.json")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def run(ids):
    L = json.load(open(lp))
    fp = os.path.join(out_dir, "fit.json")
    fit = json.load(open(fp)) if os.path.exists(fp) else {}
    for i in ids:
        text = L["segments"][i].get("tts") or L["segments"][i]["text"]
        audio, al = synthesize(text, prof["tts_voice"], model, prof["language_code"], prof["tts_settings"], key)
        raw = os.path.join(out_dir, f"{i}.raw.mp3")
        open(raw, "wb").write(audio)
        t0, t1 = speech_bounds(al) if al else (0.0, dur(raw))
        start = trim(raw, os.path.join(out_dir, f"{i}.mp3"), t0, t1)
        os.remove(raw)
        if al:
            al = {"characters": al["characters"],
                  "character_start_times_seconds": [x - start for x in al["character_start_times_seconds"]],
                  "character_end_times_seconds": [x - start for x in al["character_end_times_seconds"]]}
        json.dump(al, open(os.path.join(out_dir, f"{i}.align.json"), "w"), ensure_ascii=False)
        g = src[i]
        d = dur(os.path.join(out_dir, f"{i}.mp3"))
        fit[i] = {"orig": round(g["out"] - g["in"], 3), "new": round(d, 3),
                  "status": fit_status(g["out"] - g["in"], d, prof["fit"]["lo"], prof["fit"]["hi"])}
        print(i, fit[i], flush=True)
        json.dump(fit, open(fp, "w"), indent=1)
    json.dump({k: v["new"] for k, v in fit.items()}, open(os.path.join(out_dir, "durs.json"), "w"), indent=1)
    return fit


L0 = json.load(open(lp))
ids = a[a.index("--only") + 1].split(",") if "--only" in a else list(L0["segments"])
skip = [i for i in ids if i not in L0["segments"] or src[i].get("nonverbal")]
if skip:
    print("skip (nonverbal or untranslated):", skip)
ids = [i for i in ids if i not in skip]
fit = run(ids)
if "--rewrite-loop" in a:
    for rnd in range(prof["fit"]["max_rewrites"]):
        bad = {k: v for k, v in fit.items() if v["status"] != "ok"}
        if not bad:
            break
        rew = {}
        for k, v in bad.items():
            cur = len(json.load(open(lp))["segments"][k]["text"])
            target = int(cur * v["orig"] / v["new"])    # 원래 길이에 맞추는 글자 수
            rew[k] = {"target_chars": max(4, target), "why": "long" if v["status"] == "long" else "short"}
        rp = os.path.join(out_dir, f"rewrite_{rnd + 1}.json")
        json.dump(rew, open(rp, "w"), indent=1)
        subprocess.run([sys.executable, os.path.join(root, "scripts/translate.py"), ep, lang, "--rewrite", rp], check=True)
        fit = run(list(bad))
    bad = [k for k, v in fit.items() if v["status"] != "ok"]
    print("still out of range:", bad)
