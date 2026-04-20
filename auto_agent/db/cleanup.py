"""
자동 클린업 시스템.
- 오래된 버전 파일 삭제 (보존 정책)
- 백업 파일 정리 (*.bak.*, *_backup.*)
- 고아 에셋 탐지 (scene_specs에 참조되지 않는 파일)
- 임시 파일 정리
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .connection import get_connection, transaction, PROJECT_ROOT
from .project_manager import ProjectManager
from .version_manager import VersionManager, DEFAULT_RETENTION


class CleanupManager:
    """프로젝트 에셋 클린업."""

    def __init__(self, pm: ProjectManager = None):
        self.pm = pm or ProjectManager()
        self.vm = VersionManager(self.pm)

    def cleanup_old_versions(
        self, project_id: int, keep_last: int = None
    ) -> Dict[str, List[str]]:
        """파일 타입별 보존 정책 적용. 초과 버전 삭제."""
        return self.vm.enforce_all(project_id)

    def cleanup_backup_files(
        self, project_id: int, dry_run: bool = True
    ) -> List[str]:
        """*.bak.*, *_backup.*, *_creative_backup.* 패턴 파일 삭제."""
        project = self.pm.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])

        patterns = ["*.bak.*", "*_backup.*", "*_backup_*"]
        found = []

        for pattern in patterns:
            for f in output_dir.glob(pattern):
                if f.is_file():
                    found.append(str(f))

        # 루트에도 검색
        for pattern in patterns:
            for f in PROJECT_ROOT.glob(pattern):
                if f.is_file():
                    found.append(str(f))

        if not dry_run:
            for fp in found:
                Path(fp).unlink(missing_ok=True)

        return found

    def find_orphaned_assets(self, project_id: int) -> Dict[str, List[str]]:
        """scene_specs에 참조되지 않는 에셋 파일 탐지."""
        project = self.pm.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])

        # 현재 scene_specs에서 참조되는 씬 번호
        specs_path = output_dir / "scene_specs.json"
        if not specs_path.exists():
            return {}

        with open(specs_path, "r", encoding="utf-8") as f:
            specs = json.load(f)
        scene_numbers = {s["sceneNumber"] for s in specs.get("scenes", [])}

        orphans = {"audio": [], "image": [], "subtitle": []}

        # 오디오
        audio_dir = output_dir / "audio"
        if audio_dir.exists():
            for f in audio_dir.glob("scene_*.mp3"):
                m = re.search(r"scene_(\d+)", f.name)
                if m and int(m.group(1)) not in scene_numbers:
                    orphans["audio"].append(str(f))

        # 이미지
        images_dir = output_dir / "images"
        if images_dir.exists():
            for f in images_dir.glob("scene_*.png"):
                m = re.search(r"scene_(\d+)", f.name)
                if m and int(m.group(1)) not in scene_numbers:
                    orphans["image"].append(str(f))

        # 자막
        subtitle_dir = output_dir / "subtitles"
        if subtitle_dir.exists():
            for f in subtitle_dir.glob("scene_*.srt"):
                m = re.search(r"scene_(\d+)", f.name)
                if m and int(m.group(1)) not in scene_numbers:
                    orphans["subtitle"].append(str(f))

        # 빈 카테고리 제거
        return {k: v for k, v in orphans.items() if v}

    def cleanup_orphaned_assets(
        self, project_id: int, dry_run: bool = True
    ) -> Dict[str, List[str]]:
        """고아 에셋 삭제."""
        orphans = self.find_orphaned_assets(project_id)
        if not dry_run:
            for category, files in orphans.items():
                for fp in files:
                    Path(fp).unlink(missing_ok=True)
            # DB에서도 제거
            db_orphans = self.pm.get_orphaned_assets(project_id)
            with transaction(self.pm.db_path) as conn:
                for asset in db_orphans:
                    conn.execute("DELETE FROM assets WHERE id = ?", (asset["id"],))
        return orphans

    def cleanup_temp_dirs(
        self, project_id: int, dry_run: bool = True
    ) -> List[str]:
        """임시 디렉토리 정리 (audio_backup/ 등)."""
        project = self.pm.get_project(project_id=project_id)
        output_dir = Path(project["output_dir"])

        temp_dirs = ["audio_backup"]
        removed = []

        for dirname in temp_dirs:
            d = output_dir / dirname
            if d.exists() and d.is_dir():
                removed.append(str(d))
                if not dry_run:
                    import shutil
                    shutil.rmtree(d)

        return removed

    def full_cleanup(
        self, project_id: int, dry_run: bool = True
    ) -> dict:
        """전체 클린업 실행. dry_run=True면 미리보기만."""
        result = {
            "versions_cleaned": {},
            "backups_found": [],
            "orphans_found": {},
            "temp_dirs_found": [],
        }

        # 1. 버전 보존 정책
        if not dry_run:
            result["versions_cleaned"] = self.cleanup_old_versions(project_id)

        # 2. 백업 파일
        result["backups_found"] = self.cleanup_backup_files(project_id, dry_run)

        # 3. 고아 에셋
        if dry_run:
            result["orphans_found"] = self.find_orphaned_assets(project_id)
        else:
            result["orphans_found"] = self.cleanup_orphaned_assets(project_id, dry_run=False)

        # 4. 임시 디렉토리
        result["temp_dirs_found"] = self.cleanup_temp_dirs(project_id, dry_run)

        return result
