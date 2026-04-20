"""
프로젝트 출력 디렉토리 관리 유틸리티 (v3 — 이중 루트 + DB 연동)

모든 scripts/*.py 에서 공통으로 사용.
output/{project_name}/ 구조를 통일한다.

경로 해석:
  WORKSPACE_DIR: output, .env, DB, remotion (읽기/쓰기)
  DATA_DIR: pipeline.json, agents.json, skills, artstyle (읽기 전용)

프로젝트 디렉토리 결정 우선순위:
  1. --project <name> CLI 인자 (DB slug 조회 포함)
  2. PROJECT_NAME 환경 변수 (DB slug 조회 포함)
  3. DB: 활성 프로젝트 (가장 최근 업데이트)
  4. output/ 내 단일 서브디렉토리 자동 감지
  5. scene_specs.json의 theme 필드로 자동 생성
  6. 폴백: output/default/
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from auto_agent.paths import get_workspace_dir, get_data_dir, PACKAGE_DIR, DATA_DIR

# 하위 호환: PROJECT_ROOT → WORKSPACE_DIR
PROJECT_ROOT = get_workspace_dir()


def slugify(text: str) -> str:
    """한/영 텍스트를 안전한 폴더명으로 변환"""
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    text = re.sub(r"[\s]+", "_", text.strip())
    return text[:60] or "default"


def _try_db_project(slug: str = None):
    """DB에서 프로젝트 조회 시도. (project_dir, project_id) 또는 None 반환."""
    try:
        from auto_agent.db.connection import db_exists
        if not db_exists():
            return None
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        if slug:
            project = pm.get_project(slug=slug)
        else:
            project = pm.get_active_project()
        if project:
            d = Path(project["output_dir"])
            d.mkdir(parents=True, exist_ok=True)
            return d, project["id"]
    except Exception:
        pass
    return None


def _try_resolve_project_dir(identifier: str) -> Optional[Path]:
    """DB에서 프로젝트 디렉토리 조회. 실패하면 None."""
    try:
        from auto_agent.db.connection import db_exists
        if not db_exists():
            return None
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.resolve_project(identifier)
        if project and Path(project["output_dir"]).exists():
            return Path(project["output_dir"])
    except Exception:
        pass
    return None


def _get_manifest_filename(identifier: str, fallback: str) -> str:
    """DB에서 uuid_{slug}.json 파일명 조회. 실패 시 fallback 반환."""
    try:
        from auto_agent.db.connection import db_exists
        if not db_exists():
            return fallback
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        fname = pm.get_manifest_filename(slug=identifier)
        return fname if fname else fallback
    except Exception:
        return fallback


def get_project_dir() -> Path:
    """프로젝트 출력 디렉토리(output/{name}/) 반환. 없으면 생성."""
    workspace = get_workspace_dir()

    # 1) --project CLI 인자
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            name = sys.argv[i + 1]
            # DB 조회 시도
            result = _try_db_project(slug=name)
            if result:
                return result[0]
            d = workspace / "output" / name
            d.mkdir(parents=True, exist_ok=True)
            return d

    # 2) PROJECT_NAME 환경 변수
    env_name = os.getenv("PROJECT_NAME")
    if env_name:
        # DB 조회 시도
        result = _try_db_project(slug=env_name)
        if result:
            return result[0]
        d = workspace / "output" / env_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    # 3) DB: 활성 프로젝트
    result = _try_db_project()
    if result:
        return result[0]

    # 4) output/ 내 단일 서브디렉토리 자동 감지
    output_base = workspace / "output"
    if output_base.exists():
        subdirs = [
            p for p in output_base.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]
        if len(subdirs) == 1:
            return subdirs[0]

    # 5) scene_specs.json에서 이름 추출 (레거시)
    specs_path = workspace / "scene_specs.json"
    if specs_path.exists():
        with open(specs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("theme") or data.get("topic") or "project"
        name = slugify(name)
        d = output_base / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    # 6) 폴백
    d = output_base / "default"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_scene_specs_path() -> Path:
    """scene_specs.json 경로. DB 모드: 프로젝트 디렉토리 내, 레거시: 루트."""
    workspace = get_workspace_dir()
    # PROJECT_NAME 환경변수 우선
    env_name = os.getenv("PROJECT_NAME")
    if env_name:
        result = _try_db_project(slug=env_name)
        if result:
            project_dir, _ = result
            path = project_dir / "scene_specs.json"
            if path.exists():
                return path
    # 활성 프로젝트 폴백
    result = _try_db_project()
    if result:
        project_dir, _ = result
        path = project_dir / "scene_specs.json"
        if path.exists():
            return path
    # 레거시 폴백
    return workspace / "scene_specs.json"


def get_motion_plan_path() -> Path:
    """motion_plan.json 경로. DB 모드: 프로젝트 디렉토리 내, 레거시: 루트."""
    workspace = get_workspace_dir()
    result = _try_db_project()
    if result:
        project_dir, _ = result
        path = project_dir / "motion_plan.json"
        if path.exists():
            return path
    return workspace / "motion_plan.json"


def get_manifest_path() -> Path:
    """manifest.json 출력 경로. DB 모드: manifests/{uuid}_{slug}.json, 레거시: manifest.json."""
    workspace = get_workspace_dir()
    manifests_dir = workspace / "remotion" / "public" / "manifests"

    # --project CLI 인자에서 식별자 추출 (rebuild-manifest 호출 시)
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            identifier = sys.argv[i + 1]
            # DB에서 uuid_slug.json 파일명 조회; 실패 시 identifier 그대로 사용
            slug = Path(identifier).name  # 경로로 전달된 경우 최말단 이름만 추출
            fname = _get_manifest_filename(slug, fallback=f"{slug}.json")
            return manifests_dir / fname

    result = _try_db_project()
    if result:
        project_dir, pid = result
        # project_dir.name은 output_dir의 basename → {uuid}_{slug} 형식
        dir_name = project_dir.name
        fname = _get_manifest_filename(dir_name, fallback=f"{dir_name}.json")
        return manifests_dir / fname
    return workspace / "remotion" / "public" / "manifest.json"
