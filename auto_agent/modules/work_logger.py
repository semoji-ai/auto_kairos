"""작업 로그 수집 — Stage 1~3 수정 명령, 에러 로그 기록.

관리자 에이전트(kairos-admin-agent)가 이 로그를 분석해서
버그/취향/패턴을 분류하고 자동 개선한다.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class WorkLogger:
    """프로젝트별 작업 로그 수집."""

    def __init__(self, project_dir: Path):
        self._log_dir = project_dir / "work_logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._log_file = self._log_dir / f"{self._today}.jsonl"

    def log(self, project: str, scene: Optional[int], source: str,
            action: str, before: Optional[Dict], after: Optional[Dict],
            user: str = "system") -> Dict:
        """작업 로그 1건 기록.

        Args:
            project: 프로젝트 slug
            scene: 씬 번호 (없으면 None)
            source: "dashboard" | "claude" | "agent"
            action: "image_regenerate" | "layout_change" | "headline_edit" |
                    "tts_regenerate" | "narration_edit" | "style_change" | "error"
            before: 변경 전 상태
            after: 변경 후 상태
            user: 사용자 ID
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project,
            "scene": scene,
            "source": source,
            "action": action,
            "before": before,
            "after": after,
            "user": user,
        }

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.debug("작업 로그: %s/%s scene=%s action=%s",
                      project, source, scene, action)
        return entry

    def get_today_logs(self) -> list:
        """오늘 로그 전체 반환."""
        if not self._log_file.exists():
            return []
        logs = []
        for line in self._log_file.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs

    def get_project_logs(self, project: str, days: int = 7) -> list:
        """특정 프로젝트의 최근 N일 로그."""
        from datetime import timedelta
        all_logs = []
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = self._log_dir / f"{date}.jsonl"
            if log_file.exists():
                for line in log_file.read_text(encoding="utf-8").split("\n"):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get("project") == project:
                                all_logs.append(entry)
                        except json.JSONDecodeError:
                            continue
        return all_logs

    def get_action_stats(self, days: int = 7) -> Dict:
        """작업 유형별 통계."""
        from collections import Counter
        from datetime import timedelta
        actions = Counter()
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            log_file = self._log_dir / f"{date}.jsonl"
            if log_file.exists():
                for line in log_file.read_text(encoding="utf-8").split("\n"):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            actions[entry.get("action", "unknown")] += 1
                        except json.JSONDecodeError:
                            continue
        return dict(actions)
