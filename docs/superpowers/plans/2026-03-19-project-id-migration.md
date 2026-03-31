# 프로젝트 ID 마이그레이션 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** slug 기반 프로젝트 식별을 uuid(8자 hex) 기반으로 전환하고, 폴더 구조를 `{uuid}_{slug}`로 마이그레이션

**Architecture:** ProjectManager에 uuid 생성 + resolve_project() 중앙화. 각 모듈이 직접 경로 조합하던 코드를 PM 메서드 호출로 교체. 마이그레이션 스크립트로 기존 10개 프로젝트 폴더/DB 일괄 전환.

**Tech Stack:** Python (SQLite, pathlib), Bash

**Spec:** `docs/superpowers/specs/2026-03-19-project-id-migration-design.md`

---

## 병렬 실행 맵

```
Task 1: DB 스키마 + ProjectManager 핵심
   ↓
Task 2: 마이그레이션 스크립트 ← (Task 1 완료 필요)
   ↓
Task 3~7: 모듈 업데이트 (병렬 가능)
   ├─ Task 3: runner.py
   ├─ Task 4: cli.py
   ├─ Task 5: session_manager.py
   ├─ Task 6: build_manifest.py + remotion_bridge.py
   └─ Task 7: project_paths.py
   ↓
Task 8: app.py + dashboard/helpers.py
Task 9: vault_rag.py
Task 10: CLAUDE.md.template
   ↓
Task 11: 마이그레이션 실행 + 검증
```

---

### Task 1: DB 스키마 + ProjectManager 핵심 (기반)

**Files:**
- Modify: `auto_agent/db/schema.sql:9-23`
- Modify: `auto_agent/db/project_manager.py:1-65`

- [ ] **Step 1: schema.sql에 uuid 컬럼 추가**

`auto_agent/db/schema.sql`의 projects 테이블에 uuid 컬럼 추가 (id 다음, name 전):

```sql
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT NOT NULL DEFAULT '',               -- "b3cef462" (8자 hex)
    name            TEXT NOT NULL,                          -- "미국 이란 전쟁 2026"
    slug            TEXT NOT NULL UNIQUE,                   -- "미국_이란_전쟁_2026"
    ...
```

- [ ] **Step 2: project_manager.py에 uuid 생성 함수 추가**

파일 상단 imports 영역에 추가:

```python
import uuid as _uuid

def _generate_project_uuid() -> str:
    """8자 hex 프로젝트 ID 생성. 충돌 확률 ~1/4B."""
    return _uuid.uuid4().hex[:8]
```

- [ ] **Step 3: create_project()에 uuid 지원 추가**

`create_project()` 메서드 수정 (line 26-46):

```python
def create_project(
    self,
    name: str,
    slug: str,
    topic: str = None,
    theme: str = "simple",
    config: dict = None,
    uuid: str = None,
) -> int:
    """프로젝트 생성. output_dir 자동 생성. 프로젝트 ID 반환."""
    if not uuid:
        uuid = _generate_project_uuid()
    output_dir = get_workspace_dir() / "output" / f"{uuid}_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    with transaction(self.db_path) as conn:
        cur = conn.execute(
            """INSERT INTO projects (uuid, name, slug, topic, theme, config, output_dir)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (uuid, name, slug, topic, theme,
             json.dumps(config, ensure_ascii=False) if config else None,
             str(output_dir)),
        )
        return cur.lastrowid
```

- [ ] **Step 4: get_project()에 uuid 조회 추가**

`get_project()` 메서드 수정 (line 48-65):

```python
def get_project(
    self, project_id: int = None, slug: str = None, uuid: str = None
) -> Optional[dict]:
    """ID, slug, 또는 uuid로 프로젝트 조회."""
    conn = get_connection(self.db_path)
    try:
        if project_id:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        elif uuid:
            row = conn.execute(
                "SELECT * FROM projects WHERE uuid = ?", (uuid,)
            ).fetchone()
        elif slug:
            row = conn.execute(
                "SELECT * FROM projects WHERE slug = ?", (slug,)
            ).fetchone()
        else:
            return None
        return dict(row) if row else None
    finally:
        conn.close()
```

- [ ] **Step 5: resolve_project() 신규 메서드 추가**

`get_project()` 바로 아래에 추가:

