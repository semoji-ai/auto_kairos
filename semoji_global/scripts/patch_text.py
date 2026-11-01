"""화면 문자열 교체 job 생성.  usage: patch_text.py <EP> <lang>"""
import json, os, sys
ep, lang = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
L = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
abs_ep = os.path.abspath(ep); name = os.path.basename(abs_ep)
items = [{"comp_id": s["comp_id"], "layer": s["layer"], "ko": s["ko"], "text": L["strings"][s["id"]]["text"], "id": s["id"], "font": L["strings"][s["id"]].get("font")}
         for s in src["strings"] if s["id"] in L["strings"]]
os.makedirs(os.path.join(abs_ep, "build", lang), exist_ok=True)
json.dump({"aep": os.path.join(abs_ep, "src", f"{name}_main_ko.aep"),
           "save_as": os.path.join(abs_ep, "build", lang, f"{name}_{lang}_text.aep"),
           "out": os.path.join(abs_ep, "build", lang, "patch_text_log.json"),
           "items": items, "fx": L.get("_fx", []), "expr": L.get("_expr", []), "font_map": prof["fonts"], "min_scale": prof["min_font_scale"]},
          open(os.path.join(root, "scripts/ae/patch_text_job.json"), "w"), ensure_ascii=False, indent=1)
print("items", len(items), "fx", len(L.get("_fx", [])))
