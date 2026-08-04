"""Wiki Compiler — raw + manifests → 프로젝트 wiki/<topic>/{overview,claims,entities,timeline,index}.md.

claims.md / index.md는 jsonl을 그대로 markdown 렌더 (LLM 불필요, 결정적).
overview / entities / timeline은 LLM(sonnet)이 raw 합성.

흡수된 vault wiki(*.vault.md)는 Phase 2에서 이미 보존됨 — 별도 머지 안 함.
필요 시 fact-retriever나 사람이 양쪽 다 참조 가능.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 3)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


# ─────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _frontmatter(topic_slug: str, page_type: str) -> str:
    return (
        f"---\n"
        f'doc_type: "wiki-page"\n'
        f"topic_slug: {json.dumps(topic_slug, ensure_ascii=False)}\n"
        f"page_type: {page_type}\n"
        f'updated_at: "{_now_iso()}"\n'
        f"tags:\n"
        f'  - "wiki"\n'
        f"---\n\n"
    )


# ─────────────────────────────────────────────
# claims.md / index.md — 결정적 렌더 (LLM 안 씀)
# ─────────────────────────────────────────────

def render_claims_md(claims: list[dict], topic_slug: str) -> str:
    """claims.jsonl → markdown (옵시디언 볼트 형식 호환)."""
    out = _frontmatter(topic_slug, "claims")
    out += f"# {topic_slug} — Claims\n\n"
    if not claims:
        out += "## Claim Ledger\n- 아직 기록된 claim이 없습니다.\n"
        return out
    out += f"## Claim Ledger ({len(claims)}건)\n\n"
    for c in claims:
        cid = str(c.get("claim_id") or c.get("id") or "")
        out += f"## {cid or 'claim_unknown'}\n\n"
        out += f"- claim: {c.get('claim', '')}\n"
        if c.get("kind"):
            out += f"- kind: `{c['kind']}`\n"
        if c.get("tier"):
            out += f"- tier: `{c['tier']}`\n"
        if c.get("confidence"):
            out += f"- confidence: `{c['confidence']}`\n"
        if c.get("status"):
            out += f"- status: `{c['status']}`\n"
        sids = c.get("source_ids") or []
        if isinstance(sids, list) and sids:
            out += f"- source_ids: `{', '.join(str(s) for s in sids)}`\n"
        if c.get("evidence"):
            out += f"- evidence: {c['evidence']}\n"
        if c.get("created_at"):
            out += f"- created_at: `{c['created_at']}`\n"
        out += "\n"
    return out


def render_index_md(sources: list[dict], topic_slug: str) -> str:
    """sources.jsonl → markdown 인덱스 (제목/URL/tier 한눈에)."""
    out = _frontmatter(topic_slug, "index")
    out += f"# {topic_slug} — Source Index\n\n"
    if not sources:
        out += "수집된 소스가 없습니다.\n"
        return out
    # tier 별 그룹핑
    by_tier: dict[str, list[dict]] = {}
    for s in sources:
        t = str(s.get("tier_hint") or "unknown")
        by_tier.setdefault(t, []).append(s)
    out += f"총 {len(sources)}개 — "
    out += " / ".join(f"{t}: {len(v)}" for t, v in sorted(by_tier.items())) + "\n\n"
    for tier in ("A", "B", "unknown", "C"):
        items = by_tier.get(tier, [])
        if not items:
            continue
        out += f"## Tier {tier} ({len(items)}건)\n\n"
        for s in items:
            sid = s.get("source_id", "")
            title = s.get("title", "")
            url = s.get("url", "")
            lane = s.get("lane", "")
            pub = s.get("publisher", "")
            out += f"- **{title}** "
            if pub:
                out += f"_{pub}_ "
            out += f"[`{lane}`]"
            if url:
                out += f" → [{url}]({url})"
            out += f"\n  - id: `{sid}`\n"
        out += "\n"
    return out


# ─────────────────────────────────────────────
# overview / entities / timeline — LLM 합성
# ─────────────────────────────────────────────

SYNTHESIS_PROMPT = """당신은 옵시디언 위키 컴파일러입니다. 아래 raw 자료를 읽고
**3개 페이지**(overview / entities / timeline)를 한 번에 작성하세요.

# 출력 규칙
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"overview": "...", "entities": "...", "timeline": "..."}
- 각 페이지는 markdown 본문 (frontmatter 제외). 1500~4000자 권장.
- 한국어 자료가 우세하면 한국어, 영어 우세하면 영어로.

# 페이지별 가이드

## overview
- 토픽의 종합 요약. 시청자/작가가 한눈에 맥락 파악 가능해야.
- 핵심 인물/연도/사건 포함, 강한 hook 표현.
- 마지막 섹션 "다운스트림 작성 에이전트에게"로 hook/주의/그림 자료 안내.

## entities
- 인물 (이름·생몰·역할·업적·일화·관련 claim_id)
- 회사/브랜드 (설립·주력·소유 변천)
- 제품/사건 (이름·연도·의의)
- 모든 entity에 ### 헤더로 구분.

