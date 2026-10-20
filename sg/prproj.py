"""프리미어 .prproj(gzip XML) 시퀀스 타임라인 파서. 시간 단위: 초."""
import gzip
import xml.etree.ElementTree as ET

TICKS = 254016000000.0


def _load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)


def parse(path):
    root = _load(path)
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

    def num(e, tag):
        x = e.find(".//" + tag) if e is not None else None
        try:
            return float(x.text) / TICKS if x is not None and x.text else None
        except ValueError:
            return None

    def source_of(clip):
        """(file, seq_uid)"""
        src = ref(clip.find(".//Source")) if clip is not None else None
        for _ in range(4):
            if src is None:
                return None, None
            seq = src.find(".//SequenceSource/Sequence")
            if seq is not None:
                return None, seq.get("ObjectURef")
            m = src.find(".//Media")
            med = ref(m) if m is not None else None
            if med is not None:
                fp = med.find("ActualMediaFilePath")
                if fp is None or not fp.text or fp.text.isdigit():
                    fp = med.find("FilePath")
                return (fp.text if fp is not None else None), None
            src = ref(src.find(".//OriginalClip")) or ref(src.find(".//Source"))
        return None, None

    def level_of(item):
        """AudioClipTrackItem → (선형 gain, [[초, 선형], ...]). 볼륨 이펙트가 없으면 (1.0, [])."""
        chain = ref(item.find(".//Components"))
        if chain is None:
            return 1.0, []
        for c in chain.iter("Component"):
            comp = ref(c)
            if comp is None:
                continue
            for p in comp.iter("Param"):
                prm = ref(p)
                if prm is None or prm.findtext("Name") != "Level":
                    continue
                g = float(prm.findtext("CurrentValue") or 1.0)
                keys = []
                for kf in (prm.findtext("Keyframes") or "").split(";"):
                    f = kf.split(",")
                    if len(f) >= 2 and f[0]:
                        keys.append([round(int(f[0]) / TICKS, 4), float(f[1] or 0.0)])
                return g, keys
        return 1.0, []

    out = []
    for seq in [e for e in root if e.tag == "Sequence"]:
        tracks = []
        for tg in seq.iter("TrackGroup"):
            grp = ref(tg.find("Second"))
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
                    f, su = source_of(clip)
                    sp = clip.find(".//PlaybackSpeed") if clip is not None else None
                    g, gk = level_of(item) if kind == "audio" else (1.0, [])
                    items.append({"start": round(num(t, "Start") or 0.0, 3), "end": round(num(t, "End") or 0.0, 3),
                                  "in": round(num(clip, "InPoint") or 0.0, 3),
                                  "out": round(num(clip, "OutPoint") or 0.0, 3),
                                  "name": sub.findtext("Name") if sub is not None else None,
                                  "file": f, "seq_uid": su,
                                  "speed": float(sp.text) if sp is not None and sp.text else 1.0,
                                  "gain": g, "gain_keys": gk, "oid": item.get("ObjectID")})
                items.sort(key=lambda x: x["start"])
                idx = len([x for x in tracks if x["kind"] == kind])
                tracks.append({"kind": kind, "index": idx, "items": items})
        out.append({"sequence": (seq.findtext("Name") or "").strip(), "uid": seq.get("ObjectUID"), "tracks": tracks})
    return out
