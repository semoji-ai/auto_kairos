"""
Vault Sync Module — output/research → 볼트 02-research merge

파이프라인 step_2_vault_sync에서 실행:
- output/<uuid>/research/wiki/     → vault/02-research/wiki/     (파일 단위 덮어쓰기)
- output/<uuid>/research/manifests/→ vault/02-research/manifests/(파일 단위 덮어쓰기)
- raw/는 sync 제외 (크기)
볼트 마운트 실패 시 경고만, 파이프라인 중단 없음.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def sync_research_to_vault(output_research_root: Path, vault_research_root: Path) -> dict:
    """output/research → 볼트 wiki/manifests merge. raw 제외."""
    results: dict[str, list[str]] = {"copied": [], "failed": [], "skipped": []}

    for subdir in ("wiki", "manifests"):
        src_base = output_research_root / subdir
        dst_base = vault_research_root / subdir

        if not src_base.exists():
            results["skipped"].append(subdir)
            continue

        for slug_dir in src_base.iterdir():
            if not slug_dir.is_dir():
                continue
            dst_slug_dir = dst_base / slug_dir.name
            try:
                dst_slug_dir.mkdir(parents=True, exist_ok=True)
                for src_file in slug_dir.rglob("*"):
                    if not src_file.is_file():
                        continue
                    rel = src_file.relative_to(slug_dir)
                    dst_file = dst_slug_dir / rel
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                results["copied"].append(str(slug_dir.name))
                print(f"[vault_sync] {subdir}/{slug_dir.name} → 볼트 완료", flush=True)
            except Exception as e:
                results["failed"].append(str(slug_dir.name))
                print(f"[vault_sync] 실패 (무시): {slug_dir.name} — {e}", flush=True)

    return results


def main() -> None:
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    status_path = project_dir / "source_ingest_status.json"

    if not status_path.exists():
        print("[vault_sync] source_ingest_status.json 없음 — 스킵", flush=True)
        sys.exit(0)

    status = json.loads(status_path.read_text(encoding="utf-8"))
    research_root_str = status.get("research_root", "")
    if not research_root_str:
        print("[vault_sync] source_ingest_status.json에 research_root 없음 — 스킵", flush=True)
        sys.exit(0)

    output_research_root = Path(research_root_str)

    vault_dir = os.environ.get("KAIROS_VAULT_DIR", "")
    if not vault_dir:
        print("[vault_sync] KAIROS_VAULT_DIR 없음 — 볼트 sync 스킵", flush=True)
        sys.exit(0)

    vault_research_root = Path(vault_dir) / "02-research"
    print(f"[vault_sync] {output_research_root} → {vault_research_root}", flush=True)
    results = sync_research_to_vault(output_research_root, vault_research_root)
    print(f"[vault_sync] 완료: copied={results['copied']}, failed={results['failed']}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
