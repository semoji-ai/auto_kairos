"""raster/manual.json 의 사람 보정을 items.json 에 반영(번역·판·적용 단계가 같은 값을 보게).
"<id>#<n>": {"quad": [[x,y]×4]} — OCR이 거꾸로 읽거나 일부만 잡은 글자 영역을 손으로 지정(그림 png 좌표)."""
import copy, json, os


def apply_manual(items, manual):
    out = copy.deepcopy(items)
    for x in out:
        for n, it in enumerate(x["items"]):
            m = manual.get(f"{x['id']}#{n}", {})
            if "quad" in m:
                it["quad"] = m["quad"]
    return out


def load_items(rd):
    items = json.load(open(os.path.join(rd, "items.json")))
    mp = os.path.join(rd, "manual.json")
    return apply_manual(items, json.load(open(mp)) if os.path.exists(mp) else {})
