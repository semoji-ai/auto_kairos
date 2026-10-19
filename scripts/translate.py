"""번역.  usage: translate.py <EP> <lang> [--only id,id] [--rewrite rewrite.json]
rewrite.json: {id: {"target_chars": int, "why": "long|short"}} — 해당 구간만 길이를 맞춰 다시 번역."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.budget import char_budget
from sg.translate import translate_batch, claude_runner

ep, lang = sys.argv[1], sys.argv[2]
a = sys.argv[3:]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
gloss = json.load(open(os.path.join(root, "glossary", f"{lang}.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
out_p = os.path.join(ep, "l10n", f"{lang}.json")
os.makedirs(os.path.dirname(out_p), exist_ok=True)
L = json.load(open(out_p)) if os.path.exists(out_p) else {"lang": lang, "segments": {}, "strings": {}}

segs = [g for g in src["segments"] if not g.get("nonverbal")]
only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
rew = json.load(open(a[a.index("--rewrite") + 1])) if "--rewrite" in a else None

items = []
for i, g in enumerate(segs):
    if only and g["id"] not in only:
        continue
    if rew is not None and g["id"] not in rew:
        continue
    if rew is None and not only and g["id"] in L["segments"]:
        continue
    budget = rew[g["id"]]["target_chars"] if rew else char_budget(g["out"] - g["in"], prof["cps"])
    it = {"id": g["id"], "ko": g["ko"], "budget": budget,
          "prev": segs[i - 1]["ko"] if i else "", "next": segs[i + 1]["ko"] if i + 1 < len(segs) else ""}
    if rew:
        it["previous_translation"] = L["segments"][g["id"]]["text"]
        it["note"] = f"previous translation was too {rew[g['id']]['why']} when spoken; rewrite to about {budget} characters"
    items.append(it)
for k in range(0, len(items), 25):
    res = translate_batch(items[k:k + 25], gloss, lang, "segments", claude_runner)
    for i, t in res.items():
        L["segments"].setdefault(i, {})["text"] = t
        L["segments"][i].pop("tts", None)   # 문장이 바뀌면 옛 발음용 표기는 무효
    json.dump(L, open(out_p, "w"), ensure_ascii=False, indent=1)
    print(f"segments {min(k + 25, len(items))}/{len(items)}", flush=True)

if rew is None and not only:
    sitems = [{"id": s["id"], "ko": s["ko"].replace("\r", " / "), "max_chars": max(8, int(len(s["ko"]) * 2.2))}
              for s in src["strings"] if s["id"] not in L["strings"]]
    for k in range(0, len(sitems), 40):
        res = translate_batch(sitems[k:k + 40], gloss, lang, "strings", claude_runner)
        for i, t in res.items():
            L["strings"][i] = {"text": t.replace(" / ", "\r")}
        json.dump(L, open(out_p, "w"), ensure_ascii=False, indent=1)

with open(os.path.join(ep, "l10n", f"{lang}_review.md"), "w") as f:
    f.write(f"# {lang} 번역 대조표\n\n| id | 길이(초) | 예산 | 한국어 | 번역 |\n|---|---|---|---|---|\n")
    for g in segs:
        t = L["segments"].get(g["id"], {}).get("text", "")
        f.write(f"| {g['id']} | {g['out'] - g['in']:.1f} | {char_budget(g['out'] - g['in'], prof['cps'])} | {g['ko']} | {t} |\n")
    f.write("\n## 화면 문자열\n\n| id | 한국어 | 번역 |\n|---|---|---|\n")
    for s in src["strings"]:
        f.write(f"| {s['id']} | {s['ko'].replace(chr(13), ' / ')} | {L['strings'].get(s['id'], {}).get('text', '').replace(chr(13), ' / ')} |\n")
print("done", len(L["segments"]), "segments", len(L["strings"]), "strings")