## timeline
- 연도별 또는 시기별 chronological 표기
- 각 항목: **연도** — 사건/제품/인물 변화

# 절대 금지
- 출처 없는 추측 (raw에 없는 사실 만들지 말 것)
- 마크다운 표 안에 줄바꿈 (JSON 파싱 깨짐)
- frontmatter 작성 (시스템이 추가)
"""


def _build_synthesis_prompt(topic_slug: str, sources: list[dict], claims: list[dict], raw_excerpts: list[str]) -> str:
    body = {
        "topic_slug": topic_slug,
        "sources": [{"id": s.get("source_id"), "title": s.get("title"), "tier": s.get("tier_hint"), "lane": s.get("lane")} for s in sources[:30]],
        "claim_count": len(claims),
        "sample_claims": [c.get("claim") for c in claims[:20] if c.get("claim")],
        "raw_excerpts": raw_excerpts[:30],
    }
    return f"{SYNTHESIS_PROMPT}\n\n<input>\n{json.dumps(body, ensure_ascii=False, indent=2)}\n</input>\n"


def _parse_synthesis_response(raw: str) -> dict:
    raw = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("응답에 JSON 블록 없음")
    payload = json.loads(m.group(0))
    if not isinstance(payload, dict):
        raise ValueError("응답이 dict가 아님")
    out = {}
    for key in ("overview", "entities", "timeline"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    if not out:
        raise ValueError("3개 페이지 모두 비어있음")
    return out


# 마지막 합성 호출의 메타 (프로바이더/비용). compile_topic이 결과에 실어 보낸다.
_LAST_CALL_META: dict = {}


def _call_claude_cli(prompt: str, *, timeout: int = 240) -> str:
    """claude CLI 폴백. --model을 반드시 명시한다.

    ⚠️ --model을 빼면 사용자 기본 모델(opus/fable)을 상속해 비용이 폭증한다.
    위키 합성은 원문에서 사실을 추리는 기계적 작업이므로 sonnet으로 충분하다.
    (docs/token-waste-audit.md 5번 항목)
    """
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    model = os.environ.get("WIKI_COMPILE_CLAUDE_MODEL", "sonnet")
    result = subprocess.run(
        [claude_bin, "-p", "--model", model, "--output-format", "json"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    try:
        payload = json.loads(result.stdout)
        _LAST_CALL_META.update(
            provider=f"claude:{model}",
            cost_usd=float(payload.get("total_cost_usd") or 0),
        )
        return payload.get("result", "")
    except (json.JSONDecodeError, ValueError):
        _LAST_CALL_META.update(provider=f"claude:{model}", cost_usd=None)
        return result.stdout


def _call_codex(prompt: str, *, timeout: int = 600) -> str:
    """codex exec로 위키 합성. Claude 리밋을 소모하지 않는다.

    프로젝트 구조상 리서치는 codex, 집필은 Claude가 담당한다. 위키 합성은
    수집 자료를 정리하는 리서치 작업이므로 codex가 맞다.
    """
    from auto_agent.utils.codex_cli import build_codex_exec_cmd

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "last_message.txt"
        cmd = build_codex_exec_cmd(
            workdir=Path(tmpdir),
            output_last_message=str(out_path),
            reasoning_effort="low",  # 기계적 정리 — 추론 비용 낮게
            search=False,            # 이미 수집된 raw만 사용
        )
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"codex exit {result.returncode}: {(result.stderr or '')[:200]}")
        text = out_path.read_text(encoding="utf-8") if out_path.exists() else result.stdout
    _LAST_CALL_META.update(provider="codex", cost_usd=None)  # codex는 Claude 리밋 밖
    return text


def _default_invoker(prompt: str) -> str:
    """기본 합성 호출자 — codex 우선, 실패 시 claude(sonnet) 폴백."""
    if os.environ.get("WIKI_COMPILE_PROVIDER", "codex").strip() == "claude":
        return _call_claude_cli(prompt)
    try:
        return _call_codex(prompt)
    except Exception as exc:  # codex 미설치/실패 → claude 폴백
        print(f"    [wiki_compile] codex 실패 → claude(sonnet) 폴백: {exc}", flush=True)
        return _call_claude_cli(prompt)


def _wiki_is_fresh(wiki_dir: Path, manifest_dir: Path) -> bool:
    """합성 페이지가 이미 있고 manifest보다 새로우면 True (재합성 불필요).

    없으면 매 실행마다 전 토픽을 재합성해 편당 수십 분·수십만 토큰이 낭비된다.
    """
    pages = [wiki_dir / f"{p}.md" for p in ("overview", "entities", "timeline")]
    if not all(p.exists() and p.stat().st_size > 0 for p in pages):
        return False
    newest_wiki = max(p.stat().st_mtime for p in pages)
    manifest_files = list(manifest_dir.glob("*.jsonl")) if manifest_dir.exists() else []
    if not manifest_files:
        return True
    return newest_wiki >= max(f.stat().st_mtime for f in manifest_files)


def _read_raw_excerpts(raw_dir: Path, limit: int = 30, max_chars_per: int = 3000) -> list[str]:
    """raw/<topic>/<run>/source_notes/*.md 본문 일부 추출."""
    if not raw_dir.exists():
        return []
    excerpts: list[str] = []
    for run_dir in sorted(raw_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        notes_dir = run_dir / "source_notes"
        if not notes_dir.exists():
            continue
        for md_file in sorted(notes_dir.iterdir()):
            if len(excerpts) >= limit:
                break
            if md_file.suffix != ".md":
                continue
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            # frontmatter 제거 후 본문만
            body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
            excerpts.append(body[:max_chars_per].strip())
        if len(excerpts) >= limit:
            break
    return excerpts


def synthesize_wiki_pages(
    topic_slug: str,
    raw_dir: Path,
    sources: list[dict],
    claims: list[dict],
    *,
    invoker: Callable[[str], str] | None = None,
) -> dict:
    """LLM이 raw 자료에서 overview / entities / timeline 합성."""
    invoke = invoker or _default_invoker
    excerpts = _read_raw_excerpts(raw_dir)
    prompt = _build_synthesis_prompt(topic_slug, sources, claims, excerpts)
    raw_response = invoke(prompt)
    return _parse_synthesis_response(raw_response)


# ─────────────────────────────────────────────
# 메인 컴파일
# ─────────────────────────────────────────────

def compile_topic(
    topic_slug: str,
    project_research_dir: Path,
    *,
    invoker: Callable[[str], str] | None = None,
    skip_synthesis: bool = False,
    force: bool = False,
) -> dict:
    """하나의 토픽에 대해 wiki/<topic>/{overview,claims,entities,timeline,index}.md 생성.

    Args:
        topic_slug: 토픽 슬러그
        project_research_dir: output/<proj>/research/
        invoker: LLM 호출자 (테스트 mock용)
        skip_synthesis: True면 LLM 합성 건너뜀 (claims/index만 생성, 빠른 검증용)

    Returns:
        {written: [filepath, ...], skipped: [...], errors: [...]}
    """
    research_dir = Path(project_research_dir)
    sources = _read_jsonl(research_dir / "manifests" / topic_slug / "sources.jsonl")
    claims = _read_jsonl(research_dir / "manifests" / topic_slug / "claims.jsonl")
    raw_dir = research_dir / "raw" / topic_slug
    wiki_dir = research_dir / "wiki" / topic_slug
    wiki_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    skipped: list[str] = []
    errors: list[dict] = []

    # 1. claims.md (결정적, LLM 안 씀)
    claims_path = wiki_dir / "claims.md"
    claims_path.write_text(render_claims_md(claims, topic_slug), encoding="utf-8")
    written.append(str(claims_path.name))

    # 2. index.md (결정적)
    index_path = wiki_dir / "index.md"
    index_path.write_text(render_index_md(sources, topic_slug), encoding="utf-8")
    written.append(str(index_path.name))

    # 3. overview / entities / timeline (LLM 합성)
    if skip_synthesis:
        skipped.extend(["overview.md", "entities.md", "timeline.md"])
        return {"topic_slug": topic_slug, "written": written, "skipped": skipped, "errors": errors}

    if not sources and not claims:
        skipped.extend(["overview.md", "entities.md", "timeline.md"])
        errors.append({"reason": "sources + claims 둘 다 비어있어 synthesis 건너뜀"})
        return {"topic_slug": topic_slug, "written": written, "skipped": skipped, "errors": errors}

    # 멱등성 — 이미 합성됐고 manifest가 갱신되지 않았으면 재합성하지 않는다.
    if not force and _wiki_is_fresh(wiki_dir, research_dir / "manifests" / topic_slug):
        skipped.extend(["overview.md", "entities.md", "timeline.md"])
        return {
            "topic_slug": topic_slug, "written": written, "skipped": skipped,
            "errors": errors, "reused": True,
        }

    _LAST_CALL_META.clear()
    try:
        pages = synthesize_wiki_pages(topic_slug, raw_dir, sources, claims, invoker=invoker)
    except Exception as exc:
        errors.append({"phase": "synthesis", "reason": str(exc)})
        skipped.extend(["overview.md", "entities.md", "timeline.md"])
        return {"topic_slug": topic_slug, "written": written, "skipped": skipped, "errors": errors}

    for page_type in ("overview", "entities", "timeline"):
        body = pages.get(page_type)
        if not body:
            skipped.append(f"{page_type}.md")
            continue
        target = wiki_dir / f"{page_type}.md"
        # 기존에 vault에서 흡수된 *.vault.md는 보존됨. 새 컴파일은 본 파일에 저장.
        target.write_text(_frontmatter(topic_slug, page_type) + body + "\n", encoding="utf-8")
        written.append(target.name)

    return {
        "topic_slug": topic_slug, "written": written, "skipped": skipped, "errors": errors,
        "reused": False,
        "provider": _LAST_CALL_META.get("provider"),
        "cost_usd": _LAST_CALL_META.get("cost_usd"),
    }
