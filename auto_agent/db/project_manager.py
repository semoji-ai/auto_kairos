"""
프로젝트 관리 핵심 API.
모든 scripts와 tools에서 이 모듈을 통해 프로젝트 상태를 관리한다.
"""
import json
import hashlib
import mimetypes
import uuid as _uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .connection import get_connection, get_db_path, transaction
from auto_agent.paths import get_workspace_dir, get_data_dir


def _generate_project_uuid() -> str:
    """8자 hex 프로젝트 ID 생성. 충돌 확률 ~1/4B."""
    return _uuid.uuid4().hex[:8]


def resolve_art_style_path(art_style: str, project_dir: Path = None) -> Optional[Path]:
    """아트스타일 경로를 확실하게 resolve.

    다양한 입력 형태를 모두 처리:
      - 스타일명만: "quirky_cartoon"
      - 상대경로: "artstyle/styles/quirky_cartoon.json"
      - 절대경로: "/Users/.../quirky_cartoon.json"

    탐색 순서:
      1. 절대경로면 직접 확인
      2. 프로젝트 디렉토리 내 art_style.json (복제본)
      3. 프로젝트 디렉토리 내 artstyle/styles/{name}.json
      4. PACKAGE_DIR/data/artstyle/styles/{name}.json
      5. DATA_DIR/{art_style} (상대경로 그대로)
    """
    if not art_style:
        return None

    # 스타일명에서 .json 확장자 정리
    style_name = art_style.replace(".json", "").split("/")[-1]  # "quirky_cartoon"

    # 1. 절대경로
    abs_path = Path(art_style)
    if abs_path.is_absolute() and abs_path.exists():
        return abs_path

    # 2. 프로젝트 디렉토리 내 복제본
    if project_dir:
        for candidate in [
            project_dir / "art_style.json",
            project_dir / "artstyle" / "styles" / f"{style_name}.json",
            project_dir / art_style,
        ]:
            if candidate.exists():
                return candidate

    # 3. 패키지 데이터 디렉토리 (가장 확실한 소스)
    data_dir = get_data_dir()
    for candidate in [
        data_dir / "artstyle" / "styles" / f"{style_name}.json",
        data_dir / art_style,
        data_dir / f"{art_style}.json",
    ]:
        if candidate.exists():
            return candidate

    # 4. 워크스페이스 루트 fallback
    ws = get_workspace_dir()
    for candidate in [
        ws / "artstyle" / "styles" / f"{style_name}.json",
        ws / "art_style.json",
    ]:
        if candidate.exists():
            return candidate

    return None


