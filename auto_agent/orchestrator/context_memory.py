"""
컨텍스트 메모리 시스템.

역할:
  - 각 pipeline step 완료 후 Haiku 단일 호출로 핵심 결정/발견 요약 수집
  - 다음 에이전트 프롬프트에 이전 컨텍스트 주입
  - 웹 UI에서 조회/수동 편집
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

HAIKU_MODEL = "claude-haiku-4-5-20251001"
MAX_COLLECT_FILES = 5
MAX_FILE_SIZE = 50_000  # bytes
MAX_SNIPPET_LENGTH = 10_000  # chars
SNIPPET_HALF = 5_000  # chars (앞/뒤)

CATEGORY_MAP = {
    "research-orchestrator": "research_decision",
    "script-director": "narrative_structure",
    "assembly-director": "asset_production",
    "character-planner": "character_design",
    "fact-verifier": "fact_check",
}


class ContextMemory:
    """프로젝트별 컨텍스트 메모리 관리."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.memory_path = project_dir / "context_memory.json"

    def load(self) -> dict:
        if self.memory_path.exists():
            return json.loads(self.memory_path.read_text(encoding="utf-8"))
        return {
            "project_slug": self.project_dir.name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "entries": [],
            "manual_notes": [],
        }

    def save(self, memory: dict):
        memory["updated_at"] = datetime.now().isoformat()
        self.memory_path.write_text(
            json.dumps(memory, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ─── Runner 통합: step 완료 후 수집 ───

    def collect_after_step(
        self,
        step_id: str,
        agent_name: str,
        output_files: list,
    ):
        """step 완료 후 Haiku 단일 호출로 핵심 요약 수집.

        비용: ~$0.02 (Haiku, 입력 ~2K tokens, 출력 ~500 tokens)
        """
        import anthropic

        file_snippets = []
        for fp in output_files[:MAX_COLLECT_FILES]:
            p = Path(fp)
            if p.exists() and p.is_file() and p.stat().st_size < MAX_FILE_SIZE:
                content = p.read_text(encoding="utf-8")
                if len(content) > MAX_SNIPPET_LENGTH:
                    content = (
                        content[:SNIPPET_HALF]
                        + "\n...(중략)...\n"
                        + content[-SNIPPET_HALF:]
                    )
                file_snippets.append(f"=== {p.name} ===\n{content}")

        if not file_snippets:
            return

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"파이프라인 step '{step_id}' ({agent_name})의 "
                        f"출력물입니다.\n"
                        f"핵심 의사결정과 발견 사항을 JSON으로 요약하세요.\n\n"
                        f"{chr(10).join(file_snippets)}\n\n"
                        f'출력: {{"summary": "2-3문장", '
                        f'"key_facts": [{{"fact": "...", "source": "..."}}], '
                        f'"decisions": ["..."]}}'
                    ),
                }
            ],
        )

        try:
            entry_data = json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            entry_data = {
                "summary": response.content[0].text[:200],
                "key_facts": [],
                "decisions": [],
            }

        entry = {
            "step_id": step_id,
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "category": CATEGORY_MAP.get(agent_name, "general"),
            **entry_data,
        }

        memory = self.load()
        # 동일 step_id 기존 엔트리 교체 (재실행 시)
        memory["entries"] = [
            e for e in memory["entries"] if e["step_id"] != step_id
        ]
        memory["entries"].append(entry)
        self.save(memory)

    # ─── Runner 통합: 다음 에이전트에 주입 ───

    def build_context_prompt(self, current_step_id: str) -> str:
        """현재 step 이전의 모든 컨텍스트를 프롬프트 문자열로 변환."""
        memory = self.load()
        entries = memory.get("entries", [])
        notes = memory.get("manual_notes", [])

        if not entries and not notes:
            return ""

        lines = [
            "<context_memory>",
            "이전 파이프라인 단계에서 축적된 의사결정과 발견:",
            "",
        ]

        for entry in entries:
            if _step_order(entry["step_id"]) >= _step_order(current_step_id):
                continue
            lines.append(f"### {entry['step_id']} ({entry['agent']})")
            lines.append(entry.get("summary", ""))
            for d in entry.get("decisions", []):
                lines.append(f"  - 결정: {d}")
            for f in entry.get("key_facts", []):
                lines.append(
                    f"  - 데이터: {f['fact']} [{f.get('source', '')}]"
                )
            lines.append("")

        if notes:
            lines.append("### 수동 메모 (운영자)")
            for note in notes:
                lines.append(f"  - {note['note']}")
            lines.append("")

        lines.append("</context_memory>")
        return "\n".join(lines)

    # ─── 웹 UI: 수동 메모 ───

    def add_manual_note(self, note: str, added_by: str = "web_editor"):
        memory = self.load()
        memory.setdefault("manual_notes", []).append(
            {
                "added_at": datetime.now().isoformat(),
                "added_by": added_by,
                "note": note,
            }
        )
        self.save(memory)

    def update_entry(self, step_id: str, patch: dict):
        memory = self.load()
        for entry in memory["entries"]:
            if entry["step_id"] == step_id:
                entry.update(patch)
                break
        self.save(memory)


def _step_order(step_id: str) -> int:
    """step_id에서 순서 번호 추출. 'step_6' → 6, 'step_8b' → 8."""
    m = re.search(r"step_(\d+)", step_id)
    return int(m.group(1)) if m else 999
