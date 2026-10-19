"""프리미어 .prproj(gzip XML)에서 시퀀스 타임라인을 뽑는다 (프리미어 불필요).

  python3 -I scripts/parse_prproj.py <file.prproj> [--seq 이름부분] > timeline.json

출력: [{"sequence", "uid", "tracks": [{"kind": "video|audio", "index", "items": [
        {"start", "end", "in", "out", "name", "file", "speed"}]}]}]  (시간 단위: 초)
"""
import gzip, json, sys
import xml.etree.ElementTree as ET

TICKS = 254016000000.0


def load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)


def main():
    root = load(sys.argv[1])
    want = sys.argv[sys.argv.index("--seq") + 1] if "--seq" in sys.argv else None
    ids = {e.get("ObjectID"): e for e in root if e.get("ObjectID")}
    uids = {e.get("ObjectUID"): e for e in root if e.get("ObjectUID")}

    def ref(e):
        if e is None:
            return None
        if e.get("ObjectRef"):
            return ids.get(e.get("ObjectRef"))
        if e.get("ObjectURef"):
            return uids.get(e.get("ObjectURef"))
        return None

    def num(e, tag, default=None):
        x = e.find(".//" + tag) if e is not None else None
        try:
            return float(x.text) if x is not None and x.text else default
        except ValueError:
            return default

    def media_of(clip):
        """Clip → Source → MediaSource → Media(FilePath/ActualMediaFilePath)"""
        src = ref(clip.find(".//Source")) if clip is not None else None
        for _ in range(4):
            if src is None:
                break
            m = src.find(".//Media")
            med = ref(m) if m is not None else None
            if med is not None:
                fp = med.find("ActualMediaFilePath")
                fp = fp if fp is not None and fp.text and not fp.text.isdigit() else med.find("FilePath")
                return fp.text if fp is not None else None
            src = ref(src.find(".//OriginalClip")) or ref(src.find(".//Source"))
        return None

    out = []
    for seq in [e for e in root if e.tag == "Sequence"]:
        name = (seq.findtext("Name") or "").strip()
        if want and want not in name:
            continue
        tracks = []
        for tg in seq.iter("TrackGroup"):
            grp = ref(tg.find("Second")) or ref(tg)
            if grp is None:
                continue
            for tr in grp.iter("Track"):
                track = ref(tr)
                if track is None:
                    continue
                kind = "video" if "Video" in track.tag else "audio"
                items = []
                for ti in track.iter("TrackItem"):
                    item = ref(ti)
                    if item is None or "Transition" in item.tag:
                        continue
                    t = item.find(".//TrackItem")
                    sub = ref(item.find(".//SubClip"))
                    clip = ref(sub.find("Clip")) if sub is not None else None
                    st, en = num(t, "Start", 0.0), num(t, "End", 0.0)
                    cin, cout = num(clip, "InPoint", 0.0), num(clip, "OutPoint", 0.0)
                    items.append({"start": round(st / TICKS, 3), "end": round(en / TICKS, 3),
                                  "in": round(cin / TICKS, 3) if cin is not None else None,
                                  "out": round(cout / TICKS, 3) if cout is not None else None,
                                  "name": sub.findtext("Name") if sub is not None else None,
                                  "file": media_of(clip),
                                  "speed": num(clip, "PlaybackSpeed", 1.0)})
                items.sort(key=lambda x: x["start"])
                tracks.append({"kind": kind, "index": len([x for x in tracks if x["kind"] == kind]), "items": items})
        out.append({"sequence": name, "uid": seq.get("ObjectUID"), "tracks": tracks})
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
