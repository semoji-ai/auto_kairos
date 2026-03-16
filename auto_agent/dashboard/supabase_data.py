"""
Supabase 기반 프로젝트 데이터 액세스 레이어.

기존 ProjectManager(SQLite)와 동일한 인터페이스를 제공하여
대시보드가 Supabase를 단일 진실 소스(SSOT)로 사용할 수 있게 한다.

사용법:
    from auto_agent.dashboard.supabase_data import SupabaseProjectManager
    pm = SupabaseProjectManager()
    projects = pm.list_projects()
"""
from __future__ import annotations

import json
import mimetypes
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
