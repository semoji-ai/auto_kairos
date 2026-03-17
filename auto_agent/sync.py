"""
Supabase 동기화 모듈.

push (로컬 → Supabase):
  스텝 완료 후 자동 호출, 또는 CLI에서 수동 실행
  auto-agent sync --project <slug>

pull (Supabase → 로컬):
  웹에서 수정한 에셋을 로컬로 다운로드
  auto-agent pull --project <slug>
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Optional

from auto_agent.supabase_client import (
    get_supabase,
    supabase_enabled,
    BUCKET_NAME,
)


class SyncManager:
    """프로젝트 단위 Supabase 동기화."""

    def __init__(self, project_slug: str, project_dir: Path, local_project_id=None):
        self.slug = project_slug
        self.storage_key = _to_storage_key(project_slug)
        self.file_prefix = self.storage_key.replace("proj-", "")[:6]  # 6자 해시 프리픽스
        self.project_dir = Path(project_dir)
        self.local_project_id = local_project_id
        self._sb = None
        self._remote_project_id: Optional[str] = None

    @property
    def sb(self):
        if self._sb is None:
            self._sb = get_supabase()
        return self._sb

    # ──────────────────────────────────────────
    # 프로젝트 upsert
    # ──────────────────────────────────────────
    def ensure_project(self, project_data: dict) -> str:
        """Supabase projects 테이블에 upsert. remote UUID 반환."""
        if self._remote_project_id:
            return self._remote_project_id

        row = {
            "storage_key": self.storage_key,
            "name": project_data.get("name", self.slug),
            "slug": self.slug,
            "status": project_data.get("status", "in_progress"),
            "topic": project_data.get("topic"),
            "theme": project_data.get("theme", "simple"),
            "scene_count": project_data.get("scene_count", 0),
            "total_duration_sec": project_data.get("total_duration_sec", 0.0),
            "config": project_data.get("config") if isinstance(project_data.get("config"), dict) else None,
            "output_dir": project_data.get("output_dir"),
        }
        if isinstance(self.local_project_id, int):
            row["local_id"] = self.local_project_id

        # slug 기준 upsert
        resp = (
            self.sb.table("projects")
            .upsert(row, on_conflict="slug")
            .execute()
        )
        self._remote_project_id = resp.data[0]["id"]
        return self._remote_project_id

    # ──────────────────────────────────────────
    # 파이프라인 실행 기록 동기화
    # ──────────────────────────────────────────
    def sync_pipeline_run(
        self,
        project_id: str,
        phase: str,
        step: str,
        step_name: str,
        agent_or_module: str,
        status: str,
        duration_sec: float = 0.0,
        cost_tokens_in: int = 0,
        cost_tokens_out: int = 0,
        cost_usd: float = 0.0,
        error_log: Optional[str] = None,
    ):
        """pipeline_runs에 기록 추가."""
        row = {
            "project_id": project_id,
            "phase": phase,
            "step": step,
            "step_name": step_name,
            "agent_or_module": agent_or_module,
            "status": status,
            "duration_sec": duration_sec,
            "cost_tokens_in": cost_tokens_in,
            "cost_tokens_out": cost_tokens_out,
            "cost_usd": cost_usd,
            "error_log": error_log,
        }
        self.sb.table("pipeline_runs").insert(row).execute()

    # ──────────────────────────────────────────
    # 파일 업로드 + 에셋 등록
    # ──────────────────────────────────────────
    def upload_json(self, filename: str, data: dict) -> str:
        """JSON 데이터를 Supabase Storage에 직접 업로드. public URL 반환."""
        import json as _json
        storage_path = f"{self.storage_key}/{filename}"
        content = _json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.sb.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=content,
            file_options={
                "content-type": "application/json",
                "upsert": "true",
            },
        )
        return self.sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    def upload_file(self, local_path: Path, storage_path: str) -> str:
        """파일을 Supabase Storage에 업로드. public URL 반환."""
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"

        with open(local_path, "rb") as f:
            self.sb.storage.from_(BUCKET_NAME).upload(
                path=storage_path,
                file=f,
                file_options={
                    "content-type": content_type,
                    "upsert": "true",
                },
            )

        return self.sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    def register_asset(
        self,
        project_id: str,
        local_path: Path,
        asset_type: str,
        scene_number: Optional[int] = None,
    ) -> str:
        """파일 업로드 + assets 테이블 등록. public URL 반환.

        파일 네이밍 규칙:
          - 에셋 파일: {storage_key}/{asset_type}/{prefix}_{filename}
          - 프리픽스: storage_key에서 proj- 제거 후 앞 6자
          - JSON 메타데이터: {storage_key}/{filename} (프리픽스 없음)
        """
        # 에셋 타입별 폴더 매핑
        ASSET_FOLDERS = {
            "audio": "audio",
            "image": "images",
            "subtitle": "subtitles",
            "character": "characters",
            "viz_bg": "images/viz_bg",
        }

        folder = ASSET_FOLDERS.get(asset_type)
        original_name = local_path.name

        if folder:
            # 에셋 파일: 폴더 + 프리픽스 적용
            prefixed_name = f"{self.file_prefix}_{original_name}"
            storage_path = f"{self.storage_key}/{folder}/{prefixed_name}"
        else:
            # JSON 등 메타데이터: 루트에 프리픽스 없이
            storage_path = f"{self.storage_key}/{original_name}"
        public_url = self.upload_file(local_path, storage_path)

        checksum = _sha256(local_path)
        file_size = local_path.stat().st_size

        row = {
            "project_id": project_id,
            "asset_type": asset_type,
            "scene_number": scene_number,
            "file_path": storage_path,
            "file_name": f"{self.file_prefix}_{original_name}" if folder else original_name,
            "file_size": file_size,
            "checksum": checksum,
            "mime_type": mimetypes.guess_type(str(local_path))[0],
            "storage_url": public_url,
        }

        # checksum 기준으로 중복 방지
        existing = (
            self.sb.table("assets")
            .select("id")
            .eq("project_id", project_id)
            .eq("file_path", storage_path)
            .execute()
        )
        if existing.data:
            self.sb.table("assets").update(row).eq("id", existing.data[0]["id"]).execute()
        else:
            self.sb.table("assets").insert(row).execute()

        return public_url

    # ──────────────────────────────────────────
    # 스텝 완료 후 통합 동기화
    # ──────────────────────────────────────────
    def sync_step(
        self,
        step: dict,
        phase: str,
        status: str,
        output_files: list[str],
        cost_info: dict,
        project_data: dict,
        duration_sec: float = 0.0,
    ):
        """스텝 완료 후 호출하는 통합 동기화 메서드.

        1. 프로젝트 upsert
        2. 파이프라인 실행 기록
        3. 출력 파일 업로드
        """
        remote_pid = self.ensure_project(project_data)

        step_id = step.get("id", "")
        step_name = step.get("name", step_id)
        agent_or_module = step.get("agent") or step.get("module", "")

        # 파이프라인 기록
        self.sync_pipeline_run(
            project_id=remote_pid,
            phase=phase,
            step=step_id,
            step_name=step_name,
            agent_or_module=agent_or_module,
            status=status,
            duration_sec=duration_sec,
            cost_tokens_in=cost_info.get("tokens_in", 0),
            cost_tokens_out=cost_info.get("tokens_out", 0),
            cost_usd=cost_info.get("cost_usd", 0.0),
        )

        if status != "completed":
            return

        # 출력 파일 업로드 (디렉토리면 하위 파일 순회)
        UPLOAD_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".json", ".md", ".srt"}
        for file_path_str in output_files:
            fp = Path(file_path_str)
            if not fp.exists():
                continue

            targets = []
            if fp.is_dir():
                for child in sorted(fp.rglob("*")):
                    if child.is_file() and child.suffix.lower() in UPLOAD_EXTS:
                        targets.append(child)
            else:
                targets.append(fp)

            for target in targets:
                asset_type = _infer_asset_type(target)
                scene_num = _extract_scene_number(target.name)

                self.register_asset(
                    project_id=remote_pid,
                    local_path=target,
                    asset_type=asset_type,
                    scene_number=scene_num,
                )

    # ──────────────────────────────────────────
    # push: 로컬 전체 → Supabase (CLI용)
    # ──────────────────────────────────────────
    def push_all(self, project_data: dict) -> dict:
        """로컬 프로젝트의 주요 파일을 모두 Supabase에 업로드.

        Returns: {"project_id": str, "uploaded": int, "skipped": int}
        """
        remote_pid = self.ensure_project(project_data)

        # 동기화 대상 파일 패턴
        target_files = []
        # 루트 JSON/MD 파일
        for p in self.project_dir.iterdir():
            if p.is_file() and p.suffix in (".json", ".md"):
                target_files.append(p)
        # images/ 폴더
        images_dir = self.project_dir / "images"
        if images_dir.exists():
            for p in images_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    target_files.append(p)
        # audio/ 폴더
        audio_dir = self.project_dir / "audio"
        if audio_dir.exists():
            for p in audio_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".wav", ".mp3", ".ogg"):
                    target_files.append(p)
        # subtitles/
        subs_dir = self.project_dir / "subtitles"
        if subs_dir.exists():
            for p in subs_dir.rglob("*"):
                if p.is_file():
                    target_files.append(p)

        uploaded = 0
        skipped = 0
        for fp in target_files:
            try:
                asset_type = _infer_asset_type(fp)
                scene_num = _extract_scene_number(fp.name)
                self.register_asset(remote_pid, fp, asset_type, scene_num)
                uploaded += 1
            except Exception as e:
                print(f"    [SKIP] {fp.name}: {e}")
                skipped += 1

        return {"project_id": remote_pid, "uploaded": uploaded, "skipped": skipped}

    # ──────────────────────────────────────────
    # pull: Supabase → 로컬
    # ──────────────────────────────────────────
    def pull(self, asset_types: Optional[list[str]] = None) -> dict:
        """Supabase에서 프로젝트 에셋을 로컬로 다운로드.

        Args:
            asset_types: 다운로드할 에셋 타입 필터 (None이면 전체)

        Returns: {"downloaded": int, "skipped": int}
        """
        # remote project 찾기
        resp = (
            self.sb.table("projects")
            .select("id,storage_key")
            .eq("slug", self.slug)
            .execute()
        )
        if not resp.data:
            raise ValueError(f"Supabase에 프로젝트 '{self.slug}'가 없습니다.")

        remote_pid = resp.data[0]["id"]
        storage_key = resp.data[0].get("storage_key") or self.storage_key

        # assets 목록 조회
        query = (
            self.sb.table("assets")
            .select("file_path,file_name,checksum,asset_type")
            .eq("project_id", remote_pid)
        )
        if asset_types:
            query = query.in_("asset_type", asset_types)
        assets_resp = query.execute()

        downloaded = 0
        skipped = 0

        for asset in assets_resp.data:
            storage_path = asset["file_path"]
            # storage_path: "proj-xxx/scene_specs.json" → 로컬: project_dir/scene_specs.json
            rel = storage_path.removeprefix(f"{storage_key}/")
            local_path = self.project_dir / rel
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # checksum 비교 — 로컬 파일이 이미 최신이면 스킵
            if local_path.exists() and asset.get("checksum"):
                local_hash = _sha256(local_path)
                if local_hash == asset["checksum"]:
                    skipped += 1
                    continue

            # Storage에서 다운로드
            try:
                data = self.sb.storage.from_(BUCKET_NAME).download(storage_path)
                local_path.write_bytes(data)
                downloaded += 1
            except Exception as e:
                print(f"    [FAIL] {asset['file_name']}: {e}")
                skipped += 1

        return {"downloaded": downloaded, "skipped": skipped}


# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────
def _to_storage_key(slug: str) -> str:
    """slug → ASCII-safe Storage 키."""
    import re
    import unicodedata
    normalized = unicodedata.normalize("NFKD", slug)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    # 특수문자 정리
    ascii_str = re.sub(r"[^a-zA-Z0-9_\-]", "-", ascii_str)
    ascii_str = re.sub(r"-+", "-", ascii_str).strip("-").lower()
    alpha_count = sum(1 for c in ascii_str if c.isalpha())
    if alpha_count < 3:
        # 한글 전용 slug → 짧은 해시 폴백
        h = hashlib.md5(slug.encode()).hexdigest()[:10]
        ascii_str = f"proj-{h}"
    return ascii_str


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _infer_asset_type(path: Path) -> str:
    """파일 확장자/이름에서 에셋 타입 추론."""
    suffix = path.suffix.lower()
    name = path.name.lower()

    if suffix in (".wav", ".mp3", ".ogg"):
        return "audio"
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return "image"
    if suffix == ".srt" or "subtitle" in name:
        return "subtitle"
    if suffix in (".mp4", ".webm"):
        return "video"
    if suffix == ".md":
        return "manuscript"
    if suffix == ".json":
        return "json"
    return "other"


def _extract_scene_number(filename: str) -> Optional[int]:
    """파일명에서 씬 번호 추출. scene_003_bg.jpg → 3."""
    import re
    m = re.search(r"scene[_\-]?(\d{1,3})", filename, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None
