"""리서치 오케스트레이션 — 브리프→쿼리→레인(P1)+웹 fan-out→종합 research_report.
run_research가 지휘, 나머지는 유틸·종합 헬퍼. 런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
from pathlib import Path

_SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
_REPORT_SCHEMA = _SCHEMAS / "research_report.schema.json"


def _explorer_count(duration: str) -> int:
    """분량(예 '1분','10분')에 따른 웹리서치 에이전트 수. v3 스케일."""
    m = re.search(r"(\d+)", str(duration or ""))
    mins = int(m.group(1)) if m else 0
    if mins <= 1:
        return 3
    if mins <= 3:
        return 4
    if mins <= 5:
        return 5
    return 6


def _digest(sources: list, web_notes: list) -> dict:
    """결정적 통계(LLM 무관). 소스/노트 카운트 + lane/tier 분포."""
    lanes: dict[str, int] = {}
    tiers: dict[str, int] = {}
    for s in sources:
        lanes[s.get("lane", "")] = lanes.get(s.get("lane", ""), 0) + 1
        tiers[s.get("tier_hint", "")] = tiers.get(s.get("tier_hint", ""), 0) + 1
    return {
        "source_count": len(sources),
        "web_note_count": len([n for n in web_notes if n]),
        "lanes": lanes,
        "tiers": tiers,
    }


def _load_sources(proj_dir: Path) -> list[dict]:
    """research/manifests/**/sources.jsonl 의 모든 소스 dict 로드."""
    out: list[dict] = []
    base = Path(proj_dir) / "research" / "manifests"
    if not base.is_dir():
        return out
    for jsonl in base.rglob("sources.jsonl"):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


from concurrent.futures import ThreadPoolExecutor

from backend import llm
from backend import brief as brief_mod
from backend.research import query_planner, collector, web_agent


def _angles(brief: dict, queries: list, n: int) -> list[str]:
    """n개 웹리서치 앵글 프롬프트 생성. 쿼리를 라운드로빈으로 분배 + 브리프 맥락."""
    topic = brief.get("real_topic") or brief.get("core_question") or ""
    qs = [q["query"] for q in queries] or [topic]
    out = []
    for i in range(n):
        focus = qs[i % len(qs)]
        out.append(
            f"너는 리서치 탐색가다. 주제 '{topic}' 중 '{focus}'에 집중해 웹을 검색·열람해 "
            f"검증 가능한 사실(수치·연도·사건)과 출처 URL을 수집하라. "
            f"WebSearch/WebFetch를 사용하고, 핵심 발견을 불릿으로 정리해 출처 URL과 함께 보고하라.")
    return out


def _synthesize(proj_dir, brief: dict, sources: list, web_notes: list, on_event=None) -> dict | None:
    """레인 소스 + 웹 노트 → research_report.json (claude+스키마). 실패 시 None."""
    proj_dir = Path(proj_dir)
    out = proj_dir / "research_report.json"
    notes_text = "\n\n---\n".join(n for n in web_notes if n)
    src_text = json.dumps(sources, ensure_ascii=False, indent=2)[:8000]
    prompt = (
        "다음 브리프·수집 소스·웹 노트를 종합해 research_report JSON을 작성하라.\n"
        "필드: topic, queries(검색어 배열), sources(입력 소스 배열 그대로), "
        "web_findings([{angle, claim, source_url}]), digest({key_facts:[...], figures:[...]}).\n"
        "검증 가능한 사실 위주, 출처 URL 보존. JSON만 출력.\n\n"
        f"## 브리프\n{json.dumps(brief, ensure_ascii=False)[:3000]}\n\n"
        f"## 수집 소스(레인)\n{src_text}\n\n## 웹 노트\n{notes_text[:8000]}"
    )
    if on_event:
        on_event("리서치 종합")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REPORT_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return None
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_research(proj_dir, *, max_workers: int = 3, on_event=None) -> dict:
    """브리프→쿼리→레인(P1)+웹 fan-out→종합 research_report.
    반환 {report, queries, sources, web_notes} 또는 {error}."""
    proj_dir = Path(proj_dir)
    bf = proj_dir / "editorial_brief.json"
    if not bf.is_file():
        return {"error": "editorial_brief.json 필요 (P2 먼저)"}
    brief = json.loads(bf.read_text(encoding="utf-8"))
    duration = brief_mod.parse_plan(proj_dir).get("duration", "")

    queries = query_planner.plan_queries(brief, project_slug=proj_dir.name)
    if not queries:
        return {"error": "쿼리 생성 실패"}
    if on_event:
        on_event(f"쿼리 {len(queries)}개")
    collector.collect_queries(proj_dir, [q["query"] for q in queries], on_event=on_event)

    n = _explorer_count(duration)
    angles = _angles(brief, queries, n)
    web_dir = proj_dir / "research" / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    def _one(i_angle):
        i, angle = i_angle
        note = web_agent.run_web_research(proj_dir, angle, on_line=on_event)
        if note:
            (web_dir / f"{i}.md").write_text(note, encoding="utf-8")
        return note

    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as ex:
        web_notes = list(ex.map(_one, list(enumerate(angles))))

    sources = _load_sources(proj_dir)
    report = _synthesize(proj_dir, brief, sources, web_notes, on_event=on_event)
    digest = _digest(sources, web_notes)
    (proj_dir / "research_digest.json").write_text(
        json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    if report is None:                       # 종합 실패 → digest-only 폴백 리포트
        report = {"topic": brief.get("real_topic") or brief.get("core_question") or "",
                  "queries": [q["query"] for q in queries],
                  "sources": sources, "web_findings": [], "digest": digest}
        if on_event:
            on_event("종합 실패 — digest 기반 최소 리포트")
    (proj_dir / "research_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"report": str(proj_dir / "research_report.json"),
            "queries": len(queries), "sources": len(sources),
            "web_notes": len([n for n in web_notes if n])}
