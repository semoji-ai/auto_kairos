"""
Vault RAG — Obsidian 볼트 기반 지식 검색 + 축적 시스템

파이프라인의 각 단계에서:
  - 리서치 전: 기존 주제/방법론/소스를 검색하여 에이전트 컨텍스트에 주입
  - 원고 작성 전: 서사 패턴/문체 DNA를 검색하여 컨텍스트에 주입
  - 리서치 후: 핵심 팩트/타임라인/소스를 볼트에 자동 축적
  - 프로젝트 완료 후: 회고 노트 생성

Phase 1: 키워드 기반 마크다운 검색 (현재)
Phase 2: 벡터 임베딩 기반 시맨틱 검색 (향후)
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 볼트 기본 경로 (환경변수로 오버라이드 가능)
VAULT_DIR = Path(os.environ.get(
    "KAIROS_VAULT_DIR",
    os.path.expanduser("~/Desktop/kairos-vault"),
))


class VaultRAG:
    """Obsidian 볼트 검색 + 저장 인터페이스."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = vault_dir or VAULT_DIR
        self.enabled = self.vault_dir.exists()
        if not self.enabled:
            print(f"[VaultRAG] 볼트 미발견: {self.vault_dir} — 비활성")

    # ─────────────────────────────────────
    # 검색 (리서치/원고 전)
    # ─────────────────────────────────────

    def search_for_research(self, topic: str, category: str = "") -> str:
        """리서치 시작 전: 관련 기존 지식을 검색하여 컨텍스트 텍스트 반환."""
        if not self.enabled:
            return ""

        sections = []

        # 1. 기존 주제 리서치 검색
        topics = self._search_files(
            self.vault_dir / "02-research" / "topics",
            topic,
            max_results=3,
        )
        if topics:
            sections.append("## 기존 리서치 (볼트)")
            for path, snippet in topics:
                sections.append(f"### {path.stem}\n{snippet}\n")

        # 2. 카테고리별 리서치 방법론
        methodology = self._search_files(
            self.vault_dir / "02-research" / "methodology",
            category or topic,
            max_results=2,
        )
        if methodology:
            sections.append("## 리서치 방법론 (볼트)")
            for path, snippet in methodology:
                sections.append(f"### {path.stem}\n{snippet}\n")

        # 3. 신뢰 소스 DB
        sources = self._search_files(
            self.vault_dir / "02-research" / "sources",
            category or topic,
            max_results=2,
        )
        if sources:
            sections.append("## 참고 소스 DB (볼트)")
            for path, snippet in sources:
                sections.append(f"### {path.stem}\n{snippet}\n")

        # 4. 관련 콘텐츠 아카이브 (이전 원고 분석)
        content_dir = self._resolve_content_dir(category)
        if content_dir:
            content = self._search_files(content_dir, topic, max_results=2)
            if content:
                sections.append("## 관련 콘텐츠 (볼트)")
                for path, snippet in content:
                    sections.append(f"### {path.stem}\n{snippet}\n")

        if not sections:
            return ""

        return (
            "<vault_knowledge>\n"
            "아래는 Obsidian 볼트에서 검색된 기존 지식입니다. "
            "리서치 시 참고하되, 새로운 정보와 교차 검증하세요.\n\n"
            + "\n".join(sections)
            + "\n</vault_knowledge>"
        )

    def search_for_manuscript(self, topic: str, category: str = "") -> str:
        """원고 작성 전: 서사 패턴/문체 DNA를 검색하여 컨텍스트 텍스트 반환."""
        if not self.enabled:
            return ""

        sections = []

        # 1. 카테고리별 서사 분석
        storytelling = self._search_files(
            self.vault_dir / "01-patterns" / "storytelling",
            category or topic,
            max_results=2,
        )
        if storytelling:
            sections.append("## 서사 패턴 (볼트)")
            for path, snippet in storytelling:
                sections.append(f"### {path.stem}\n{snippet}\n")

        # 2. 프로젝트 회고 (유사 프로젝트)
        retros = self._search_files(
            self.vault_dir / "07-projects",
            topic,
            max_results=2,
        )
        if retros:
            sections.append("## 유사 프로젝트 회고 (볼트)")
            for path, snippet in retros:
                sections.append(f"### {path.stem}\n{snippet}\n")

        if not sections:
            return ""

        return (
            "<vault_patterns>\n"
            "아래는 Obsidian 볼트에서 검색된 서사 패턴/회고입니다. "
            "원고 구성 시 참고하세요.\n\n"
            + "\n".join(sections)
            + "\n</vault_patterns>"
        )

    # ─────────────────────────────────────
    # 축적 (리서치/원고 후)
    # ─────────────────────────────────────

    def save_research_result(self, topic: str, category: str,
                             summary: str, key_facts: List[str],
                             sources: List[str]) -> Optional[Path]:
        """리서치 완료 후: 핵심 팩트/소스를 볼트에 축적."""
        if not self.enabled:
            return None

        topics_dir = self.vault_dir / "02-research" / "topics"
        topics_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r'[/\\:*?"<>|]', '_', topic)
        filepath = topics_dir / f"{safe_name}.md"

        content = f"""---
tags: [research, {category}]
date: {datetime.now().strftime('%Y-%m-%d')}
topic: {topic}
---

# {topic}

## 요약
{summary}

## 핵심 팩트
"""
        for fact in key_facts:
            content += f"- {fact}\n"

        content += "\n## 출처\n"
        for src in sources:
            content += f"- {src}\n"

        filepath.write_text(content, encoding="utf-8")
        print(f"[VaultRAG] 리서치 결과 저장: {filepath}")
        return filepath

    def save_project_retro(self, project_slug: str, topic: str,
                           successes: List[str], improvements: List[str],
                           patterns: List[str]) -> Optional[Path]:
        """프로젝트 완료 후: 회고 노트 생성."""
        if not self.enabled:
            return None

        project_dir = self.vault_dir / "07-projects" / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)

        filepath = project_dir / "retro.md"

        content = f"""---
tags: [retro, project]
date: {datetime.now().strftime('%Y-%m-%d')}
project: {project_slug}
topic: {topic}
---

# {project_slug} 회고

## 성공 요인
"""
        for s in successes:
            content += f"- {s}\n"

        content += "\n## 개선할 점\n"
        for i in improvements:
            content += f"- {i}\n"

        content += "\n## 추출 패턴\n"
        for p in patterns:
            content += f"- {p}\n"

        filepath.write_text(content, encoding="utf-8")
        print(f"[VaultRAG] 프로젝트 회고 저장: {filepath}")
        return filepath

    def record_pipeline_error(
        self,
        step_name: str,
        chapter: int,
        scene_range: tuple,
        error_message: str,
        project_slug: str,
        agent: str = "visual-composer",
        label: str = "",
    ) -> Optional[Path]:
        """파이프라인 에러를 볼트에 기록. 동일 파일이 있으면 recurrence 증가."""
        if not self.enabled:
            return None

        errors_dir = self.vault_dir / "08-dev" / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{step_name}-ch{chapter}-{today}.md"
        filepath = errors_dir / filename

        # 기존 파일이 있으면 recurrence 증가
        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8")
            m = re.search(r"recurrence:\s*(\d+)", existing)
            old_count = int(m.group(1)) if m else 1
            new_count = old_count + 1
            updated = re.sub(
                r"recurrence:\s*\d+",
                f"recurrence: {new_count}",
                existing,
            )
            filepath.write_text(updated, encoding="utf-8")
            print(f"[VaultRAG] 에러 기록 업데이트 (recurrence={new_count}): {filepath}")
            return filepath

        start, end = scene_range
        display_label = label if label else step_name

        content = f"""---
tags: [error, pipeline, chunked-parallel, {step_name}]
date: {today}
severity: minor
pipeline-step: {step_name}
agent: {agent}
project: {project_slug}
status: open
recurrence: 1
---

# {display_label} Ch{chapter} 실패

## 증상
- 챕터 {chapter} (씬 {start}~{end}) LLM 호출 실패
- 재시도 2회 모두 실패

## 원인
{error_message}

## 영향
- 씬 {start}~{end}은 이전 scene_specs 데이터 유지
- 후속 스텝에서 해당 씬 처리 시 이전 단계 데이터 사용

## 관련 패턴
"""
        filepath.write_text(content, encoding="utf-8")
        print(f"[VaultRAG] 에러 기록 생성: {filepath}")
        return filepath

    # ─────────────────────────────────────
    # 내부 유틸
    # ─────────────────────────────────────

    def _search_files(self, directory: Path, query: str,
                      max_results: int = 3) -> List[tuple]:
        """디렉토리 내 .md 파일에서 키워드 검색.

        Returns: [(Path, snippet_text), ...]
        """
        if not directory.exists():
            return []

        query_lower = query.lower()
        # 쿼리를 단어로 분할하여 개별 매칭
        keywords = [w for w in query_lower.split() if len(w) >= 2]
        if not keywords:
            keywords = [query_lower]

        results = []
        for md_file in directory.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
                text_lower = text.lower()

                # 파일명 또는 내용에서 키워드 매칭
                filename_lower = md_file.stem.lower()
                score = 0
                for kw in keywords:
                    if kw in filename_lower:
                        score += 10  # 파일명 매칭은 높은 점수
                    score += text_lower.count(kw)

                if score > 0:
                    # 스니펫 추출 (첫 번째 키워드 주변 300자)
                    snippet = self._extract_snippet(text, keywords, max_chars=500)
                    results.append((md_file, snippet, score))
            except Exception:
                continue

        # 점수 내림차순 정렬
        results.sort(key=lambda x: x[2], reverse=True)
        return [(r[0], r[1]) for r in results[:max_results]]

    def _extract_snippet(self, text: str, keywords: List[str],
                         max_chars: int = 500) -> str:
        """텍스트에서 키워드 주변 스니펫 추출."""
        text_lower = text.lower()

        # frontmatter 제거
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                text = text[end + 3:].strip()
                text_lower = text.lower()

        # 첫 번째 키워드 위치 찾기
        best_pos = len(text)
        for kw in keywords:
            pos = text_lower.find(kw)
            if 0 <= pos < best_pos:
                best_pos = pos

        # 키워드 주변 max_chars 추출
        start = max(0, best_pos - 100)
        end = min(len(text), start + max_chars)
        snippet = text[start:end].strip()

        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _resolve_content_dir(self, category: str) -> Optional[Path]:
        """카테고리명 → 콘텐츠 디렉토리 매핑."""
        mapping = {
            "brand": self.vault_dir / "02-content" / "brand",
            "브랜드": self.vault_dir / "02-content" / "brand",
            "common": self.vault_dir / "02-content" / "common",
            "일반상식": self.vault_dir / "02-content" / "common",
            "people": self.vault_dir / "02-content" / "people",
            "인물": self.vault_dir / "02-content" / "people",
            "technology": self.vault_dir / "02-content" / "technology",
            "기술": self.vault_dir / "02-content" / "technology",
            "geography": self.vault_dir / "02-content" / "geography",
            "지리": self.vault_dir / "02-content" / "geography",
        }
        for key, path in mapping.items():
            if key in category.lower():
                return path
        return None

    def _detect_category(self, topic: str) -> str:
        """주제에서 카테고리 자동 판별."""
        topic_lower = topic.lower()

        brand_signals = ["기업", "브랜드", "회사", "창업", "삼성", "현대", "애플", "나이키"]
        people_signals = ["인물", "대통령", "선수", "의사", "장군", "왕", "독립운동"]
        tech_signals = ["기술", "AI", "반도체", "핵", "우주", "과학"]
        geo_signals = ["전쟁", "지정학", "국가", "영토", "분쟁"]

        for signal in brand_signals:
            if signal in topic_lower:
                return "brand"
        for signal in people_signals:
            if signal in topic_lower:
                return "people"
        for signal in tech_signals:
            if signal in topic_lower:
                return "technology"
        for signal in geo_signals:
            if signal in topic_lower:
                return "geography"

        return "common"
