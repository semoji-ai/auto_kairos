"""
중앙 규칙 관리자.

규칙 파일(프롬프트, 스킬, 파이프라인 설정)을 Supabase에 저장/조회하고
로컬 캐시(.rules_cache/)를 통해 오프라인 실행을 지원한다.

크로스플랫폼 안전 규칙:
- 모든 파일 I/O는 encoding="utf-8"
- rule_store key는 항상 / 구분자 (POSIX)
- content는 항상 LF 줄바꿈
- checksum은 UTF-8 바이트 기준 SHA-256
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Optional

from auto_agent.supabase_client import get_supabase, supabase_enabled

# 로컬 data/ 디렉토리 (fallback)
DATA_DIR = Path(__file__).parent / "data"

# 규칙 파일 → rule_type 매핑
RULE_MANIFEST = {
    # 파이프라인 설정
    "pipeline.json": "pipeline",
    "agents.json": "agent_config",
    # 에이전트 스킬
    "skills/agents/research-orchestrator/SKILL.md": "skill",
    "skills/agents/script-director/SKILL.md": "skill",
    "skills/agents/fact-verifier/SKILL.md": "skill",
    "skills/agents/assembly-director/SKILL.md": "skill",
    "skills/agents/character-planner/SKILL.md": "skill",
    "skills/agents/trend-analyst/SKILL.md": "skill",
    "skills/agents/performance-analyst/SKILL.md": "skill",
    "skills/agents/upload-info-generator/SKILL.md": "skill",
    "skills/agents/multiformat-director/SKILL.md": "skill",
    # 공유 스킬
    "skills/shared/writing-style.md": "skill",
    "skills/shared/writing-style-iromism.md": "skill",
    "skills/shared/writing-style-semoji.md": "skill",
    "skills/shared/motion-presets.md": "skill",
    "skills/shared/remotion-design-system.md": "skill",
    "skills/shared/korean-tts-rules.md": "skill",
    "skills/shared/image-generation.md": "skill",
    "skills/shared/image-prompt-rules.md": "skill",
    "skills/shared/research-format.md": "skill",
    "skills/shared/market-analysis.md": "skill",
    "skills/shared/channel-metrics.md": "skill",
}


def _checksum(content: str) -> str:
    """UTF-8 바이트 기준 SHA-256."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize(content: str) -> str:
    """CRLF → LF 통일."""
    return content.replace("\r\n", "\n")