```python
def resolve_project(self, identifier: str) -> Optional[dict]:
    """uuid(8자 hex) 또는 slug로 프로젝트 조회.

    8자 hex 패턴이면 uuid 우선 조회, fallback으로 slug.
    그 외는 slug로 조회.
    """
    if (len(identifier) == 8
        and all(c in '0123456789abcdef' for c in identifier.lower())):
        project = self.get_project(uuid=identifier.lower())
        if project:
            return project
    return self.get_project(slug=identifier)

def get_project_dir(self, project_id: int = None, uuid: str = None, slug: str = None) -> Optional[Path]:
    """프로젝트 output 디렉토리 경로. DB의 output_dir 반환."""
    project = self.get_project(project_id=project_id, uuid=uuid, slug=slug)
    if not project:
        return None
    return Path(project["output_dir"])

def get_manifest_filename(self, project_id: int = None, uuid: str = None, slug: str = None) -> Optional[str]:
    """매니페스트 파일명: {uuid}_{slug}.json"""
    project = self.get_project(project_id=project_id, uuid=uuid, slug=slug)
    if not project:
        return None
    return f"{project['uuid']}_{project['slug']}.json"
```

- [ ] **Step 6: 검증**

```bash
python3 -c "
from auto_agent.db.project_manager import ProjectManager, _generate_project_uuid
uuid = _generate_project_uuid()
assert len(uuid) == 8
assert all(c in '0123456789abcdef' for c in uuid)
print(f'uuid 생성 OK: {uuid}')
"
```

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/db/schema.sql auto_agent/db/project_manager.py
git commit -m "feat: ProjectManager에 uuid 생성 + resolve_project() + 경로 메서드 추가"
```

---

### Task 2: 마이그레이션 스크립트

**Files:**
- Create: `auto_agent/db/migrate_to_uuid.py`

- [ ] **Step 1: 마이그레이션 스크립트 작성**

```python
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
```

- [ ] **Step 2: dry-run 테스트**

```bash
python3 -m auto_agent.db.migrate_to_uuid --dry-run
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/db/migrate_to_uuid.py
git commit -m "feat: uuid 마이그레이션 스크립트 추가 (dry-run 지원)"
```

---

### Task 3: runner.py — 경로 중앙화

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:240`

- [ ] **Step 1: project_dir 설정 코드 수정**

Line 240 부근, `output_dir` 설정 코드를 찾아 DB 기반으로 변경:

현재:
```python
output_dir = str(get_workspace_dir() / "output" / project_slug)
```

변경: ProjectManager에서 이미 DB에 output_dir이 저장되어 있으므로, 프로젝트 조회 시 받은 output_dir을 사용하도록 수정. runner가 project dict를 이미 갖고 있다면 `self.project["output_dir"]` 활용.

runner.py에서 `project_slug`로 경로를 직접 조합하는 모든 곳을 `self.project["output_dir"]` 또는 `self.project_dir`로 교체.

- [ ] **Step 2: project_slug 변수가 경로 조합에 쓰이는 곳 모두 확인**

```bash
grep -n "output.*project_slug\|output.*self.project_slug" auto_agent/orchestrator/runner.py
```

모든 경로 조합을 DB의 output_dir 기반으로 교체.

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "refactor: runner.py 경로 조합을 DB output_dir 기반으로 변경"
```

---

### Task 4: cli.py — resolve_project 적용

**Files:**
- Modify: `auto_agent/cli.py:602-660`

- [ ] **Step 1: --project 처리 로직 수정**

현재 `--project` 플래그는 slug만 받음. `resolve_project()`를 활용하여 uuid/slug 양쪽 허용:

```python
# 기존
project_slug = _get_arg(args[1:], "--project")

# 변경
project_identifier = _get_arg(args[1:], "--project")
if project_identifier:
    pm = ProjectManager()
    project = pm.resolve_project(project_identifier)
    if not project:
        print_error(f"프로젝트를 찾을 수 없습니다: {project_identifier}")
        return
    project_slug = project["slug"]
```

이 패턴을 cli.py에서 `--project`를 사용하는 모든 곳(line 602, 629, 644, 660)에 적용.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat: CLI --project에 uuid/slug 양쪽 허용"
```

---

### Task 5: session_manager.py — uuid 기반 경로

**Files:**
- Modify: `auto_agent/session_manager.py:31-38, 90, 297-298`

- [ ] **Step 1: 세션/로그 경로를 project dict 기반으로 변경**

Line 33: 세션 파일명은 uuid_{slug} 형태로:
```python
def _session_file(project_slug: str) -> Path:
    return _sessions_dir() / f"{project_slug}.json"
```
→ 이 함수의 인자를 그대로 유지하되, 호출부에서 `f"{uuid}_{slug}"` 형태로 전달.

Line 38: 로그 디렉토리는 DB의 output_dir 사용:
```python
def _logs_dir(project_slug: str) -> Path:
    d = get_workspace_dir() / "output" / project_slug / "logs"
```
→ 이 함수를 project dict의 output_dir 기반으로 변경.

