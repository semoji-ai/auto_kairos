"""코스트코(B209) 중국어판 포맷 적용: 상단 목차 끄기, 자막바·자막 템플릿·챕터 판·챕터 소리를 템플릿(assets/global/<lang>/format/costco_format.aep)으로.
usage: format_costco.py <EP> <lang>   (master_config "costco_format" 있을 때만, swap_assets 다음·timewarp 전에 _swapped.aep를 고쳐 저장)
master_config "costco_format": {"hide_layers": [본편 레이어 번호…(목차·기존 자막바)], "chapter_layers": [장 제목 글자 레이어 번호…(순서=1장…)],
                                "mute_layers": [본편 AE 안 장 효과음 레이어 번호…]}
장 제목은 l10n 화면 문자열("1. 山德士的童年")에서 번호 뒤 글자. 자막바는 "자막바"·"자막바그림자"로 바뀌므로 subtitle_bar_layers도 그 이름이어야 함."""
import json, os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
code = os.path.basename(ep)
cfg = json.load(open(os.path.join(ep, "master_config.json")))
F = cfg.get("costco_format")
if not F:
    sys.exit(0)
mid = int(list(cfg["parts"].values())[0]["comp_id"])
src = {(s["comp_id"], s["layer"]): s for s in json.load(open(os.path.join(ep, "master", "source.json")))["strings"]}
L10 = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))["strings"]
G = json.load(open(os.path.join(ep, cfg["graph"])))
lay = {L["i"]: L for L in G["comps"][str(mid)]["layers"]}
chapters = []
for n, i in enumerate(F["chapter_layers"], 1):
    s = src.get((mid, i)); t = L10[s["id"]]["text"] if s else lay[i]["name"]
    chapters.append({"layer": i, "num": n, "title": re.sub(r"^\s*\d+\s*[.．、]\s*", "", t), "in": lay[i]["in"], "out": lay[i]["out"]})
bd = os.path.join(ep, "build", lang); aep = os.path.join(bd, f"{code}_{lang}_swapped.aep")
job = {"aep": aep, "save_as": aep, "main_id": mid, "fmt": os.path.join(ROOT, "assets", "global", lang, "format", "costco_format.aep"),
       "sub_name": cfg["subtitle_comp_prefix"], "hide": F.get("hide_layers", []), "mute": F.get("mute_layers", []),
       "chapters": chapters, "out": os.path.join(bd, "format_costco_log.json")}
jp = os.path.join(ROOT, "scripts", "ae", "format_costco_job.json")
json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
if os.path.exists(job["out"]):
    os.remove(job["out"])
tj = os.path.join(tempfile.gettempdir(), "format_costco_check.js"); shutil.copy(os.path.join(ROOT, "scripts/ae/format_costco.jsx"), tj)
subprocess.run(["node", "--check", tj], check=True)
subprocess.run([os.path.join(ROOT, "scripts/ae/run.sh"), os.path.join(ROOT, "scripts/ae/format_costco.jsx")], check=True)
log = json.loads(open(job["out"]).read(), strict=False)
print("format_costco", {k: (v if not isinstance(v, list) or k == "errors" else len(v)) for k, v in log.items()})
if log.get("errors"):
    sys.exit("format_costco 오류")
