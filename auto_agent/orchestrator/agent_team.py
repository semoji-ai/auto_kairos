# -*- coding: utf-8 -*-
"""
멀티 에이전트 팀 오케스트레이터.

Director가 전체를 총괄하고, Researcher/Writer/Reviewer를
병렬 dispatch하여 목표 분량에 맞는 리서치 + 원고를 생성합니다.

사용법:
    from auto_agent.orchestrator.agent_team import AgentTeam
    team = AgentTeam(project_id, slug, target_length=10000)
    result = team.run()
"""
from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from .agent_loop import AgentConfig, AgentLoop, AgentResult
from .tools import ToolExecutor


@dataclass
class TeamResult:
    """팀 실행 결과."""
    status: str  # "completed", "failed"
    research_episodes: int = 0
    chapters: int = 0
    total_chars: int = 0
    target_chars: int = 0
    total_cost_usd: float = 0.0
    total_time_sec: float = 0.0
    error: str = ""


class AgentTeam:
    """멀티 에이전트 팀 오케스트레이터."""

    def __init__(
        self,
        project_id: str,
        slug: str,
        topic: str,
        target_length: int = 10000,
        art_style: str = "",
        max_parallel: int = 4,
        on_progress: callable = None,
    ):
        self.project_id = project_id
        self.slug = slug
        self.topic = topic
        self.target_length = target_length
        self.art_style = art_style
        self.max_parallel = max_parallel
        self.on_progress = on_progress or (lambda phase, msg: None)

        # 분량 역산
        self.needed_chapters = self._calc_chapters(target_length)
        self.needed_episodes = max(self.needed_chapters * 2, int(target_length / 500))

        # 공유 상태
        self._research_data = {}
        self._outline = {}
        self._chapters = {}
        self._total_cost = 0.0

    def _calc_chapters(self, chars: int) -> int:
        """목표 분량 → 챕터 수."""
        avg_per_chapter = 800
        n = max(1, round(chars / avg_per_chapter))
        return min(n, 20)

    # ═══════════════════════════════════════
    # 메인 실행
    # ═══════════════════════════════════════

    def run(self) -> TeamResult:
        """전체 파이프라인 실행."""
        start = time.time()

        try:
            # Phase 1: 병렬 리서치
            self.on_progress("research", f"리서치 시작 (목표 에피소드 {self.needed_episodes}개)")
            research = self._phase_research()

            # Phase 2: 아웃라인 + 스타일가이드
            self.on_progress("outline", f"아웃라인 설계 ({self.needed_chapters}챕터)")
            outline = self._phase_outline(research)

            # Phase 3: 병렬 집필
            self.on_progress("writing", f"병렬 집필 시작 ({self.needed_chapters}챕터)")
            chapters = self._phase_writing(outline, research)

            # Phase 4: 통합 + 일관성 검수
            self.on_progress("integration", "메인작가 통합 검수")
            manuscript = self._phase_integration(outline, chapters)

            # Phase 5: 검증 + 보강
            self.on_progress("review", "팩트체크 + 분량 검증")
            final = self._phase_review(manuscript, research)

            # 저장
            self.on_progress("save", "Supabase 저장")
            self._save_results(research, outline, final)

            elapsed = time.time() - start
            char_count = sum(len(ch) for ch in final.values())

            return TeamResult(
                status="completed",
                research_episodes=len(research.get("episodes", [])),
                chapters=len(final),
                total_chars=char_count,
                target_chars=self.target_length,
                total_cost_usd=self._total_cost,
                total_time_sec=elapsed,
            )

        except Exception as e:
            return TeamResult(
                status="failed",
                total_cost_usd=self._total_cost,
                total_time_sec=time.time() - start,
                error=str(e),
            )

    # ═══════════════════════════════════════
    # Phase 1: 병렬 리서치
    # ═══════════════════════════════════════

    def _phase_research(self) -> dict:
        """리서치 에이전트를 병렬 dispatch."""
        # 주제를 시대/영역별로 분할
        segments = self._split_research_segments()

        all_episodes = []
        all_stats = []
        all_figures = []
        all_timeline = []
        all_sources = []

        with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
            futures = {}
            for seg in segments:
                f = pool.submit(self._run_researcher, seg)
                futures[f] = seg["label"]

            for f in as_completed(futures):
                label = futures[f]
                try:
                    result = f.result()
                    all_episodes.extend(result.get("episodes", []))
                    all_stats.extend(result.get("statistics", []))
                    all_figures.extend(result.get("key_figures", []))
                    all_timeline.extend(result.get("timeline", []))
                    all_sources.extend(result.get("sources", []))
                    self.on_progress("research", f"  {label}: 에피소드 {len(result.get('episodes', []))}개 수집")
                except Exception as e:
                    self.on_progress("research", f"  {label}: 실패 - {e}")

        # 에피소드 부족 시 추가 리서치
        if len(all_episodes) < self.needed_episodes:
            gap = self.needed_episodes - len(all_episodes)
            self.on_progress("research", f"  에피소드 부족 ({len(all_episodes)}/{self.needed_episodes}), {gap}개 추가 리서치")
            extra = self._run_gap_research(all_episodes, gap)
            all_episodes.extend(extra.get("episodes", []))
            all_stats.extend(extra.get("statistics", []))

        # 타임라인 시간순 정렬
        all_timeline.sort(key=lambda x: x.get("date", ""))

        # key_figures 중복 제거
        seen_names = set()
        unique_figures = []
        for fig in all_figures:
            if fig["name"] not in seen_names:
                seen_names.add(fig["name"])
                unique_figures.append(fig)

        research = {
            "topic": self.topic,
            "summary": f"{self.topic} — {len(all_episodes)}개 에피소드, {len(all_stats)}개 데이터포인트",
            "episodes": all_episodes,
            "statistics": all_stats,
            "key_figures": unique_figures,
            "timeline": all_timeline,
            "sources": all_sources,
            "comparisons": [],
        }
        self._research_data = research
        return research

    def _split_research_segments(self) -> list:
        """주제를 리서치 세그먼트로 분할."""
        # 기본: 시대별 3분할 + 테마별 추가
        base = [
            {
                "label": "창업기-초기성장",
                "query_hints": [
                    f"{self.topic} 탄생 초기 역사 창업자",
                    f"{self.topic} origin founding early history",
                ],
                "focus": "탄생 배경, 창업자, 초기 성장, 핵심 인물",
            },
            {
                "label": "성장기-황금기",
                "query_hints": [
                    f"{self.topic} 성장 확장 마케팅 전략",
                    f"{self.topic} growth expansion marketing strategy",
                ],
                "focus": "성장 전략, 마케팅 혁신, 글로벌 확장, 경쟁",
            },
            {
                "label": "현대-미래",
                "query_hints": [
                    f"{self.topic} 현재 매출 시장점유율 미래 전략 2025 2026",
                    f"{self.topic} recent revenue market share future",
                ],
                "focus": "현재 위상, 재무 데이터, 최신 전략, 논란, 미래 전망",
            },
        ]

        # 에피소드 목표가 높으면 세그먼트 추가
        if self.needed_episodes > 20:
            base.append({
                "label": "일화-논란-문화",
                "query_hints": [
                    f"{self.topic} 논란 실패 위기 문화적 영향 일화",
                    f"{self.topic} controversy failure crisis cultural impact anecdote",
                ],
                "focus": "실패 사례, 논란, 법적 분쟁, 문화적 영향, 흥미로운 일화",
            })

        return base

    def _run_researcher(self, segment: dict) -> dict:
        """단일 리서치 세그먼트 실행."""
        prompt = f"""당신은 전문 리서처입니다. 아래 주제에 대해 심층 리서치를 수행하세요.

주제: {self.topic}
초점 영역: {segment['focus']}
검색 힌트: {', '.join(segment['query_hints'])}

## 작업

1. 위 검색 힌트를 기반으로 WebSearch를 3~5회 수행하세요.
2. 검색 결과에서 에피소드, 데이터, 인물, 타임라인을 추출하세요.
3. 결과를 아래 JSON 형식으로 정리하여 출력하세요.

## 출력 형식 (반드시 JSON만 출력)

```json
{{
  "episodes": [
    {{
      "title": "에피소드 제목",
      "content": "1-2문장 요약",
      "narrative_draft": "200-500자 대본 수준 서술",
      "must_include": [{{"fact": "핵심 팩트", "reason": "중요한 이유"}}],
      "visual_hints": ["chart", "quote", "timeline", "image"]
    }}
  ],
  "statistics": [
    {{"metric": "지표명", "value": "수치", "unit": "단위", "year": "연도", "context": "맥락"}}
  ],
  "key_figures": [
    {{"name": "인물명", "role": "역할", "relevance": "주제와의 관계"}}
  ],
  "timeline": [
    {{"date": "YYYY", "event": "사건", "significance": "중요도"}}
  ],
  "sources": [
    {{"title": "출처 제목", "url": "URL"}}
  ]
}}
```

에피소드를 최소 5개 이상 추출하세요. 각 narrative_draft는 200~500자로 상세하게 써주세요."""

        tool_executor = self._make_tool_executor()
        config = AgentConfig(
            model="claude-sonnet-4-5-20250929",
            max_turns=15,
            max_tokens_per_turn=8192,
            budget_usd=1.0,
            timeout_sec=120,
            allowed_tools=["web_search", "web_fetch"],
            system_prompt="당신은 전문 리서치 에이전트입니다. 한국어로 답변하세요.",
        )

        loop = AgentLoop(tool_executor)
        result = loop.run(config, prompt)
        self._total_cost += result.cost_usd

        # JSON 파싱
        return self._extract_json(result.final_text)

    def _run_gap_research(self, existing_episodes: list, gap: int) -> dict:
        """부족한 에피소드를 추가 리서치."""
        existing_titles = [ep.get("title", "") for ep in existing_episodes]

        prompt = f"""주제: {self.topic}

이미 수집된 에피소드: {json.dumps(existing_titles, ensure_ascii=False)}

위에 없는 새로운 에피소드를 {gap}개 이상 추가로 리서치하세요.
다음 관점에서 탐색하세요:
- 핵심 인물의 개인사/일화
- 실패 사례/위기/논란
- 문화적 영향
- 경쟁사와의 비교
- 최신 데이터/뉴스

JSON 형식으로만 출력하세요 (episodes, statistics 포함)."""

        tool_executor = ToolExecutor(workspace_dir=None, allowed_paths=["/tmp"])
        config = AgentConfig(
            model="claude-sonnet-4-5-20250929",
            max_turns=10,
            budget_usd=0.5,
            timeout_sec=90,
            allowed_tools=["web_search", "web_fetch"],
        )
        loop = AgentLoop(tool_executor)
        result = loop.run(config, prompt)
        self._total_cost += result.cost_usd
        return self._extract_json(result.final_text)

    # ═══════════════════════════════════════
    # Phase 2: 아웃라인 + 스타일가이드
    # ═══════════════════════════════════════

    def _phase_outline(self, research: dict) -> dict:
        """메인작가가 아웃라인을 설계."""
        episodes_summary = json.dumps(
            [{"title": ep["title"], "content": ep.get("content", "")}
             for ep in research.get("episodes", [])],
            ensure_ascii=False
        )
        stats_summary = json.dumps(research.get("statistics", [])[:20], ensure_ascii=False)

        prompt = f"""당신은 메인 작가입니다. 아래 리서치를 바탕으로 영상 원고의 아웃라인을 설계하세요.

## 정보
- 주제: {self.topic}
- 목표 분량: {self.target_length}자
- 필요 챕터 수: {self.needed_chapters}개
- 에피소드 목록: {episodes_summary}
- 주요 통계: {stats_summary}

## 규칙
- 각 챕터는 500~1300자 범위
- 1챕터 = 1서브 주제 (뭉뚱그리지 않음)
- 3막 구조: Act1 (15-20%), Act2 (60-70%), Act3 (15-20%)
- 챕터 간 자연스러운 연결 고리 설계

## 출력 (JSON만)

```json
{{
  "chapters": [
    {{
      "number": 1,
      "title": "챕터 제목",
      "act": 1,
      "target_chars": 800,
      "key_points": ["포인트1", "포인트2"],
      "episodes_to_use": ["에피소드 제목1", "에피소드 제목2"],
      "transition_in": "",
      "transition_out": "다음 챕터로의 연결 문장 힌트"
    }}
  ],
  "style_guide": {{
    "tone": "대화체 설명",
    "sentence_max": 40,
    "forbidden": ["번역체", "논문체"],
    "sample_paragraph": "이런 느낌으로 써야 합니다... (3-5문장 예시)"
  }}
}}
```"""

        tool_executor = ToolExecutor(workspace_dir=None, allowed_paths=["/tmp"])
        config = AgentConfig(
            model="claude-opus-4-6",
            max_turns=5,
            max_tokens_per_turn=16384,
            budget_usd=2.0,
            timeout_sec=120,
            allowed_tools=[],
        )
        loop = AgentLoop(tool_executor)
        result = loop.run(config, prompt)
        self._total_cost += result.cost_usd

        outline = self._extract_json(result.final_text)
        self._outline = outline
        return outline

    # ═══════════════════════════════════════
    # Phase 3: 병렬 집필
    # ═══════════════════════════════════════

    def _phase_writing(self, outline: dict, research: dict) -> dict:
        """서브작가들이 챕터를 병렬 집필."""
        chapters_list = outline.get("chapters", [])
        style_guide = outline.get("style_guide", {})

        # 챕터를 그룹으로 분할 (서브작가당 2~4챕터)
        group_size = max(2, math.ceil(len(chapters_list) / self.max_parallel))
        groups = []
        for i in range(0, len(chapters_list), group_size):
            groups.append(chapters_list[i:i + group_size])

        results = {}
        with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
            futures = {}
            for group in groups:
                nums = [ch["number"] for ch in group]
                f = pool.submit(
                    self._run_sub_writer, group, style_guide, research
                )
                futures[f] = nums

            for f in as_completed(futures):
                nums = futures[f]
                try:
                    chapter_texts = f.result()
                    results.update(chapter_texts)
                    self.on_progress("writing", f"  Ch {nums} 완료")
                except Exception as e:
                    self.on_progress("writing", f"  Ch {nums} 실패: {e}")

        self._chapters = results
        return results

    def _run_sub_writer(self, chapters: list, style_guide: dict, research: dict) -> dict:
        """서브작가 — 할당된 챕터들을 집필."""
        # 해당 챕터에 필요한 에피소드만 추출
        needed_titles = set()
        for ch in chapters:
            needed_titles.update(ch.get("episodes_to_use", []))

        relevant_episodes = [
            ep for ep in research.get("episodes", [])
            if ep.get("title") in needed_titles
        ]
        # 매칭 안 되면 전체 에피소드를 줌
        if not relevant_episodes:
            relevant_episodes = research.get("episodes", [])

        chapters_spec = json.dumps(chapters, ensure_ascii=False)
        episodes_data = json.dumps(relevant_episodes, ensure_ascii=False)
        style_data = json.dumps(style_guide, ensure_ascii=False)
        stats_data = json.dumps(research.get("statistics", [])[:15], ensure_ascii=False)

        prompt = f"""당신은 서브 작가입니다. 아래 챕터들을 집필하세요.

## 스타일 가이드 (반드시 준수)
{style_data}

## 작성할 챕터
{chapters_spec}

## 사용할 에피소드/데이터
에피소드: {episodes_data}
통계: {stats_data}

## 규칙
1. 각 챕터의 target_chars에 맞춰 분량 조절 (±10%)
2. 대화체 (~거든요, ~입니다)
3. 한 문장 최대 40자
4. 씬 경계에 --- 구분선
5. 챕터 시작은 ## Chapter N: 제목
6. transition_in을 자연스럽게 연결
7. transition_out 힌트에 맞춰 챕터 끝 맺기

## 출력
각 챕터의 원고 텍스트를 순서대로 작성하세요. JSON이 아니라 마크다운 원고입니다."""

        tool_executor = ToolExecutor(workspace_dir=None, allowed_paths=["/tmp"])
        config = AgentConfig(
            model="claude-opus-4-6",
            max_turns=5,
            max_tokens_per_turn=16384,
            budget_usd=3.0,
            timeout_sec=180,
            allowed_tools=[],
        )
        loop = AgentLoop(tool_executor)
        result = loop.run(config, prompt)
        self._total_cost += result.cost_usd

        # 챕터별 분리
        chapter_texts = {}
        for ch in chapters:
            num = ch["number"]
            chapter_texts[num] = self._extract_chapter(result.final_text, num)

        return chapter_texts

    # ═══════════════════════════════════════
    # Phase 4: 통합 + 일관성 검수
    # ═══════════════════════════════════════

    def _phase_integration(self, outline: dict, chapters: dict) -> dict:
        """메인작가가 전체 원고를 통합 검수."""
        # 챕터 순서대로 합치기
        sorted_nums = sorted(chapters.keys())
        full_text = "\n\n".join(chapters.get(n, "") for n in sorted_nums)

        prompt = f"""당신은 메인 작가입니다. 서브 작가들이 집필한 챕터를 통합 검수하세요.

## 원고
{full_text}

## 검수 항목
1. **톤 통일**: 챕터 간 문체가 다르면 수정
2. **중복 제거**: 같은 내용이 여러 챕터에 나오면 한 곳만 남김
3. **연결 매끄럽게**: 챕터 간 전환이 자연스러운지 확인, 필요시 수정
4. **분량 확인**: 전체 {self.target_length}자 목표. 부족하면 보강, 초과하면 다듬기
5. **스토리 아크**: 도입→전개→결말이 자연스러운지

## 출력
수정된 전체 원고를 챕터별로 출력하세요. ## Chapter N: 제목 형식 유지."""

        tool_executor = ToolExecutor(workspace_dir=None, allowed_paths=["/tmp"])
        config = AgentConfig(
            model="claude-opus-4-6",
            max_turns=5,
            max_tokens_per_turn=16384,
            budget_usd=3.0,
            timeout_sec=180,
            allowed_tools=[],
        )
        loop = AgentLoop(tool_executor)
        result = loop.run(config, prompt)
        self._total_cost += result.cost_usd

        # 챕터별 분리
        integrated = {}
        for num in sorted_nums:
            text = self._extract_chapter(result.final_text, num)
            if text:
                integrated[num] = text
            else:
                integrated[num] = chapters.get(num, "")

        return integrated

    # ═══════════════════════════════════════
    # Phase 5: 검증 + 보강
    # ═══════════════════════════════════════

    def _phase_review(self, chapters: dict, research: dict) -> dict:
        """리뷰어가 팩트체크 + 분량 검증."""
        full_text = "\n\n".join(chapters[n] for n in sorted(chapters.keys()))
        char_count = sum(len(ch) for ch in chapters.values())

        # 분량 부족 시 Director가 보강 지시
        if char_count < self.target_length * 0.85:
            self.on_progress("review", f"  분량 부족 ({char_count}/{self.target_length}), 보강 중...")
            chapters = self._boost_chapters(chapters, research)

        return chapters

    def _boost_chapters(self, chapters: dict, research: dict) -> dict:
        """분량 부족 챕터를 보강."""
        current_total = sum(len(ch) for ch in chapters.values())
        deficit = self.target_length - current_total

        # 가장 짧은 챕터들을 보강
        sorted_by_length = sorted(chapters.items(), key=lambda x: len(x[1]))

        for num, text in sorted_by_length[:3]:
            boost_amount = min(deficit // 3, 500)
            if boost_amount < 100:
                break

            prompt = f"""아래 챕터를 {boost_amount}자 정도 보강하세요. 새로운 디테일, 일화, 수치를 추가하세요.
기존 톤과 문체를 유지하세요.

{text}

보강된 전체 챕터를 출력하세요."""

            tool_executor = ToolExecutor(workspace_dir=None, allowed_paths=["/tmp"])
            config = AgentConfig(
                model="claude-sonnet-4-5-20250929",
                max_turns=3,
                budget_usd=0.5,
                timeout_sec=60,
                allowed_tools=[],
            )
            loop = AgentLoop(tool_executor)
            result = loop.run(config, prompt)
            self._total_cost += result.cost_usd

            if len(result.final_text) > len(text):
                chapters[num] = result.final_text
                deficit -= (len(result.final_text) - len(text))

        return chapters

    # ═══════════════════════════════════════
    # 저장
    # ═══════════════════════════════════════

    def _save_results(self, research: dict, outline: dict, chapters: dict):
        """결과를 Supabase Storage에 저장."""
        from auto_agent.storage import ProjectStorage

        ps = ProjectStorage(self.project_id)

        # research_report.json
        ps.save_json("research_report.json", research)

        # outline.json
        ps.save_json("outline.json", outline)

        # final_manuscript.md
        sorted_nums = sorted(chapters.keys())
        title_line = f"# {self.topic}\n\n"
        full = title_line + "\n\n".join(chapters[n] for n in sorted_nums)
        ps.save_text("final_manuscript.md", full)

        # 챕터별 분할
        for num in sorted_nums:
            ps.save_text(f"chapters/ch{num}.md", chapters[num])

    # ═══════════════════════════════════════
    # 유틸
    # ═══════════════════════════════════════

    def _make_tool_executor(self) -> ToolExecutor:
        """ToolExecutor 생성."""
        from pathlib import Path
        tmp = Path("/tmp")
        return ToolExecutor(workspace_root=tmp, project_dir=tmp)

    def _extract_json(self, text: str) -> dict:
        """텍스트에서 JSON 블록 추출."""
        import re
        # ```json ... ``` 블록 찾기
        match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # 전체가 JSON인 경우
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # { ... } 블록 찾기
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}

    def _extract_chapter(self, text: str, chapter_num: int) -> str:
        """전체 텍스트에서 특정 챕터 추출."""
        import re
        pattern = rf"(## Chapter {chapter_num}:.*?)(?=## Chapter \d+:|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
