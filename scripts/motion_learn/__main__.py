"""모션 학습 파이프라인 CLI (Phase A).
사용: python -m scripts.motion_learn collect --urls refs/urls.txt
      python -m scripts.motion_learn analyze --slug <slug>
      python -m scripts.motion_learn merge --slug <slug> --approve name1 name2"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "refs"
LIB = ROOT / "data" / "artstyle" / "motion" / "motion_presets.json"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="motion_learn")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--urls", required=True, help="URL 목록 파일(한 줄 1개)")
    a = sub.add_parser("analyze"); a.add_argument("--slug", required=True)
    m = sub.add_parser("merge"); m.add_argument("--slug", required=True); m.add_argument("--approve", nargs="*", default=[])
    sub.add_parser("candidates").add_argument("--slug", required=True)
    v = sub.add_parser("verify"); v.add_argument("--slug", required=True); v.add_argument("--threshold", type=int, default=75)
    return p


def main(argv=None):
    from scripts.motion_learn import collect, analyze, merge_presets, verify
    args = build_parser().parse_args(argv)
    if args.cmd == "collect":
        urls = [ln.strip() for ln in Path(args.urls).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        for r in collect.collect(urls, REFS):
            print("수집:", r["slug"], r.get("title", ""), r["path"])
    elif args.cmd == "analyze":
        r = analyze.analyze(args.slug, REFS, LIB)
        print(f"분석: 컷 {r['cuts']}, 신규 프리셋 후보 {r['new_preset_count']}개 → refs/{args.slug}/new_presets.json")
    elif args.cmd == "candidates":
        cands = merge_presets.list_candidates(REFS / args.slug / "new_presets.json")
        print(json.dumps(cands, ensure_ascii=False, indent=2))
    elif args.cmd == "merge":
        cands = merge_presets.list_candidates(REFS / args.slug / "new_presets.json")
        res = merge_presets.merge(LIB, cands, args.approve)
        print("머지:", res)
        jsx_lib = ROOT / "cep" / "com.autokairos.pd" / "jsx" / "tylenol" / "motion_presets.json"
        if jsx_lib.parent.is_dir():
            shutil.copy(LIB, jsx_lib)
            print("동기화: jsx 빌더 라이브러리 갱신")
    elif args.cmd == "verify":
        r = verify.verify(args.slug, REFS, LIB, threshold=args.threshold)
        if r.get("error"):
            print("검증 실패:", r["error"])
        else:
            print(f"검증: {'통과' if r['passed'] else '재시도'} (점수 {r['score']}/{r.get('threshold', args.threshold)}, "
                  f"구조 {'OK' if not r['structural']['issues'] else r['structural']['issues']}) → refs/{args.slug}/verify/verdict.json")


if __name__ == "__main__":
    main()
