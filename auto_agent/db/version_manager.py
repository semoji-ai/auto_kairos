"""
파일 버전 관리 유틸리티.
ProjectManager.save_version/rollback_version의 고수준 래퍼.
보존 정책(retention policy) 적용.
"""
from pathlib import Path
from typing import Dict, List, Optional

from .project_manager import ProjectManager


DEFAULT_RETENTION = {
    "scene_specs": 5,
    "motion_plan": 5,
    "manuscript": 3,
    "scene_decomposition": 3,
    "outline": 3,
    "manifest": 3,
    "character_plan": 3,
    "art_style": 2,
    "subtitles_json": 3,
    "other": 3,
}


class VersionManager:
    """파일 버전 저장 + 보존 정책 적용."""

    def __init__(self, pm: ProjectManager = None):
        self.pm = pm or ProjectManager()

    def save_and_enforce(
        self,
        project_id: int,
        file_type: str,
        source_path: Path,
        description: str = None,
        created_by: str = None,
        keep_last: int = None,
    ) -> int:
        """버전 저장 후 보존 정책 적용. version_id 반환."""
        version_id = self.pm.save_version(
            project_id, file_type, source_path, description, created_by
        )
        retention = keep_last or DEFAULT_RETENTION.get(file_type, 5)
        self.enforce_retention(project_id, file_type, retention)
        return version_id

    def enforce_retention(
        self, project_id: int, file_type: str, keep_last: int = 5
    ) -> List[str]:
        """보존 정책 적용. 삭제된 파일 경로 목록 반환."""
        versions = self.pm.get_versions(project_id, file_type)
        if len(versions) <= keep_last:
            return []

        to_delete = versions[keep_last:]  # versions는 최신 먼저 정렬
        deleted = []
        project = self.pm.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])

        from .connection import transaction
        with transaction(self.pm.db_path) as conn:
            for v in to_delete:
                file_path = output_dir / v["file_path"]
                if file_path.exists():
                    file_path.unlink()
                    deleted.append(str(file_path))
                conn.execute(
                    "DELETE FROM file_versions WHERE id = ?", (v["id"],)
                )

        return deleted

    def enforce_all(self, project_id: int) -> Dict[str, List[str]]:
        """프로젝트의 모든 file_type에 대해 보존 정책 적용."""
        result = {}
        from .connection import get_connection
        conn = get_connection(self.pm.db_path)
        try:
            rows = conn.execute(
                """SELECT DISTINCT file_type FROM file_versions
                   WHERE project_id = ?""",
                (project_id,),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            ft = row["file_type"]
            retention = DEFAULT_RETENTION.get(ft, 5)
            deleted = self.enforce_retention(project_id, ft, retention)
            if deleted:
                result[ft] = deleted

        return result
