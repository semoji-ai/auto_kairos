"""기존 프로젝트를 uuid_{slug} 구조로 마이그레이션.

Usage:
    python3 -m auto_agent.db.migrate_to_uuid --dry-run   # 미리보기
    python3 -m auto_agent.db.migrate_to_uuid              # 실행
"""
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

from auto_agent.db.connection import get_db_path, get_connection, transaction
from auto_agent.db.project_manager import _generate_project_uuid
from auto_agent.paths import get_workspace_dir


def migrate(dry_run: bool = False):
    db_path = get_db_path()
    workspace = get_workspace_dir()

    if not db_path.exists():
        print("[ERROR] DB 파일 없음:", db_path)
        return

    # 1. DB 백업
    if not dry_run:
        backup_path = db_path.with_suffix(f".db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(db_path, backup_path)
        print(f"[BACKUP] {backup_path}")

    # 2. uuid 컬럼 확인/추가
    conn = get_connection(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()]
    if "uuid" not in columns:
        if dry_run:
            print("[DRY-RUN] ALTER TABLE projects ADD COLUMN uuid TEXT DEFAULT ''")
        else:
            conn.execute("ALTER TABLE projects ADD COLUMN uuid TEXT DEFAULT ''")
            conn.commit()
            print("[DB] uuid 컬럼 추가")
    conn.close()

    # 3. 프로젝트별 마이그레이션
    conn = get_connection(db_path)
    projects = [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY id").fetchall()]
    conn.close()

    rollback_log = []

    for p in projects:
        pid = p["id"]
        slug = p["slug"]
        old_uuid = p.get("uuid", "")
        uuid = old_uuid if old_uuid else _generate_project_uuid()

        old_dir = workspace / "output" / slug
        new_dir = workspace / "output" / f"{uuid}_{slug}"

        old_manifest = workspace / "remotion" / "public" / "manifests" / f"{slug}.json"
        new_manifest = workspace / "remotion" / "public" / "manifests" / f"{uuid}_{slug}.json"

        print(f"\n[{pid}] {slug} → {uuid}_{slug}")

        # 폴더 rename
        if old_dir.exists() and not new_dir.exists():
            if dry_run:
                print(f"  [DRY-RUN] mv {old_dir.name} → {new_dir.name}")
            else:
                old_dir.rename(new_dir)
                print(f"  [RENAME] {old_dir.name} → {new_dir.name}")
            rollback_log.append({"type": "dir", "old": str(old_dir), "new": str(new_dir)})
        elif new_dir.exists():
            print(f"  [SKIP] 이미 마이그레이션됨: {new_dir.name}")
        elif not old_dir.exists():
            print(f"  [SKIP] 폴더 없음: {old_dir.name}")

        # 매니페스트 rename
        if old_manifest.exists() and not new_manifest.exists():
            if dry_run:
                print(f"  [DRY-RUN] mv {old_manifest.name} → {new_manifest.name}")
            else:
                old_manifest.rename(new_manifest)
                print(f"  [RENAME] {old_manifest.name} → {new_manifest.name}")
            rollback_log.append({"type": "manifest", "old": str(old_manifest), "new": str(new_manifest)})

        # DB 업데이트
        if not dry_run:
            with transaction(db_path) as conn:
                conn.execute(
                    "UPDATE projects SET uuid = ?, output_dir = ? WHERE id = ?",
                    (uuid, str(new_dir), pid),
                )
            print(f"  [DB] uuid={uuid}, output_dir={new_dir}")
        else:
            print(f"  [DRY-RUN] UPDATE uuid={uuid}, output_dir={new_dir}")

    # 4. rollback 정보 저장
    if not dry_run and rollback_log:
        rollback_path = workspace / "output" / "_migration_rollback.json"
        rollback_path.write_text(json.dumps(rollback_log, indent=2, ensure_ascii=False))
        print(f"\n[ROLLBACK] 복원 정보: {rollback_path}")

    # 5. 검증
    print("\n=== 검증 ===")
    conn = get_connection(db_path)
    for row in conn.execute("SELECT id, uuid, slug, output_dir FROM projects ORDER BY id"):
        p = dict(row)
        exists = Path(p["output_dir"]).exists()
        status = "✓" if exists else "✗ 폴더 없음"
        print(f"  [{p['id']}] {p['uuid']}_{p['slug']} — {status}")
    conn.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("=== DRY RUN MODE ===\n")
    migrate(dry_run=dry)
