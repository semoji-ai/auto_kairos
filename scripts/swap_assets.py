"""언어별 공용 에셋 대체 표(assets/global/swap_<lang>.json) 적용: 이름이 같은 footage를 모두 영어판 파일로 교체.
usage: swap_assets.py <EP> <lang>   (입력 build/<lang>/<EP>_<lang>_text_raster.aep → <EP>_<lang>_swapped.aep)
NAS 이름은 NFD일 수 있어 NFC로 맞춰 비교. 교체 파일은 원본과 크기·길이가 같아야 함(다르면 실패)."""
import json, os, subprocess, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
nfc = lambda s: unicodedata.normalize("NFC", s or "")


def swap_targets(names, table):
    norm = {nfc(k): v for k, v in table.items()}
    return {n: norm[nfc(n)] for n in names if nfc(n) in norm}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", path], capture_output=True, text=True).stdout
    d = json.loads(out)
    return {"w": d["streams"][0]["width"], "h": d["streams"][0]["height"], "dur": float(d["format"]["duration"])}


if __name__ == "__main__":
    ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
    code = os.path.basename(ep)
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    table = json.load(open(os.path.join(ROOT, "assets", "global", f"swap_{lang}.json")))
    inv = json.load(open(os.path.join(ep, cfg.get("inventory", "inventory_nas.json"))))
    t = swap_targets([f["name"] for f in inv["footage"]], table)
    items = []
    for f in inv["footage"]:
        if f["name"] in t:
            path = os.path.join(ROOT, t[f["name"]])
            if not os.path.exists(path):
                sys.exit(f"대체 파일 없음: {path} (build_global_assets.py로 먼저 만들 것)")
            items.append({"id": f["id"], "name": nfc(f["name"]), "path": path, **probe(path)})
    bd = os.path.join(ep, "build", lang)
    job = {"aep": os.path.join(bd, f"{code}_{lang}_text_raster.aep"), "save_as": os.path.join(bd, f"{code}_{lang}_swapped.aep"),
           "out": os.path.join(bd, "swap_assets_log.json"), "items": items}
    json.dump(job, open(os.path.join(ROOT, "scripts", "ae", "swap_assets_job.json"), "w"), ensure_ascii=False, indent=1)
    if os.path.exists(job["out"]):
        os.remove(job["out"])
    subprocess.run([os.path.join(ROOT, "scripts", "ae", "run.sh"), os.path.join(ROOT, "scripts", "ae", "swap_assets.jsx")], check=True)
    if not os.path.exists(job["out"]):
        sys.exit("swap_assets.jsx가 기록을 남기지 않음(AE 오류 대화상자 확인)")
    log = json.load(open(job["out"]))
    print({k: (len(v) if isinstance(v, list) else v) for k, v in log.items()})
    if log.get("missing") or log.get("mismatch") or log.get("errors"):
        sys.exit(f"에셋 교체 문제: {log}")
