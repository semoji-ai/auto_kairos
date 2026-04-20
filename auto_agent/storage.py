"""
Supabase Storage 중심 파일 I/O 레이어.

모든 파이프라인 파일(JSON, 텍스트, 바이너리)을
Supabase Storage에 저장/조회하는 단일 인터페이스.

사용법:
    from auto_agent.storage import ProjectStorage
    ps = ProjectStorage(project_id)

    # JSON 저장/로드
    ps.save_json("research_report.json", data)
    data = ps.load_json("research_report.json")

    # 텍스트 저장/로드
    ps.save_text("final_manuscript.md", text)
    text = ps.load_text("final_manuscript.md")

    # 바이너리 파일 업로드 (이미지, 오디오 등)
    url = ps.upload("images/scene_001.jpg", image_bytes)
    url = ps.upload_local("images/scene_001.jpg", "/tmp/scene_001.jpg")

    # 에셋 등록
    ps.register_asset("image", scene_number=1, url=url)

    # public URL 가져오기
    url = ps.get_url("images/scene_001.jpg")
"""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Optional

from auto_agent.supabase_client import get_supabase, BUCKET_NAME


class ProjectStorage:
    """프로젝트별 Supabase Storage 래퍼."""

    def __init__(self, project_id: str, storage_key: str = None):
        self.project_id = project_id
        self._sb = None
        self._storage_key = storage_key

    @property
    def sb(self):
        if self._sb is None:
            self._sb = get_supabase()
        return self._sb

    @property
    def storage_key(self) -> str:
        if self._storage_key is None:
            resp = (
                self.sb.table("projects")
                .select("storage_key")
                .eq("id", self.project_id)
                .execute()
            )
            if resp.data:
                self._storage_key = resp.data[0]["storage_key"]
            else:
                raise ValueError(f"프로젝트 {self.project_id}의 storage_key를 찾을 수 없습니다.")
        return self._storage_key

    def _path(self, relative: str) -> str:
        """storage_key 기반 전체 경로."""
        return f"{self.storage_key}/{relative}"

    # ── JSON ──

    def save_json(self, filename: str, data: dict) -> str:
        """JSON 파일 저장. public URL 반환."""
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return self.upload(filename, content, "application/json")

    def load_json(self, filename: str) -> Optional[dict]:
        """JSON 파일 로드. 없으면 None."""
        try:
            data = self.sb.storage.from_(BUCKET_NAME).download(self._path(filename))
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    # ── 텍스트 ──

    def save_text(self, filename: str, text: str) -> str:
        """텍스트 파일 저장. public URL 반환."""
        content = text.encode("utf-8")
        ct = "text/markdown" if filename.endswith(".md") else "text/plain"
        return self.upload(filename, content, ct)

    def load_text(self, filename: str) -> Optional[str]:
        """텍스트 파일 로드. 없으면 None."""
        try:
            data = self.sb.storage.from_(BUCKET_NAME).download(self._path(filename))
            return data.decode("utf-8")
        except Exception:
            return None

    # ── 바이너리 업로드 ──

    def upload(self, relative_path: str, content: bytes,
               content_type: str = None) -> str:
        """바이너리 데이터를 Storage에 업로드. public URL 반환."""
        if not content_type:
            content_type = mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        self.sb.storage.from_(BUCKET_NAME).upload(
            path=self._path(relative_path),
            file=content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return self.get_url(relative_path)

    def upload_local(self, relative_path: str, local_path: str) -> str:
        """로컬 파일을 Storage에 업로드. public URL 반환."""
        with open(local_path, "rb") as f:
            content = f.read()
        return self.upload(relative_path, content)

    # ── URL 조회 ──

    def get_url(self, relative_path: str) -> str:
        """파일의 public URL 반환."""
        return self.sb.storage.from_(BUCKET_NAME).get_public_url(self._path(relative_path))

    # ── 에셋 등록 ──

    def register_asset(self, asset_type: str, scene_number: int = None,
                       file_path: str = "", storage_url: str = "",
                       metadata: dict = None) -> str:
        """에셋을 assets 테이블에 등록. 에셋 ID 반환."""
        file_name = Path(file_path).name if file_path else ""
        row = {
            "project_id": self.project_id,
            "asset_type": asset_type,
            "scene_number": scene_number,
            "file_path": file_path,
            "file_name": file_name,
            "storage_url": storage_url,
            "metadata": metadata or {},
        }
        resp = self.sb.table("assets").upsert(
            row, on_conflict="project_id,asset_type,scene_number,file_path"
        ).execute()
        return resp.data[0]["id"] if resp.data else ""

    # ── 파이프라인 이력 ──

    def start_run(self, phase: str, step: str, step_name: str = None,
                  agent: str = None) -> str:
        """파이프라인 실행 시작. run_id 반환."""
        row = {
            "project_id": self.project_id,
            "phase": phase,
            "step": step,
            "step_name": step_name,
            "agent_or_module": agent,
            "status": "running",
        }
        resp = self.sb.table("pipeline_runs").insert(row).execute()
        return resp.data[0]["id"]

    def complete_run(self, run_id: str, cost_tokens_in: int = 0,
                     cost_tokens_out: int = 0, cost_usd: float = 0.0) -> None:
        """파이프라인 실행 완료."""
        self.sb.table("pipeline_runs").update({
            "status": "completed",
            "cost_tokens_in": cost_tokens_in,
            "cost_tokens_out": cost_tokens_out,
            "cost_usd": cost_usd,
        }).eq("id", run_id).execute()

    def fail_run(self, run_id: str, error: str) -> None:
        """파이프라인 실행 실패."""
        self.sb.table("pipeline_runs").update({
            "status": "failed",
            "error_log": error[:5000],
        }).eq("id", run_id).execute()


def get_project_storage(slug: str) -> ProjectStorage:
    """slug → ProjectStorage 인스턴스."""
    sb = get_supabase()
    resp = sb.table("projects").select("id, storage_key").eq("slug", slug).execute()
    if not resp.data:
        raise ValueError(f"프로젝트 '{slug}'를 찾을 수 없습니다.")
    row = resp.data[0]
    return ProjectStorage(row["id"], row["storage_key"])
