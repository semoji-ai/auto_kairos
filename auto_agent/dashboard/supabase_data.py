"""
Supabase 기반 프로젝트 데이터 액세스 레이어 (SSOT).

모든 프로젝트 데이터(DB + Storage)를 Supabase에서 관리.
로컬 파일 시스템 의존 없음. (manifest.json만 로컬 생성)

사용법:
    from auto_agent.dashboard.supabase_data import SupabaseProjectManager
    pm = SupabaseProjectManager()
    projects = pm.list_projects()
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import List, Optional

from auto_agent.supabase_client import get_supabase, BUCKET_NAME


class SupabaseProjectManager:
    """Supabase 기반 프로젝트 매니저. 대시보드 읽기/쓰기 전용."""

    def __init__(self):
        self._sb = None

    @property
    def sb(self):
        if self._sb is None:
            self._sb = get_supabase()
        return self._sb

    # ──────────────────────────────────────
    # 프로젝트 CRUD
    # ──────────────────────────────────────

    def list_projects(self, status: str = None) -> List[dict]:
        query = self.sb.table("projects").select("*").order("updated_at", desc=True)
        if status:
            query = query.eq("status", status)
        resp = query.execute()
        return [self._normalize_project(p) for p in resp.data]

    def get_project(self, project_id: int = None, slug: str = None) -> Optional[dict]:
        if slug:
            resp = self.sb.table("projects").select("*").eq("slug", slug).execute()
        elif project_id:
            resp = self.sb.table("projects").select("*").eq("local_id", project_id).execute()
        else:
            return None
        if not resp.data:
            return None
        return self._normalize_project(resp.data[0])

    def create_project(
        self,
        name: str,
        slug: str,
        topic: str = None,
        theme: str = "simple",
        config: dict = None,
    ) -> str:
        """프로젝트 생성. Supabase UUID 반환."""
        storage_key = "proj-" + hashlib.sha1(slug.encode()).hexdigest()[:10]
        row = {
            "name": name,
            "slug": slug,
            "topic": topic or name,
            "theme": theme,
            "config": config or {},
            "status": "draft",
            "scene_count": 0,
            "storage_key": storage_key,
        }
        resp = self.sb.table("projects").insert(row).execute()
        return resp.data[0]["id"]

    def delete_project(self, project_id: str) -> None:
        """프로젝트 + 관련 데이터 삭제."""
        # 에셋, 파이프라인 이력, 버전 먼저 삭제
        self.sb.table("assets").delete().eq("project_id", project_id).execute()
        self.sb.table("pipeline_runs").delete().eq("project_id", project_id).execute()
        self.sb.table("file_versions").delete().eq("project_id", project_id).execute()
        self.sb.table("projects").delete().eq("id", project_id).execute()

    def get_active_project(self) -> Optional[dict]:
        resp = (
            self.sb.table("projects")
            .select("*")
            .neq("status", "archived")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return self._normalize_project(resp.data[0])

    def update_project(self, project_id: str, **kwargs) -> None:
        row = {}
        for key in ("name", "status", "topic", "theme", "scene_count",
                     "total_duration_sec", "config"):
            if key in kwargs:
                val = kwargs[key]
                if key == "config" and isinstance(val, dict):
                    row[key] = val
                else:
                    row[key] = val
        if row:
            self.sb.table("projects").update(row).eq("id", project_id).execute()

    # ──────────────────────────────────────
    # 프로젝트 Config
    # ──────────────────────────────────────

    def get_config(self, project_id: str) -> dict:
        """프로젝트 config JSON 반환."""
        project = self.get_project(project_id=project_id)
        if not project:
            return {}
        config = project.get("config")
        if isinstance(config, str):
            try:
                return json.loads(config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return config or {}

    def set_config(self, project_id: str, config: dict) -> None:
        """프로젝트 config 전체 교체."""
        self.update_project(project_id, config=config)

    def update_config(self, project_id: str, **kwargs) -> None:
        """프로젝트 config에 키-값 머지."""
        current = self.get_config(project_id)
        current.update(kwargs)
        self.set_config(project_id, current)

    def delete_config_key(self, project_id: str, key: str) -> None:
        """프로젝트 config에서 키 삭제."""
        current = self.get_config(project_id)
        current.pop(key, None)
        self.set_config(project_id, current)

    def provision_art_style(self, project_id: str) -> Optional[str]:
        """아트스타일 JSON을 Storage에 업로드. Storage URL 반환."""
        config = self.get_config(project_id)
        art_style_rel = config.get("art_style")
        if not art_style_rel:
            return None
        from auto_agent.paths import get_data_dir
        src = get_data_dir() / art_style_rel
        if not src.exists():
            return None
        # JSON을 Storage에 업로드
        url = self.upload_local_file(project_id, "art_style.json", str(src))
        # 참조 이미지도 업로드
        ref_dir = src.parent
        for img in ref_dir.glob("*.jpg"):
            self.upload_local_file(project_id, f"artstyle/{img.name}", str(img))
        for img in ref_dir.glob("*.png"):
            self.upload_local_file(project_id, f"artstyle/{img.name}", str(img))
        return url

    # ──────────────────────────────────────
    # 파이프라인 실행 이력
    # ──────────────────────────────────────

    def get_pipeline_history(self, project_id: str) -> List[dict]:
        resp = (
            self.sb.table("pipeline_runs")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data

    def start_pipeline_run(self, project_id: str, phase: str, step: str,
                           step_name: str = None, agent_or_module: str = None,
                           metadata: dict = None) -> str:
        row = {
            "project_id": project_id,
            "phase": phase,
            "step": step,
            "step_name": step_name,
            "agent_or_module": agent_or_module,
            "status": "running",
            "metadata": metadata,
        }
        resp = self.sb.table("pipeline_runs").insert(row).execute()
        return resp.data[0]["id"]

    def complete_pipeline_run(self, run_id: str, cost_tokens_in: int = 0,
                              cost_tokens_out: int = 0, cost_usd: float = 0.0) -> None:
        self.sb.table("pipeline_runs").update({
            "status": "completed",
            "cost_tokens_in": cost_tokens_in,
            "cost_tokens_out": cost_tokens_out,
            "cost_usd": cost_usd,
        }).eq("id", run_id).execute()

    def fail_pipeline_run(self, run_id: str, error_log: str) -> None:
        self.sb.table("pipeline_runs").update({
            "status": "failed",
            "error_log": error_log[:5000],
        }).eq("id", run_id).execute()

    # ──────────────────────────────────────
    # 비용 분석
    # ──────────────────────────────────────

    def get_cost_summary(self, project_id: str = None) -> dict:
        query = self.sb.table("pipeline_runs").select(
            "cost_tokens_in, cost_tokens_out, cost_usd, duration_sec, status"
        )
        if project_id:
            query = query.eq("project_id", project_id)
        resp = query.execute()

        total_in = sum(r.get("cost_tokens_in") or 0 for r in resp.data)
        total_out = sum(r.get("cost_tokens_out") or 0 for r in resp.data)
        total_usd = sum(r.get("cost_usd") or 0.0 for r in resp.data)
        total_dur = sum(r.get("duration_sec") or 0.0 for r in resp.data)

        return {
            "total_runs": len(resp.data),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_usd": round(total_usd, 4),
            "total_duration_sec": round(total_dur, 1),
        }

    def get_cost_by_agent(self, project_id: str) -> List[dict]:
        resp = (
            self.sb.table("pipeline_runs")
            .select("agent_or_module, cost_tokens_in, cost_tokens_out, cost_usd")
            .eq("project_id", project_id)
            .execute()
        )
        agents: dict = {}
        for r in resp.data:
            agent = r.get("agent_or_module") or "unknown"
            if agent not in agents:
                agents[agent] = {"agent_or_module": agent, "run_count": 0,
                                 "tokens_in": 0, "tokens_out": 0, "total_usd": 0.0}
            a = agents[agent]
            a["run_count"] += 1
            a["tokens_in"] += r.get("cost_tokens_in") or 0
            a["tokens_out"] += r.get("cost_tokens_out") or 0
            a["total_usd"] += r.get("cost_usd") or 0.0

        result = sorted(agents.values(), key=lambda x: x["total_usd"], reverse=True)
        for r in result:
            r["total_usd"] = round(r["total_usd"], 4)
        return result

    # ──────────────────────────────────────
    # 에셋 관리
    # ──────────────────────────────────────

    def get_assets(self, project_id: str, asset_type: str = None,
                   scene_number: int = None) -> List[dict]:
        query = (
            self.sb.table("assets")
            .select("*")
            .eq("project_id", project_id)
            .order("scene_number")
        )
        if asset_type:
            query = query.eq("asset_type", asset_type)
        if scene_number is not None:
            query = query.eq("scene_number", scene_number)
        resp = query.execute()
        return resp.data

    def get_asset_counts(self, project_id: str) -> dict:
        resp = (
            self.sb.table("assets")
            .select("asset_type")
            .eq("project_id", project_id)
            .execute()
        )
        counts: dict = {}
        for r in resp.data:
            t = r["asset_type"]
            counts[t] = counts.get(t, 0) + 1
        return counts

    # ──────────────────────────────────────
    # 버전 관리
    # ──────────────────────────────────────

    def get_versions(self, project_id: str, file_type: str) -> List[dict]:
        resp = (
            self.sb.table("file_versions")
            .select("*")
            .eq("project_id", project_id)
            .eq("file_type", file_type)
            .order("version", desc=True)
            .execute()
        )
        return resp.data

    # ──────────────────────────────────────
    # Storage 파일 읽기
    # ──────────────────────────────────────

    def load_project_json(self, project_id: str, filename: str) -> Optional[dict]:
        """Supabase Storage에서 프로젝트 JSON 파일 로드."""
        storage_key = self._get_storage_key(project_id)
        if not storage_key:
            return None
        storage_path = f"{storage_key}/{filename}"
        try:
            data = self.sb.storage.from_(BUCKET_NAME).download(storage_path)
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def load_project_text(self, project_id: str, filename: str) -> Optional[str]:
        """Supabase Storage에서 프로젝트 텍스트 파일 로드."""
        storage_key = self._get_storage_key(project_id)
        if not storage_key:
            return None
        storage_path = f"{storage_key}/{filename}"
        try:
            data = self.sb.storage.from_(BUCKET_NAME).download(storage_path)
            return data.decode("utf-8")
        except Exception:
            return None

    def get_file_public_url(self, project_id: str, relative_path: str) -> Optional[str]:
        """Storage 파일의 public URL 반환."""
        storage_key = self._get_storage_key(project_id)
        if not storage_key:
            return None
        storage_path = f"{storage_key}/{relative_path}"
        return self.sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    def save_project_json(self, project_id: str, filename: str, data: dict) -> str:
        """Supabase Storage에 JSON 파일 저장. public URL 반환."""
        storage_key = self._get_storage_key(project_id)
        if not storage_key:
            raise ValueError("프로젝트 storage_key를 찾을 수 없습니다.")
        storage_path = f"{storage_key}/{filename}"
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.sb.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": "application/json", "upsert": "true"},
        )
        return self.sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    # ──────────────────────────────────────
    # 이미지/오디오 URL (assets 테이블 기반)
    # ──────────────────────────────────────

    def get_scene_image_url(self, project_id: str, scene_number: int) -> Optional[str]:
        """씬 이미지의 Supabase Storage public URL."""
        resp = (
            self.sb.table("assets")
            .select("storage_url")
            .eq("project_id", project_id)
            .eq("asset_type", "image")
            .eq("scene_number", scene_number)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0].get("storage_url")
        return None

    def get_scene_image_candidates(self, project_id: str, scene_number: int) -> list:
        """씬의 모든 이미지 후보 (검색+생성) 반환."""
        resp = (
            self.sb.table("assets")
            .select("id, storage_url, file_path, file_name, metadata, created_at")
            .eq("project_id", project_id)
            .eq("scene_number", scene_number)
            .in_("asset_type", ["image", "viz_bg"])
            .order("created_at")
            .execute()
        )
        candidates = []
        for row in resp.data:
            fp = row.get("file_path", "")
            # 타입 추론: search/, generated/, viz_bg/ 등
            if "/search/" in fp:
                img_type = "search"
            elif "/generated/" in fp:
                img_type = "generated"
            elif "/viz_bg/" in fp:
                img_type = "viz_bg"
            else:
                img_type = "final"
            candidates.append({
                "id": row["id"],
                "url": row["storage_url"],
                "file_name": row.get("file_name", ""),
                "type": img_type,
                "metadata": row.get("metadata") or {},
            })
        return candidates

    def get_scene_audio_url(self, project_id: str, scene_number: int) -> Optional[str]:
        """씬 오디오의 Supabase Storage public URL."""
        resp = (
            self.sb.table("assets")
            .select("storage_url")
            .eq("project_id", project_id)
            .eq("asset_type", "audio")
            .eq("scene_number", scene_number)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0].get("storage_url")
        return None

    # ──────────────────────────────────────
    # Storage 파일 업로드
    # ──────────────────────────────────────

    def upload_file(self, project_id: str, relative_path: str,
                    content: bytes, content_type: str = None) -> str:
        """파일을 Supabase Storage에 업로드. public URL 반환."""
        storage_key = self._get_storage_key(project_id)
        if not storage_key:
            raise ValueError("프로젝트 storage_key를 찾을 수 없습니다.")
        storage_path = f"{storage_key}/{relative_path}"
        if not content_type:
            content_type = mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        self.sb.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return self.sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)

    def upload_local_file(self, project_id: str, relative_path: str,
                          local_path: str) -> str:
        """로컬 파일을 Supabase Storage에 업로드. public URL 반환."""
        with open(local_path, "rb") as f:
            content = f.read()
        return self.upload_file(project_id, relative_path, content)

    def save_project_text(self, project_id: str, filename: str, text: str) -> str:
        """텍스트 파일을 Storage에 저장. public URL 반환."""
        content = text.encode("utf-8")
        content_type = "text/markdown" if filename.endswith(".md") else "text/plain"
        return self.upload_file(project_id, filename, content, content_type)

    def register_asset(self, project_id: str, asset_type: str,
                       scene_number: int = None, file_path: str = "",
                       file_name: str = "", storage_url: str = "",
                       metadata: dict = None) -> str:
        """에셋을 assets 테이블에 등록. 에셋 ID 반환."""
        row = {
            "project_id": project_id,
            "asset_type": asset_type,
            "scene_number": scene_number,
            "file_path": file_path,
            "file_name": file_name or Path(file_path).name if file_path else "",
            "storage_url": storage_url,
            "metadata": metadata or {},
        }
        resp = self.sb.table("assets").upsert(
            row, on_conflict="project_id,asset_type,scene_number,file_path"
        ).execute()
        return resp.data[0]["id"] if resp.data else ""

    def save_version(self, project_id: str, file_type: str,
                     version: int = None, storage_url: str = "",
                     metadata: dict = None) -> None:
        """파일 버전 기록."""
        if version is None:
            # 다음 버전 자동 계산
            existing = self.get_versions(project_id, file_type)
            version = (existing[0].get("version", 0) + 1) if existing else 1
        row = {
            "project_id": project_id,
            "file_type": file_type,
            "version": version,
            "storage_url": storage_url,
            "metadata": metadata or {},
        }
        self.sb.table("file_versions").insert(row).execute()

    # ──────────────────────────────────────
    # 라이선스
    # ──────────────────────────────────────

    def get_licenses(self, project_id: str) -> List[dict]:
        resp = (
            self.sb.table("asset_licenses")
            .select("*, assets!inner(file_path, scene_number)")
            .eq("assets.project_id", project_id)
            .execute()
        )
        result = []
        for r in resp.data:
            asset_info = r.pop("assets", {})
            r["file_path"] = asset_info.get("file_path")
            r["scene_number"] = asset_info.get("scene_number")
            result.append(r)
        return result

    # ──────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────

    def _get_storage_key(self, project_id: str) -> Optional[str]:
        """project_id → storage_key 조회 (캐시)."""
        if not hasattr(self, "_storage_key_cache"):
            self._storage_key_cache = {}
        if project_id in self._storage_key_cache:
            return self._storage_key_cache[project_id]

        resp = (
            self.sb.table("projects")
            .select("storage_key")
            .eq("id", project_id)
            .execute()
        )
        if resp.data:
            key = resp.data[0].get("storage_key")
            self._storage_key_cache[project_id] = key
            return key
        return None

    def _normalize_project(self, row: dict) -> dict:
        """Supabase 프로젝트 row를 기존 ProjectManager 형식으로 변환."""
        return {
            "id": row.get("id"),  # UUID
            "local_id": row.get("local_id"),
            "name": row.get("name"),
            "slug": row.get("slug"),
            "topic": row.get("topic"),
            "theme": row.get("theme", "simple"),
            "config": row.get("config") or {},
            "output_dir": row.get("output_dir") or "",
            "storage_key": row.get("storage_key"),
            "status": row.get("status", "created"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "scene_count": row.get("scene_count", 0),
            "total_duration_sec": row.get("total_duration_sec", 0.0),
        }