class ProjectManager:
    """프로젝트 CRUD, 에셋 등록, 파이프라인 추적, 버전 관리."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or get_db_path()

    # ─────────────────────────────────────
    # 프로젝트 CRUD
    # ─────────────────────────────────────

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

    def resolve_project(self, identifier: str) -> Optional[dict]:
        """uuid(8자 hex) 또는 slug로 프로젝트 조회.

        8자 hex 패턴이면 uuid 우선 조회, fallback으로 slug.
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

    def get_active_project(self) -> Optional[dict]:
        """가장 최근 업데이트된 비-archived 프로젝트 반환."""
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                """SELECT * FROM projects
                   WHERE status != 'archived'
                   ORDER BY updated_at DESC LIMIT 1"""
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_projects(self, status: str = None) -> List[dict]:
        """프로젝트 목록 조회. status 필터 선택."""
        conn = get_connection(self.db_path)
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM projects ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_project(self, project_id: int, **kwargs) -> None:
        """프로젝트 필드 업데이트. kwargs로 컬럼=값 전달."""
        allowed = {
            "name", "status", "topic", "theme", "scene_count",
            "total_duration_sec", "config",
        }
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        if "config" in fields and isinstance(fields["config"], dict):
            fields["config"] = json.dumps(fields["config"], ensure_ascii=False)

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id]

        with transaction(self.db_path) as conn:
            conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?", values
            )

    # ─────────────────────────────────────
    # 프로젝트 Config (art_style, voice_id 등)
    # ─────────────────────────────────────

    def get_config(self, project_id: int) -> dict:
        """프로젝트 config JSON 반환. 없으면 빈 dict."""
        project = self.get_project(project_id=project_id)
        if not project or not project.get("config"):
            return {}
        try:
            return json.loads(project["config"])
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_config(self, project_id: int, config: dict) -> None:
        """프로젝트 config 전체 교체."""
        self.update_project(project_id, config=config)

    def update_config(self, project_id: int, **kwargs) -> None:
        """프로젝트 config에 키-값 머지 (기존 값 유지)."""
        current = self.get_config(project_id)
        current.update(kwargs)
        self.set_config(project_id, current)

    def get_art_style_path(self, project_id: int) -> Optional[str]:
        """프로젝트의 art_style JSON 경로. resolve_art_style_path()로 통합 resolve."""
        config = self.get_config(project_id)
        art_style = config.get("art_style")
        project_dir = self.get_project_dir(project_id)
        result = resolve_art_style_path(art_style, project_dir)
        return str(result) if result else None

    def provision_art_style(self, project_id: int) -> Optional[str]:
        """아트스타일 JSON + 참조 이미지를 프로젝트 출력 폴더에 복사.

        Returns:
            복사된 art_style.json 경로, 또는 None (소스 없음)
        """
        import shutil
        config = self.get_config(project_id)
        art_style_rel = config.get("art_style")
        if not art_style_rel:
            return None

        # resolve_art_style_path로 통합 resolve
        src_path = resolve_art_style_path(art_style_rel)
        if not src_path:
            return None

        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        dest_json = project_dir / "art_style.json"

        # 1) JSON 복사
        shutil.copy2(src_path, dest_json)

        # 2) 참조 이미지 복사
        try:
            import json as _json
            style_data = _json.loads(src_path.read_text(encoding="utf-8"))
            ref_image = style_data.get("reference_image", "")
            if ref_image:
                ref_src = Path(ref_image)
                if not ref_src.is_absolute():
                    ref_src = get_data_dir() / ref_image
                if ref_src.exists():
                    ref_dest = project_dir / ref_src.name
                    shutil.copy2(ref_src, ref_dest)
                    # JSON 내 참조 경로를 로컬 파일명으로 갱신
                    style_data["reference_image"] = ref_src.name
                    dest_json.write_text(
                        _json.dumps(style_data, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
        except Exception:
            pass  # 참조 이미지 복사 실패해도 JSON은 이미 복사됨

        return str(dest_json)

    def get_voice_config(self, project_id: int) -> dict:
        """프로젝트의 TTS 설정 반환. {voice_id, voice_settings}."""
        config = self.get_config(project_id)
        return {
            "voice_id": config.get("voice_id"),
            "voice_settings": config.get("voice_settings"),
        }

    # ─────────────────────────────────────
    # 경로 해석
    # ─────────────────────────────────────

    def get_project_dir(self, project_id: int) -> Path:
        """프로젝트 output 디렉토리 경로."""
        project = self.get_project(project_id=project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        return Path(project["output_dir"])

    def get_scene_specs_path(self, project_id: int) -> Path:
        """scene_specs.json 경로 (프로젝트 디렉토리 내)."""
        return self.get_project_dir(project_id) / "scene_specs.json"

    def get_motion_plan_path(self, project_id: int) -> Path:
        """motion_plan.json 경로."""
        return self.get_project_dir(project_id) / "motion_plan.json"

    def get_manifest_path(self, project_id: int) -> Path:
        """Remotion manifest 경로 (remotion/public/manifests/{slug}.json)."""
        project = self.get_project(project_id=project_id)
        slug = project["slug"]
        return get_workspace_dir() / "remotion" / "public" / "manifests" / f"{slug}.json"

    def get_manuscript_path(self, project_id: int) -> Path:
        """final_manuscript.md 경로."""
        return self.get_project_dir(project_id) / "final_manuscript.md"

    # ─────────────────────────────────────
    # 파이프라인 실행 추적
    # ─────────────────────────────────────

    def start_pipeline_run(
        self,
        project_id: int,
        phase: str,
        step: str,
        step_name: str = None,
        agent_or_module: str = None,
        metadata: dict = None,
    ) -> int:
        """파이프라인 단계 실행 시작. run_id 반환."""
        with transaction(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO pipeline_runs
                   (project_id, phase, step, step_name, agent_or_module,
                    status, started_at, metadata)
                   VALUES (?, ?, ?, ?, ?, 'running', datetime('now'), ?)""",
                (project_id, phase, step, step_name, agent_or_module,
                 json.dumps(metadata, ensure_ascii=False) if metadata else None),
            )
            # 프로젝트 상태도 in_progress로
            conn.execute(
                "UPDATE projects SET status = 'in_progress' WHERE id = ? AND status = 'created'",
                (project_id,),
            )
            return cur.lastrowid

    def complete_pipeline_run(
        self,
        run_id: int,
        cost_tokens_in: int = 0,
        cost_tokens_out: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """파이프라인 단계 완료 처리."""
        with transaction(self.db_path) as conn:
            conn.execute(
                """UPDATE pipeline_runs SET
                   status = 'completed',
                   completed_at = datetime('now'),
                   duration_sec = (julianday(datetime('now')) - julianday(started_at)) * 86400,
                   cost_tokens_in = ?,
                   cost_tokens_out = ?,
                   cost_usd = ?
                   WHERE id = ?""",
                (cost_tokens_in, cost_tokens_out, cost_usd, run_id),
            )

    def fail_pipeline_run(self, run_id: int, error_log: str) -> None:
        """파이프라인 단계 실패 처리."""
        with transaction(self.db_path) as conn:
            conn.execute(
                """UPDATE pipeline_runs SET
                   status = 'failed',
                   completed_at = datetime('now'),
                   duration_sec = (julianday(datetime('now')) - julianday(started_at)) * 86400,
                   error_log = ?
                   WHERE id = ?""",
                (error_log, run_id),
            )

    def get_pipeline_history(self, project_id: int) -> List[dict]:
        """프로젝트의 파이프라인 실행 히스토리."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT * FROM pipeline_runs
                   WHERE project_id = ?
                   ORDER BY created_at DESC""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_cost_summary(self, project_id: int = None) -> dict:
        """비용 요약. project_id 없으면 전체."""
        conn = get_connection(self.db_path)
        try:
            if project_id:
                row = conn.execute(
                    """SELECT
                       COUNT(*) as total_runs,
                       SUM(cost_tokens_in) as total_tokens_in,
                       SUM(cost_tokens_out) as total_tokens_out,
                       SUM(cost_usd) as total_usd,
                       SUM(duration_sec) as total_duration_sec
                       FROM pipeline_runs WHERE project_id = ?""",
                    (project_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT
                       COUNT(*) as total_runs,
                       SUM(cost_tokens_in) as total_tokens_in,
                       SUM(cost_tokens_out) as total_tokens_out,
                       SUM(cost_usd) as total_usd,
                       SUM(duration_sec) as total_duration_sec
                       FROM pipeline_runs"""
                ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def get_cost_by_agent(self, project_id: int) -> List[dict]:
        """에이전트/모듈별 비용 집계."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT agent_or_module,
                   COUNT(*) as run_count,
                   SUM(cost_tokens_in) as tokens_in,
                   SUM(cost_tokens_out) as tokens_out,
                   SUM(cost_usd) as total_usd
                   FROM pipeline_runs
                   WHERE project_id = ? AND agent_or_module IS NOT NULL
                   GROUP BY agent_or_module
                   ORDER BY total_usd DESC""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ─────────────────────────────────────
    # 에셋 등록
    # ─────────────────────────────────────

    def register_asset(
        self,
        project_id: int,
        asset_type: str,
        file_path: str,
        scene_number: int = None,
        metadata: dict = None,
    ) -> int:
        """에셋 파일 등록. asset_id 반환."""
        fp = Path(file_path)
        file_name = fp.name
        file_size = fp.stat().st_size if fp.exists() else 0
        mime = mimetypes.guess_type(str(fp))[0]

        # 상대 경로 계산 (프로젝트 output_dir 기준)
        project = self.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])
        try:
            rel_path = str(fp.relative_to(output_dir))
        except ValueError:
            rel_path = str(fp)

        # 중복 방지: 같은 프로젝트 + 같은 경로면 업데이트
        conn = get_connection(self.db_path)
        try:
            existing = conn.execute(
                "SELECT id FROM assets WHERE project_id = ? AND file_path = ?",
                (project_id, rel_path),
            ).fetchone()
        finally:
            conn.close()

        if existing:
            with transaction(self.db_path) as conn:
                conn.execute(
                    """UPDATE assets SET file_size = ?, mime_type = ?, metadata = ?
                       WHERE id = ?""",
                    (file_size, mime,
                     json.dumps(metadata, ensure_ascii=False) if metadata else None,
                     existing["id"]),
                )
                return existing["id"]

        with transaction(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO assets
                   (project_id, asset_type, scene_number, file_path, file_name,
                    file_size, mime_type, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (project_id, asset_type, scene_number, rel_path, file_name,
                 file_size, mime,
                 json.dumps(metadata, ensure_ascii=False) if metadata else None),
            )
            return cur.lastrowid

    def get_assets(
        self,
        project_id: int,
        asset_type: str = None,
        scene_number: int = None,
    ) -> List[dict]:
        """에셋 조회. 타입/씬 번호 필터 선택."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT * FROM assets WHERE project_id = ?"
            params = [project_id]
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            if scene_number is not None:
                query += " AND scene_number = ?"
                params.append(scene_number)
            query += " ORDER BY scene_number, asset_type"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_asset_counts(self, project_id: int) -> dict:
        """에셋 타입별 개수."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT asset_type, COUNT(*) as count
                   FROM assets WHERE project_id = ?
                   GROUP BY asset_type""",
                (project_id,),
            ).fetchall()
            return {r["asset_type"]: r["count"] for r in rows}
        finally:
            conn.close()

    def get_orphaned_assets(self, project_id: int) -> List[dict]:
        """scene_specs에 참조되지 않는 에셋 탐지."""
        project = self.get_project(project_id=project_id)
        specs_path = Path(project["output_dir"]) / "scene_specs.json"
        if not specs_path.exists():
            return []

        import json as _json
        with open(specs_path, "r", encoding="utf-8") as f:
            specs = _json.load(f)
        scene_numbers = {s["sceneNumber"] for s in specs.get("scenes", [])}

        assets = self.get_assets(project_id)
        orphans = []
        for asset in assets:
            if asset["scene_number"] and asset["scene_number"] not in scene_numbers:
                orphans.append(asset)
        return orphans

    # ─────────────────────────────────────
    # 버전 관리
    # ─────────────────────────────────────

    def save_version(
        self,
        project_id: int,
        file_type: str,
        source_path: Path,
        description: str = None,
        created_by: str = None,
    ) -> int:
        """파일의 현재 버전을 versions/ 디렉토리에 저장하고 DB에 등록."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"{source} not found")

        project = self.get_project(project_id=project_id)
        versions_dir = Path(project["output_dir"]) / "versions"
        versions_dir.mkdir(exist_ok=True)

        # 다음 버전 번호
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                """SELECT MAX(version) as max_ver FROM file_versions
                   WHERE project_id = ? AND file_type = ?""",
                (project_id, file_type),
            ).fetchone()
            next_version = (row["max_ver"] or 0) + 1
        finally:
            conn.close()

        # 파일 복사
        ext = source.suffix
        dest = versions_dir / f"{file_type}_v{next_version:03d}{ext}"

        import shutil
        shutil.copy2(source, dest)

        # 체크섬
        checksum = hashlib.sha256(dest.read_bytes()).hexdigest()
        file_size = dest.stat().st_size

        # 상대 경로
        output_dir = Path(project["output_dir"])
        try:
            rel_path = str(dest.relative_to(output_dir))
        except ValueError:
            rel_path = str(dest)

        with transaction(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO file_versions
                   (project_id, file_type, version, file_path, file_size,
                    checksum, description, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (project_id, file_type, next_version, rel_path, file_size,
                 checksum, description, created_by),
            )
            return cur.lastrowid

    def get_versions(self, project_id: int, file_type: str) -> List[dict]:
        """파일 버전 히스토리 (최신 먼저)."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT * FROM file_versions
                   WHERE project_id = ? AND file_type = ?
                   ORDER BY version DESC""",
                (project_id, file_type),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_latest_version(self, project_id: int, file_type: str) -> Optional[dict]:
        """최신 버전 정보."""
        versions = self.get_versions(project_id, file_type)
        return versions[0] if versions else None

    def rollback_version(
        self, project_id: int, file_type: str, version: int
    ) -> Path:
        """특정 버전으로 롤백. 현재 파일을 새 버전으로 저장 후 복원."""
        import shutil

        # 대상 버전 찾기
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                """SELECT * FROM file_versions
                   WHERE project_id = ? AND file_type = ? AND version = ?""",
                (project_id, file_type, version),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError(f"Version {version} of {file_type} not found")

        project = self.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])
        version_file = output_dir / row["file_path"]

        if not version_file.exists():
            raise FileNotFoundError(f"Version file {version_file} not found")

        # 현재 파일의 활성 경로
        ext = version_file.suffix
        active_path = output_dir / f"{file_type}{ext}"

        # 현재 파일을 버전으로 저장 (있는 경우)
        if active_path.exists():
            self.save_version(
                project_id, file_type, active_path,
                description=f"Auto-save before rollback to v{version}",
                created_by="rollback",
            )

        # 버전 파일을 활성 위치로 복사
        shutil.copy2(version_file, active_path)

        return active_path

    # ─────────────────────────────────────
    # 라이선스 추적
    # ─────────────────────────────────────

    def register_license(
        self,
        asset_id: int,
        source: str,
        source_url: str = None,
        license_type: str = None,
        attribution: str = None,
        title: str = None,
    ) -> int:
        """에셋에 라이선스 정보 등록."""
        with transaction(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO asset_licenses
                   (asset_id, source, source_url, license_type, attribution, title)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (asset_id, source, source_url, license_type, attribution, title),
            )
            return cur.lastrowid

    def get_licenses(self, project_id: int) -> List[dict]:
        """프로젝트의 모든 라이선스 정보."""
        conn = get_connection(self.db_path)
        try:
            rows = conn.execute(
                """SELECT al.*, a.file_path, a.scene_number
                   FROM asset_licenses al
                   JOIN assets a ON al.asset_id = a.id
                   WHERE a.project_id = ?
                   ORDER BY a.scene_number""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
