"""trend-analyst / performance-analyst Claude CLI 실행 래퍼."""
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_vault_dir, get_data_dir
from auto_agent.utils.platform import subprocess_kwargs

logger = logging.getLogger(__name__)


class AgentRunner:
    """에이전트 실행 래퍼 — Claude CLI로 에이전트 호출."""

    def __init__(self):
        self._vault_dir = get_vault_dir()
        self._data_dir = get_data_dir()
        self._agents_config = self._load_agents_config()

    def run_trend_analyst(self, channel: str, seed: Optional[str] = None,
                          autoresearch: bool = False, max_rounds: int = 5) -> Dict:
        """trend-analyst 에이전트 실행."""
        if autoresearch:
            from auto_agent.modules.auto_research_loop import AutoResearchLoop
            loop = AutoResearchLoop(channel=channel, max_rounds=max_rounds, seed=seed)
            prompt = loop.build_loop_prompt()
            config = self._agents_config.get("agents", {}).get("trend-analyst", {})
            # autoresearch는 웹 검색 필요
            return self._run_agent(prompt, config, extra_tools=["WebSearch", "WebFetch"])
        prompt = self.build_trend_analyst_prompt(channel, seed)
        config = self._agents_config.get("agents", {}).get("trend-analyst", {})
        return self._run_agent(prompt, config)

    def run_performance_analyst(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> Dict:
        """performance-analyst 에이전트 실행."""
        prompt = self.build_performance_analyst_prompt(mode, channel, video_id)
        config = self._agents_config.get("agents", {}).get("performance-analyst", {})
        return self._run_agent(prompt, config)

    # ── 프롬프트 빌더 ──

    def build_trend_analyst_prompt(self, channel: str, seed: Optional[str] = None) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/trend-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["market-analysis"])

        if seed:
            mode_text = f"""## 실행 모드: 시드 모드
사용자 키워드: "{seed}"
이 키워드를 기반으로 볼트에서 관련 데이터를 탐색하고,
트렌드 적합성 + 채널 적합성을 검증하여 기획안 1개를 구체화하세요."""
        else:
            mode_text = """## 실행 모드: 자율 모드
볼트의 트렌드, 채널 성과, 경쟁 채널 데이터를 교차 분석하여
주제 후보 3~5개를 순위화한 기획안을 생성하세요."""

        return f"""# trend-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 트렌드: market/trends/
- 채널 성과: channels/{channel}/videos/
- 경쟁 채널: channels/competitors/
- 기존 피드백: insights/feedback/
- 기존 기획안: insights/planning/

## 출력
기획안을 insights/planning/{today}-기획안.md 로 저장하세요.

{skill_content}

{shared_skills}
"""

    def build_performance_analyst_prompt(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/performance-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["channel-metrics", "market-analysis"])

        if mode == "video" and video_id:
            mode_text = f"""## 실행 모드: 영상 성과 분석
영상 ID: {video_id}
channels/{channel}/videos/ 에서 해당 영상 노트를 찾아 성과를 분석하세요.
기획안의 예상 성과 대비 실제 달성률을 평가하세요."""
        else:
            mode_text = f"""## 실행 모드: 주간 종합 리뷰
이번 주 {channel} 채널의 전체 성과를 분석하세요.
경쟁 채널 동향을 확인하고 watchlist 리뷰를 수행하세요.
Stage 0 피드백을 insights/feedback/ 에 저장하세요."""

        return f"""# performance-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 채널 성과: channels/{channel}/videos/
- 채널 Analytics: channels/{channel}/analytics/
- 경쟁 채널: channels/competitors/
- 트렌드: market/trends/
- 기존 인사이트: insights/performance/
- 피드백 출력: insights/feedback/

{skill_content}

{shared_skills}
"""

    # ── Claude CLI 실행 ──

    def _run_agent(self, prompt: str, config: Dict,
                   extra_tools: Optional[List[str]] = None) -> Dict:
        """Claude CLI로 에이전트 실행."""
        model = config.get("model", "sonnet")
        max_turns = config.get("max_turns", 30)
        timeout = config.get("max_duration_minutes", 15) * 60

        cmd = self._build_claude_cmd(model=model, max_turns=max_turns,
                                     extra_tools=extra_tools)

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._vault_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                **subprocess_kwargs(),
            )
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)

            return {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout", "returncode": -1, "stdout": "", "stderr": "timeout"}
        except Exception as e:
            return {"status": "error", "returncode": -1, "stdout": "", "stderr": str(e)}

    def _build_claude_cmd(self, model: str, max_turns: int,
                          extra_tools: Optional[List[str]] = None) -> List[str]:
        """Claude CLI 명령어 빌드."""
        cli_path = self._find_claude_cli()
        tools = ["Read", "Write", "Glob", "Grep"]
        if extra_tools:
            tools.extend(extra_tools)
        cmd = [
            cli_path, "--print", "--output-format", "json",
            "--model", model, "--max-turns", str(max_turns),
        ]
        for tool in tools:
            cmd += ["--allowedTools", tool]
        return cmd

    def _find_claude_cli(self) -> str:
        """Claude CLI 바이너리 경로."""
        import shutil
        path = shutil.which("claude")
        if path:
            return path
        raise FileNotFoundError("Claude CLI를 찾을 수 없습니다. 'claude'가 PATH에 있는지 확인하세요.")

    # ── 스킬 로딩 ──

    def _load_skill(self, relative_path: str) -> str:
        path = self._data_dir / "skills" / relative_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("스킬 파일 없음: %s", path)
        return ""

    def _load_shared_skills(self, skill_names: List[str]) -> str:
        parts = []
        for name in skill_names:
            content = self._load_skill(f"shared/{name}.md")
            if content:
                parts.append(content)
        return "\n\n---\n\n".join(parts)

    def _load_agents_config(self) -> Dict:
        path = self._data_dir / "agents.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}
