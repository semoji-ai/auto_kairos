"""Vault lookup — NAS 02-research wiki에서 매칭 토픽 흡수.

NAS 단절 / slug 매칭 실패 시에도 파이프라인은 계속 진행 (read-only 흡수).

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 2)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional


# ─────────────────────────────────────────────
# 볼트 경로 / 헬스체크
# ─────────────────────────────────────────────

DEFAULT_VAULT_PATH = "/Volumes/kairos/kairos_vault/kairos-vault/02-research"
HEALTH_CHECK_TIMEOUT = 5


def get_vault_root() -> Optional[Path]:
    """KAIROS_VAULT_DIR env 또는 기본 NAS 경로. 미존재 시 None."""
    env = os.environ.get("KAIROS_VAULT_DIR", "").strip()
    if env:
        path = Path(env) / "02-research" if not env.endswith("02-research") else Path(env)
    else:
        path = Path(DEFAULT_VAULT_PATH)
    return path if path.exists() else None


def vault_health_check(timeout: int = HEALTH_CHECK_TIMEOUT) -> tuple[bool, str]:
    """NAS 마운트 살아있는지 확인. (ok, reason)."""
    root = get_vault_root()
    if root is None:
        return False, "vault path 미존재 (NAS 미마운트?)"
    wiki_dir = root / "wiki"
    if not wiki_dir.exists():
        return False, f"wiki/ 디렉토리 없음: {wiki_dir}"
    # 가벼운 read 시도 (NAS 멈춰있는지 검증)
    try:
        list(wiki_dir.iterdir())
    except Exception as exc:
        return False, f"wiki/ read 실패: {exc}"
    return True, "ok"


def list_vault_topics() -> list[str]:
    """볼트의 모든 토픽 슬러그 목록."""
    root = get_vault_root()
    if root is None:
        return []
    wiki_dir = root / "wiki"
    if not wiki_dir.exists():
        return []
    try:
        return sorted([d.name for d in wiki_dir.iterdir() if d.is_dir()])
    except Exception:
        return []


# ─────────────────────────────────────────────
# Slug matcher (LLM-driven)
# ─────────────────────────────────────────────

MATCHER_PROMPT = """당신은 리서치 토픽 매처입니다. 새 영상 프로젝트의 검색 쿼리들이
볼트(과거 리서치 저장소)의 어떤 기존 토픽과 매칭되는지 판정하세요.

입력:
- 새 프로젝트 검색 쿼리들 (entity 후보)
- 볼트 토픽 슬러그 목록

출력 규칙:
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"matches": [{"vault_slug": "...", "confidence": 0.0~1.0, "rationale": "..."}]}
- confidence ≥ 0.7만 반환. 낮으면 빼세요.
- 같은 벌트 슬러그를 두 번 매칭하지 않습니다.
- entity 명시적 일치 우선 (예: "유한양행" 쿼리 ↔ "유한양행" 슬러그 = 0.95).
- 의미적 일치는 0.7~0.85 범위 (예: "한국 제약산업" ↔ "lg_반도체" = 매칭 안 함).
"""


def _build_matcher_prompt(queries: list[str], vault_slugs: list[str]) -> str:
    """LLM 매처에 전달할 프롬프트."""
    body = {
        "queries": queries,
        "vault_topics": vault_slugs,
    }
    return f"{MATCHER_PROMPT}\n\n<input>\n{json.dumps(body, ensure_ascii=False, indent=2)}\n</input>\n"


def _parse_matcher_response(raw: str) -> list[dict]:
    raw = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("응답에 JSON 블록 없음")
    payload = json.loads(m.group(0))
    matches = payload.get("matches") if isinstance(payload, dict) else None
    if not isinstance(matches, list):
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("vault_slug") or "").strip()
        if not slug or slug in seen:
            continue
        try:
            conf = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            continue
        if conf < 0.7:
            continue
        seen.add(slug)
        out.append({
            "vault_slug": slug,
            "confidence": round(conf, 2),
            "rationale": str(item.get("rationale") or ""),
        })
    return out


def _call_claude_cli(prompt: str, *, timeout: int = 60) -> str:
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    result = subprocess.run(
        [claude_bin, "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    return result.stdout


def match_vault_topics(
    queries: list[str],
    vault_slugs: list[str] | None = None,
    *,
    invoker: Callable[[str], str] | None = None,
) -> list[dict]:
    """LLM이 queries ↔ vault_slugs 매칭. confidence ≥ 0.7만 반환.

    invoker: 테스트용 mock. 미지정 시 Claude CLI subprocess.
    슬러그 목록 비어있으면 즉시 빈 리스트.
    """
    slugs = vault_slugs if vault_slugs is not None else list_vault_topics()
    if not queries or not slugs:
        return []
    invoke = invoker or _call_claude_cli
    prompt = _build_matcher_prompt(queries, slugs)
    try:
        raw = invoke(prompt)
        return _parse_matcher_response(raw)
    except Exception as exc:
        print(f"[vault_lookup] matcher 실패: {exc}", flush=True)
        return []


# ─────────────────────────────────────────────
# 흡수 (read-only copy)
# ─────────────────────────────────────────────

WIKI_PAGES = ("overview.md", "claims.md", "entities.md", "timeline.md", "images.md", "log.md")


def absorb_topic(
    vault_slug: str,
    project_research_dir: Path,
    *,
    target_slug: Optional[str] = None,
) -> dict:
    """볼트 wiki/<vault_slug>/ → 프로젝트 wiki/<target_slug>/. read-only copy.

    target_slug 미지정 시 vault_slug 그대로 사용.
    이미 있는 페이지는 덮어쓰지 않고 .vault.md 접미사로 저장 (충돌 안전).
    """
    root = get_vault_root()
    if root is None:
        return {"absorbed": False, "reason": "vault unavailable"}
    src = root / "wiki" / vault_slug
    if not src.exists():
        return {"absorbed": False, "reason": f"vault topic 없음: {vault_slug}"}

    target = target_slug or vault_slug
    dst = Path(project_research_dir) / "wiki" / target
    dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for page in WIKI_PAGES:
        src_file = src / page
        if not src_file.exists():
            continue
        dst_file = dst / page
        if dst_file.exists():
            # 충돌 안전 — 별도 이름으로 보관
            dst_file = dst / f"{page.rsplit('.', 1)[0]}.vault.md"
        shutil.copy2(src_file, dst_file)
        copied.append(dst_file.name)

    # manifests/<topic>/claims.jsonl + sources.jsonl도 흡수
    for manifest_file in ("claims.jsonl", "sources.jsonl"):
        src_m = root / "manifests" / vault_slug / manifest_file
        if not src_m.exists():
            continue
        dst_m_dir = Path(project_research_dir) / "manifests" / target
        dst_m_dir.mkdir(parents=True, exist_ok=True)
        dst_m = dst_m_dir / manifest_file
        if dst_m.exists():
            # append (jsonl이라 안전)
            with open(src_m, "r", encoding="utf-8") as fr, open(dst_m, "a", encoding="utf-8") as fw:
                fw.write(fr.read())
        else:
            shutil.copy2(src_m, dst_m)
        copied.append(manifest_file)

    return {
        "absorbed": True,
        "vault_slug": vault_slug,
        "target_slug": target,
        "files": copied,
    }
