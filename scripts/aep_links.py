"""aep 파일을 AE 없이 읽어 footage 링크 상태를 진단한다 (읽기 전용).

사용:
  python3 -I scripts/aep_links.py index  <root> <index.json>          # NAS 파일 인덱스
  python3 -I scripts/aep_links.py scan   <root> <index.json> <out.jsonl> [aep 상대경로 필터 부분문자열]

AE의 링크 해석 규칙을 흉내낸다:
  1) alas JSON의 fullpath(절대경로)가 존재하면 OK_ABS
  2) 프로젝트 위치 기준 상대경로(ascendcount_base/target)가 존재하면 OK_REL
  3) 아니면 파일명으로 후보를 찾는다: 같은 에피소드 폴더 → 전체 트리
경로 비교는 모두 NFC 상대경로(root 기준) 문자열로 한다 (NAS 파일명은 NFD 혼재).
"""
import json, os, struct, sys, unicodedata

NFC = lambda s: unicodedata.normalize("NFC", s)


def build_index(root):
    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ("#recycle", "@eaDir")]
        rel = os.path.relpath(dp, root)
        for f in fns:
            p = f if rel == "." else os.path.join(rel, f)
            files.append(NFC(p))
    return files


def alas_refs(path):
    """RIFX 트리를 seek로 훑으며 alas 청크(JSON)만 읽는다."""
    refs = []
    with open(path, "rb") as fh:
        head = fh.read(12)
        if head[:4] != b"RIFX":
            return None
        end = 8 + struct.unpack(">I", head[4:8])[0]

        def walk(pos, stop):
            while pos + 8 <= stop:
                fh.seek(pos)
                h = fh.read(8)
                if len(h) < 8:
                    return
                cid, size = h[:4], struct.unpack(">I", h[4:8])[0]
                body = pos + 8
                if cid == b"LIST":
                    walk(body + 4, body + size)
                elif cid == b"alas":
                    raw = fh.read(size).rstrip(b"\0")
                    try:
                        refs.append(json.loads(raw.decode("utf-8")))
                    except Exception:
                        refs.append({"_raw": raw[:300].decode("utf-8", "replace")})
                pos = body + size + (size & 1)

        walk(12, end)
    return refs


def split_any(p):
    return [x for x in p.replace("\\", "/").split("/") if x]


def main_scan(root, index_path, out_path, filt=None):
    files = json.load(open(index_path))
    fileset = set(files)
    dirset = set()
    by_name = {}
    for f in files:
        by_name.setdefault(os.path.basename(f).lower(), []).append(f)
        d = os.path.dirname(f)
        while d and d not in dirset:
            dirset.add(d)
            d = os.path.dirname(d)
    exists = lambda rel: rel in fileset or rel in dirset
    rootname = NFC(os.path.basename(root.rstrip("/")))

    aeps = [f for f in files if f.lower().endswith(".aep")
            and "auto-save" not in f.lower() and (not filt or filt in f)]
    out = open(out_path, "w")
    for n, aep in enumerate(aeps, 1):
        parts = aep.split("/")
        episode = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        try:
            refs = alas_refs(os.path.join(root, unicodedata.normalize("NFD", aep)))
            if refs is None:
                refs = alas_refs(os.path.join(root, aep))
        except Exception as e:
            out.write(json.dumps({"aep": aep, "error": repr(e)}, ensure_ascii=False) + "\n")
            continue
        res = []
        for r in refs or []:
            fp = NFC(r.get("fullpath", ""))
            if not fp:
                continue
            comps = split_any(fp)
            st, hit = "MISSING", None
            # 1) 절대경로: root 이름이 경로 안에 있으면 그 뒤를 root 기준 상대경로로 본다
            if rootname in comps:
                rel = "/".join(comps[comps.index(rootname) + 1:])
                if exists(rel):
                    st, hit = "OK_ABS", rel
            # 2) 상대경로
            if st == "MISSING":
                b, t = r.get("ascendcount_base", 0), r.get("ascendcount_target", 0)
                if b and t:
                    up = parts[:-1][: len(parts) - b] if b > 1 else parts[:-1]
                    rel = "/".join(up + comps[-t:])
                    if exists(rel):
                        st, hit = "OK_REL", rel
            # 3) 파일명 검색
            cands = []
            if st == "MISSING" and comps:
                cands = by_name.get(comps[-1].lower(), [])
                local = [c for c in cands if c.startswith(episode + "/")]
                if len(local) >= 1:
                    st, hit = "FIX_EPISODE", local[0]
                elif cands:
                    st, hit = "FIX_GLOBAL", cands[0]
            res.append({"fullpath": fp, "status": st, "hit": hit, "ncand": len(cands),
                        "folder": r.get("target_is_folder", False)})
        out.write(json.dumps({"aep": aep, "refs": res}, ensure_ascii=False) + "\n")
        if n % 50 == 0:
            print(f"{n}/{len(aeps)}", flush=True)
    out.close()


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "index":
        json.dump(build_index(sys.argv[2]), open(sys.argv[3], "w"), ensure_ascii=False)
    elif cmd == "scan":
        main_scan(*sys.argv[2:6]) if len(sys.argv) > 5 else main_scan(*sys.argv[2:5])