class RuleManager:
    """중앙 규칙 저장소 관리자."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (DATA_DIR.parent / ".rules_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._enabled = supabase_enabled()

    # ── Fetch (중앙 → 로컬 캐시) ──

    def fetch_all(self) -> int:
        """중앙에서 전체 규칙 fetch → 로컬 캐시 저장. 변경된 파일 수 리턴."""
        # 로컬 기반 운영 — Supabase 동기화 비활성화
        return 0

        if not self._enabled:
            return 0

        sb = get_supabase()
        resp = sb.table("rule_store").select("key, content, checksum").execute()
        rows = resp.data or []

        changed = 0
        for row in rows:
            key = row["key"]
            content = row["content"]
            remote_checksum = row["checksum"]

            cache_path = self._cache_path(key)

            # 로컬 캐시와 checksum 비교
            if cache_path.exists():
                local_content = cache_path.read_text(encoding="utf-8")
                if _checksum(local_content) == remote_checksum:
                    continue

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(content, encoding="utf-8")
            changed += 1

        return changed

    # ── Load (캐시 → fallback 로컬) ──

    def load(self, key: str) -> str:
        """규칙 로드. 로컬 data/ 우선 → 캐시 fallback."""
        # 1순위: 로컬 data/ (수정 반영 보장)
        local_path = DATA_DIR / PurePosixPath(key)
        if local_path.exists():
            return local_path.read_text(encoding="utf-8")

        # 2순위: 캐시 (오프라인 fallback)
        cache_path = self._cache_path(key)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"규칙을 찾을 수 없습니다: {key}")

    def load_json(self, key: str) -> dict:
        """JSON 규칙 로드."""
        return json.loads(self.load(key))

    # ── Push (로컬 → 중앙) ──

    def push(self, key: str, content: str, updated_by: str = "system",
             description: str = "") -> dict:
        """규칙을 중앙에 push + 버전 기록."""
        if not self._enabled:
            raise RuntimeError("Supabase 미연결 — push 불가")

        content = _normalize(content)
        cs = _checksum(content)
        rule_type = RULE_MANIFEST.get(key, "skill")

        sb = get_supabase()

        # 기존 버전 조회
        existing = sb.table("rule_store").select("checksum").eq("key", key).execute()
        if existing.data:
            old_checksum = existing.data[0]["checksum"]
            if old_checksum == cs:
                return {"status": "unchanged", "key": key}

            # 이전 content를 버전 히스토리에 저장
            old_content_resp = sb.table("rule_store").select("content").eq("key", key).execute()
            if old_content_resp.data:
                ver_resp = (sb.table("rule_versions")
                            .select("version")
                            .eq("rule_key", key)
                            .order("version", desc=True)
                            .limit(1)
                            .execute())
                next_ver = (ver_resp.data[0]["version"] + 1) if ver_resp.data else 1

                sb.table("rule_versions").insert({
                    "rule_key": key,
                    "version": next_ver,
                    "content": old_content_resp.data[0]["content"],
                    "checksum": old_checksum,
                    "description": description or f"v{next_ver} before update",
                    "created_by": updated_by,
                }).execute()

        # upsert
        sb.table("rule_store").upsert({
            "key": key,
            "content": content,
            "rule_type": rule_type,
            "checksum": cs,
            "updated_by": updated_by,
        }, on_conflict="key").execute()

        # 로컬 캐시도 갱신
        cache_path = self._cache_path(key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")

        return {"status": "pushed", "key": key, "checksum": cs}

    def push_all(self, updated_by: str = "system") -> dict:
        """RULE_MANIFEST의 모든 로컬 파일을 중앙에 push."""
        results = {"pushed": 0, "unchanged": 0, "missing": 0}
        for key in RULE_MANIFEST:
            local_path = DATA_DIR / PurePosixPath(key)
            if not local_path.exists():
                results["missing"] += 1
                continue
            content = local_path.read_text(encoding="utf-8")
            r = self.push(key, content, updated_by=updated_by)
            if r["status"] == "pushed":
                results["pushed"] += 1
            else:
                results["unchanged"] += 1
        return results

    # ── Rollback ──

    def rollback(self, key: str, version: int) -> dict:
        """특정 버전으로 롤백."""
        if not self._enabled:
            raise RuntimeError("Supabase 미연결 — rollback 불가")

        sb = get_supabase()
        ver_resp = (sb.table("rule_versions")
                    .select("content, checksum")
                    .eq("rule_key", key)
                    .eq("version", version)
                    .execute())
        if not ver_resp.data:
            raise ValueError(f"버전 {version}을 찾을 수 없습니다: {key}")

        old = ver_resp.data[0]
        return self.push(key, old["content"],
                         updated_by="rollback",
                         description=f"rollback to v{version}")

    # ── List ──

    def list_versions(self, key: str) -> list:
        """버전 히스토리 조회."""
        if not self._enabled:
            return []
        sb = get_supabase()
        resp = (sb.table("rule_versions")
                .select("version, checksum, description, created_by, created_at")
                .eq("rule_key", key)
                .order("version", desc=True)
                .execute())
        return resp.data or []

    def push_artstyle(self, style_name: str, content: str,
                      updated_by: str = "system") -> dict:
        """아트스타일 프리셋을 중앙에 push."""
        key = f"artstyle/styles/{style_name}.json"
        return self.push(key, content, updated_by=updated_by)

    def list_artstyles(self) -> list:
        """중앙에 등록된 아트스타일 목록."""
        if not self._enabled:
            return []
        sb = get_supabase()
        resp = (sb.table("rule_store")
                .select("key, updated_at, updated_by")
                .eq("rule_type", "artstyle")
                .execute())
        return resp.data or []

    # ── Internal ──

    def _cache_path(self, key: str) -> Path:
        """key → 로컬 캐시 경로 변환."""
        return self.cache_dir / PurePosixPath(key)
