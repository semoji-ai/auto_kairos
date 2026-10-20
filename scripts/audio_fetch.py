"""프리미어 층 오디오 재료(효과음 wav·BGM mp3·아웃트로 BGM)를 NAS에서 episodes/<EP>/src/audio/ 로 복사.
usage: audio_fetch.py <EP>
경로: prproj의 \\\\jleavens_NAS\\jleavens\\… → /Volumes/jleavens/… (NAS 이름은 NFD라 구간마다 NFC 비교로 찾음).
경로가 없거나(중첩 시퀀스) 다른 컴퓨터 경로(C:\\…)면 NAS 음악 폴더들에서 파일명으로 찾는다."""
import json, os, shutil, sys, unicodedata

NAS = "/Volumes/jleavens"
SEARCH = ["001_shared_drive/2.edit_source/유투브용 무료음악/epidemic_sound",
          "002_intra/001_세상의모든지식/유투브용 무료음악", "002_intra/001_세상의모든지식/◆브랜드백과사전"]
nfc = lambda s: unicodedata.normalize("NFC", s)


def resolve(parts, base=NAS):
    """NFC 이름 구간 목록 → 실제(NFD 포함) 경로 또는 None."""
    cur = base
    for p in parts:
        try:
            hit = [x for x in os.listdir(cur) if nfc(x) == nfc(p)]
        except OSError:
            return None
        if not hit:
            return None
        cur = os.path.join(cur, hit[0])
    return cur


def find_by_name(name, index):
    return index.get(nfc(name))


def build_index():
    idx = {}
    for rel in SEARCH:
        root = resolve(rel.split("/"))
        if not root:
            continue
        for dp, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith((".mp3", ".wav", ".m4a")):
                    idx.setdefault(nfc(f), os.path.join(dp, f))
    return idx


if __name__ == "__main__":
    ep = sys.argv[1]
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    A = cfg["audio"]
    P = json.load(open(os.path.join(ep, "pr_timeline.json")))
    seqs = {s["uid"]: s for s in P}
    want = {}
    def collect(uid, tracks):
        for t in seqs[uid]["tracks"]:
            if t["kind"] == "audio" and (tracks is None or t["index"] in tracks):
                for it in t["items"]:
                    if it["seq_uid"]:
                        collect(it["seq_uid"], None)
                    elif it["name"]:
                        want.setdefault(it["name"], it["file"])
    collect(A["main_seq_uid"], [A["sfx_track"]] + A["bgm_tracks"])
    want.setdefault(A["outro_bgm"], None)
    out = os.path.join(ep, "src", "audio"); os.makedirs(out, exist_ok=True)
    index, copied, missing = None, 0, []
    for name, f in sorted(want.items()):
        dst = os.path.join(out, nfc(name))
        if os.path.exists(dst):
            continue
        src = None
        if f and f.startswith("\\\\"):
            src = resolve(f.split("\\")[4:])          # \\jleavens_NAS\jleavens\<…>
        if not src:
            index = index or build_index()
            src = find_by_name(name, index)
        if not src:
            missing.append(name); continue
        shutil.copy2(src, dst); copied += 1
        print("copy", name, "<-", src)
    print("copied", copied, "missing", len(missing), missing)
    sys.exit(1 if missing else 0)