Line 297-298: pipeline_state.json도 동일하게 변경.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/session_manager.py
git commit -m "refactor: session_manager 경로를 DB output_dir 기반으로 변경"
```

---

### Task 6: build_manifest.py + remotion_bridge.py — 매니페스트 경로

**Files:**
- Modify: `auto_agent/scripts/build_manifest.py`
- Modify: `auto_agent/tools/remotion_bridge.py:451`

- [ ] **Step 1: build_manifest.py 매니페스트 출력 경로 변경**

매니페스트 파일명을 `{uuid}_{slug}.json`으로 변경. build_manifest가 project_id와 storage_key를 인자로 받는데, 이를 DB 조회로 교체하거나 uuid_{slug} 형태의 storage_key를 전달받도록 수정.

- [ ] **Step 2: remotion_bridge.py line 451 수정**

현재 `project_slug` 미정의 버그 있음. DB 조회로 매니페스트 경로를 결정하도록 수정.

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/build_manifest.py auto_agent/tools/remotion_bridge.py
git commit -m "refactor: 매니페스트 경로를 uuid_{slug} 기반으로 변경"
```

---

### Task 7: project_paths.py — resolve 활용

**Files:**
- Modify: `auto_agent/scripts/project_paths.py:71, 82, 162, 168`

- [ ] **Step 1: 경로 결정 로직에 PM resolve 활용**

Line 71, 82: `--project` 인자와 `PROJECT_NAME` 환경변수 처리 시 `pm.resolve_project()` 사용.
Line 162, 168: 매니페스트 경로에 `pm.get_manifest_filename()` 사용.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/scripts/project_paths.py
git commit -m "refactor: project_paths를 PM resolve 기반으로 변경"
```

---

### Task 8: app.py + dashboard/helpers.py — URL 경로

**Files:**
- Modify: `app.py`
- Modify: `auto_agent/dashboard/helpers.py:63, 79, 87`

- [ ] **Step 1: helpers.py URL 경로 변경**

Line 63, 79, 87: `/output/{slug}/images/...` → DB output_dir 기반으로 변경.
app.py에서 slug를 추출하는 곳도 uuid_{slug} 호환으로 수정.

helpers.py의 함수들이 slug 대신 project dict (또는 output_dir 이름)를 받도록 수정:
```python
# 현재
def get_scene_image_url(slug, scene_num, ext=".png"):
    return f"/output/{slug}/images/scene_{scene_num:03d}{ext}"

# 변경: slug 인자는 실제로는 디렉토리명 (uuid_slug)
def get_scene_image_url(project_dir_name, scene_num, ext=".png"):
    return f"/output/{project_dir_name}/images/scene_{scene_num:03d}{ext}"
```

app.py에서 호출 시 `Path(project["output_dir"]).name` 전달.

- [ ] **Step 2: 커밋**

```bash
git add app.py auto_agent/dashboard/helpers.py
git commit -m "refactor: 대시보드 URL을 uuid_{slug} 기반으로 변경"
```

---

### Task 9: vault_rag.py — 볼트 경로

**Files:**
- Modify: `auto_agent/orchestrator/vault_rag.py:187, 195, 199, 263`

- [ ] **Step 1: 볼트 프로젝트 경로에 uuid 반영**

Line 187: `07-projects/{project_slug}` → `07-projects/{uuid}_{project_slug}` 형태로 변경.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/orchestrator/vault_rag.py
git commit -m "refactor: vault_rag 경로에 uuid 반영"
```

---

### Task 10: CLAUDE.md.template 업데이트

**Files:**
- Modify: `auto_agent/data/CLAUDE.md.template`

- [ ] **Step 1: 경로 안내 업데이트**

`output/{project-slug}/` → `output/{uuid}_{slug}/` 형태로 안내 변경.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/data/CLAUDE.md.template
git commit -m "docs: CLAUDE.md.template 경로 안내를 uuid_{slug}로 업데이트"
```

---

### Task 11: 마이그레이션 실행 + 검증

- [ ] **Step 1: dry-run으로 미리보기**

```bash
python3 -m auto_agent.db.migrate_to_uuid --dry-run
```

10개 프로젝트의 변경 예정 내역 확인.

- [ ] **Step 2: 실제 마이그레이션 실행**

```bash
python3 -m auto_agent.db.migrate_to_uuid
```

- [ ] **Step 3: 검증**

```bash
# DB 확인
sqlite3 auto_agent.db "SELECT id, uuid, slug, output_dir FROM projects ORDER BY id;"

# 폴더 확인
ls output/

# 매니페스트 확인
ls remotion/public/manifests/ 2>/dev/null
```

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "chore: 기존 프로젝트 10개 uuid 마이그레이션 완료"
```
