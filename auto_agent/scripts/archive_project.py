"""완성한 편을 보관 워크스페이스(NAS)로 옮긴다.

    python -m auto_agent.scripts.archive_project <프로젝트경로> [--dest ...] [--dry-run]

## 왜 이런 모양인가

**① DB 의 `output_dir` 은 NAS 를 가리키지 않는다.**
`docs/v5-plan.md:76` — 「오늘 DB의 `output_dir`이 NAS 경로로 박혀 대시보드가 죽는
일이 있었다」. 그래서 실물만 NAS 로 보내고 **원래 자리에는 `ARCHIVED.json` 표석**을
남긴다. 대시보드는 늘 있는 로컬 경로를 보고, NAS 가 안 붙어 있어도 죽지 않는다.

**② 복사 → 검증 → 삭제 순서다.**
NAS 는 느리다(실측 쓰기 11MB/s, 작은 파일 4.3개/초). 7GB 한 편이 10분을 넘으므로
중간에 끊길 수 있다. 검증이 통과하기 전에는 원본을 건드리지 않는다 — 끊기면
그냥 다시 돌리면 된다.

**③ 덮어쓰지 않는다.** 대상 자리에 같은 이름이 이미 있으면 멈춘다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

STUB_NAME = "ARCHIVED.json"

# 기본 보관 자리. 다른 곳으로 보내려면 --dest 또는 KAIROS_ARCHIVE_DIR.
DEFAULT_DEST = Path("/Volumes/jleavens/007_AI프로젝트/auto_kairos_workspace")


class ArchiveError(RuntimeError):
    pass


# ── 표석 ─────────────────────────────────────────────────────────────────

def is_archived(proj_dir: Path) -> bool:
    return (Path(proj_dir) / STUB_NAME).is_file()


def read_stub(proj_dir: Path) -> dict:
    return json.loads((Path(proj_dir) / STUB_NAME).read_text(encoding="utf-8"))


# ── 내부 ─────────────────────────────────────────────────────────────────

def _walk(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(src: Path, dst: Path) -> bool:
    """옮긴 것이 원본과 같은가.

    **크기만 보지 않는다.** 느린 링크에서 끊긴 복사가 크기만 맞는 경우가 있다.
    파일 목록·크기를 먼저 보고, 통과하면 해시까지 본다.
    """
    s_files = _walk(src)
    rels = [p.relative_to(src) for p in s_files]
    for rel in rels:
        d = dst / rel
        if not d.is_file():
            print(f"    [검증] 빠짐: {rel}", flush=True)
            return False
        if d.stat().st_size != (src / rel).stat().st_size:
            print(f"    [검증] 크기 다름: {rel}", flush=True)
            return False
    for i, rel in enumerate(rels, 1):
        if _sha(src / rel) != _sha(dst / rel):
            print(f"    [검증] 내용 다름: {rel}", flush=True)
            return False
        if i % 200 == 0:
            print(f"    [검증] {i}/{len(rels)}", flush=True)
    return True


# ── 본체 ─────────────────────────────────────────────────────────────────

def archive_project(proj_dir: Path, dest_root: Path, dry_run: bool = False) -> dict:
    proj_dir = Path(proj_dir).resolve()
    dest_root = Path(dest_root)

    if not proj_dir.is_dir():
        raise ArchiveError(f"프로젝트 폴더가 없습니다: {proj_dir}")
    if is_archived(proj_dir):
        raise ArchiveError(f"이미 보관된 프로젝트입니다: {proj_dir}")
    if not dest_root.is_dir():
        raise ArchiveError(f"보관 자리가 없습니다(마운트 확인): {dest_root}")

    dest = dest_root / proj_dir.name
    if dest.exists():
        raise ArchiveError(f"보관 자리에 같은 이름이 이미 있습니다: {dest}")

    files = _walk(proj_dir)
    total = sum(p.stat().st_size for p in files)
    info = {"name": proj_dir.name, "files": len(files), "bytes": total,
            "archived_to": str(dest)}

    if dry_run:
        print(f"  [dry-run] {proj_dir.name}: {len(files):,}개 / {total/2**30:.2f} GiB → {dest}")
        return info

    print(f"  복사 {len(files):,}개 / {total/2**30:.2f} GiB → {dest}", flush=True)
    shutil.copytree(proj_dir, dest)

    print("  검증 중…", flush=True)
    if not _verify(proj_dir, dest):
        raise ArchiveError(
            f"검증 실패 — **원본은 그대로 둡니다**. 옮긴 것을 지우고 다시 시도하세요: {dest}"
        )

    # 검증을 통과한 뒤에야 원본을 비운다. 표석은 남긴다.
    for child in proj_dir.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()

    stub = dict(info, archived_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (proj_dir / STUB_NAME).write_text(
        json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ 완료. 원래 자리에는 {STUB_NAME} 만 남았습니다.", flush=True)
    return info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="완성한 편을 보관 워크스페이스로 옮긴다")
    ap.add_argument("project", help="프로젝트 폴더 (output/<uuid>_<slug>)")
    ap.add_argument("--dest", default=os.environ.get("KAIROS_ARCHIVE_DIR", str(DEFAULT_DEST)),
                    help="보관 자리 (기본: NAS auto_kairos_workspace)")
    ap.add_argument("--dry-run", action="store_true", help="옮기지 않고 규모만 본다")
    a = ap.parse_args(argv)
    try:
        archive_project(Path(a.project), Path(a.dest), dry_run=a.dry_run)
    except ArchiveError as e:
        print(f"  ✗ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
