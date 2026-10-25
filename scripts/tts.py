"""구간 TTS.  usage: tts.py <EP> <lang> [--only id,…] [--model m] [--out-dir tts/<lang>] [--rewrite-loop] [--force]
같은 텍스트로 이미 만든 구간은 건너뜀(--force로 강제 재생성)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.budget import fit_status
from sg.tts import speech_bounds, synthesize, trim, load_key, text_hash, should_synth, zh_spoken, context_text, slice_alignment, cut_bounds
from sg.audio import decode, speech_spans
import time

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
    order = [g for g in src if g in L["segments"] and not src[g].get("nonverbal")]   # 앞뒤 문맥(context_text)용 순서
    for i in ids:
        text = L["segments"][i].get("tts") or L["segments"][i]["text"]
        if lang == "zh":
            text = zh_spoken(text)   # 숫자 연도·월일을 한자 읽기로(v4가 아라비아 숫자 연도를 잘못 읽음)
        k = order.index(i) if i in order else -1
        say = lambda j: (lambda t: zh_spoken(t) if lang == "zh" else t)(L["segments"][j].get("tts") or L["segments"][j]["text"])
        prev = say(order[k - 1]) if k > 0 else ""
        nxt = say(order[k + 1]) if 0 <= k < len(order) - 1 else ""
        if not should_synth(fit, i, text, os.path.join(out_dir, f"{i}.mp3"), force=FORCE):
            continue
        comp, ca, cb = context_text(prev, text, nxt) if lang == "zh" else (text, 0, len(text))
        for attempt in range(4):
            try:
                audio, al = synthesize(comp, prof["tts_voice"], model, prof["language_code"], prof["tts_settings"], key)
                break
            except Exception as e:   # 429/5xx 등 → 잠시 후 재시도
                if attempt == 3:
                    raise
                print("retry", i, e, flush=True); time.sleep(5 * (attempt + 1))
        raw = os.path.join(out_dir, f"{i}.raw.mp3")
        open(raw, "wb").write(audio)
        if al and len(al.get("characters", [])) == len(comp):
            al = slice_alignment(al, ca, cb)          # 이웃 문맥을 빼고 본문 글자만
        elif comp != text:
            sys.exit(f"{i}: 정렬 글자 수가 합성 문장과 다름 — 본문만 잘라 낼 수 없음")
        t0, t1 = speech_bounds(al) if al else (0.0, dur(raw))
        if comp != text:                              # 이웃 문맥과 함께 읽혔으면 경계를 실제 쉼에 맞춤
            t0, t1 = cut_bounds(speech_spans(decode(raw), 16000, min_silence=0.08, pad=0.0), t0, t1, ca > 0, cb < len(comp))
        start = trim(raw, os.path.join(out_dir, f"{i}.mp3"), t0, t1)
        os.remove(raw)
        if al:
            al = {"characters": al["characters"],
                  "character_start_times_seconds": [x - start for x in al["character_start_times_seconds"]],
                  "character_end_times_seconds": [x - start for x in al["character_end_times_seconds"]]}
        json.dump(al, open(os.path.join(out_dir, f"{i}.align.json"), "w"), ensure_ascii=False)
        g = src[i]
        d = dur(os.path.join(out_dir, f"{i}.mp3"))
        fit[i] = {"orig": round(g["out"] - g["in"], 3), "new": round(d, 3), "hash": text_hash(text),
                  "status": fit_status(g["out"] - g["in"], d, prof["fit"]["lo"], prof["fit"]["hi"])}
        print(i, fit[i], flush=True)
        json.dump(fit, open(fp, "w"), indent=1)
        json.dump({k: v["new"] for k, v in fit.items()}, open(os.path.join(out_dir, "durs.json"), "w"), indent=1)
    return fit


FORCE = "--force" in a
L0 = json.load(open(lp))
ids = a[a.index("--only") + 1].split(",") if "--only" in a else list(L0["segments"])
skip = [i for i in ids if i not in L0["segments"] or src[i].get("nonverbal")]
if skip:
    print("skip (nonverbal or untranslated):", skip)
ids = [i for i in ids if i not in skip]
fit = run(ids)
if "--rewrite-loop" in a:
    for rnd in range(prof["fit"]["max_rewrites"]):
        notes = json.load(open(lp))["segments"]
        bad = {k: v for k, v in fit.items() if v["status"] != "ok" and k in ids   # 이번 실행 범위만
               and not notes[k].get("note")}                                     # 손으로 고친 문장(note)은 다시 번역하지 않음
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
    bad = [k for k, v in fit.items() if v["status"] != "ok" and k in ids]
    print("still out of range:", bad)
