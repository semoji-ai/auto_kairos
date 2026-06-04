"""스킬 반환 포맷 헬퍼.

Skill Contract: artifact_paths / summary / decisions 세 가지만 메인에 반환.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class SkillResult:
    artifact_paths: list[str] = field(default_factory=list)
    summary: str = ""
    decisions: list[str] = field(default_factory=list)

    def add_artifact(self, path: Path | str) -> None:
        self.artifact_paths.append(str(path))

    def add_decision(self, note: str) -> None:
        self.decisions.append(note)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)
