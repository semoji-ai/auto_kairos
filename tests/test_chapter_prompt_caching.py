"""챕터 병렬 호출의 정적 블록은 시스템 프롬프트로 간다 — 그래야 캐시를 탄다.

## 왜 이 파일이 있나

`step_2`(씬 분할)는 챕터 수만큼 claude CLI 를 병렬 호출한다(LG편 기준 7회). 그
7회가 **똑같은 정적 블록**(`<agent_skill>` + `<shared_skills>`, chapters 모드
슬라이스 기준 57KB)을 각자 들고 갔다.

`docs/token-waste-audit.md` 1-B 는 이것을 「CLI 라서 캐싱 경로를 못 탄다」고 적고
Anthropic SDK 전환을 제안했다. **틀렸다.** CLI 는 캐싱을 한다. 실측:

    정적 블록을 --append-system-prompt-file 로   2회차: write 0      read 106,516
    정적 블록을 stdin(user 메시지)로              2회차: write 83,454 read  23,069

**user 메시지에 있으면 캐시를 못 탄다.** 자리를 옮기면 탄다 — SDK 전환도 API 키도
필요 없다. 이 파일이 그 자리를 고정한다.
"""
from __future__ import annotations

import json

import pytest

from auto_agent.orchestrator.runner import PipelineRunner


class TestStaticBlockPlacement:
    def test_system_prompt_carries_the_static_block(self):
        """정적 블록은 시스템 프롬프트 쪽에 담긴다."""
        text = PipelineRunner._build_chapter_static_system(
            agent_skill="SKILL 본문",
            shared_skills_text="\n\n## 공유\n\n공유 본문",
        )
        assert "<agent_skill>" in text
        assert "SKILL 본문" in text
        assert "<shared_skills>" in text
        assert "공유 본문" in text

    def test_shared_skills_omitted_when_empty(self):
        """공유 스킬이 없으면 빈 태그를 넣지 않는다 — 바이트가 달라지면 캐시가 갈린다."""
        text = PipelineRunner._build_chapter_static_system("SKILL 본문", "")
        assert "<shared_skills>" not in text

    def test_identical_inputs_give_identical_bytes(self):
        """캐시는 prefix 바이트 일치다. 같은 입력이면 한 바이트도 달라선 안 된다."""
        a = PipelineRunner._build_chapter_static_system("SKILL", "공유")
        b = PipelineRunner._build_chapter_static_system("SKILL", "공유")
        assert a == b


class TestSystemPromptFile:
    def test_same_content_reuses_one_file(self, tmp_path):
        """7개 챕터가 같은 파일을 본다 — 파일이 갈리면 캐시도 갈린다."""
        p1 = PipelineRunner._write_chapter_system_prompt(tmp_path, "같은 내용")
        p2 = PipelineRunner._write_chapter_system_prompt(tmp_path, "같은 내용")
        assert p1 == p2
        assert p1.read_text(encoding="utf-8") == "같은 내용"

    def test_different_content_gives_different_file(self, tmp_path):
        p1 = PipelineRunner._write_chapter_system_prompt(tmp_path, "내용 A")
        p2 = PipelineRunner._write_chapter_system_prompt(tmp_path, "내용 B")
        assert p1 != p2

    def test_concurrent_writes_do_not_tear(self, tmp_path):
        """병렬 발사 중에 반쯤 쓰인 파일을 읽으면 캐시가 어긋난다."""
        from concurrent.futures import ThreadPoolExecutor

        body = "가" * 40_000
        with ThreadPoolExecutor(max_workers=8) as pool:
            paths = list(pool.map(
                lambda _: PipelineRunner._write_chapter_system_prompt(tmp_path, body),
                range(8),
            ))
        assert len(set(paths)) == 1
        assert paths[0].read_text(encoding="utf-8") == body


class TestCostParsingCapturesCache:
    """캐시 토큰을 안 읽으면 캐시가 도는지 아닌지 알 수가 없다.

    CLI 는 usage 에 cache_creation_input_tokens / cache_read_input_tokens 를
    이미 준다(실측 확인). 파서가 버리고 있었다.
    """

    def _runner(self):
        return PipelineRunner.__new__(PipelineRunner)

    def test_cache_fields_are_recorded(self):
        payload = json.dumps({
            "type": "result",          # 실제 CLI 출력이 갖는 판별자
            "usage": {
                "input_tokens": 2,
                "output_tokens": 4,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 106516,
            },
            "total_cost_usd": 0.01,
            "model": "claude-opus-4-6",
        })
        info = self._runner()._parse_claude_cost(payload, "")
        assert info["cache_read"] == 106516
        assert info["cache_write"] == 0

    def test_missing_cache_fields_default_to_zero(self):
        """옛 CLI 나 다른 출력 형식에서도 죽지 않는다."""
        payload = json.dumps({"type": "result",
                              "usage": {"input_tokens": 10, "output_tokens": 5}})
        info = self._runner()._parse_claude_cost(payload, "")
        assert info["cache_read"] == 0
        assert info["cache_write"] == 0
        assert info["tokens_in"] == 10


class TestCacheWarming:
    """7개를 동시에 던지면 아무도 캐시를 못 읽는다.

    캐시 항목은 **앞선 응답이 시작된 뒤에야** 읽을 수 있다. 동시 발사에서는 7개가
    전부 「아직 없는 캐시」를 보고 각자 쓴다 — 쓰기는 읽기의 12.5배다.
    값싼 호출 하나로 먼저 굽고 던진다.
    """

    def _runner(self, tmp_path, monkeypatch):
        """스킬 로딩은 이 테스트의 관심사가 아니다 — 발사 횟수와 플래그만 본다."""
        r = PipelineRunner.__new__(PipelineRunner)
        r.project_dir = tmp_path
        r.project_slug = "테스트"
        monkeypatch.setattr(r, "_load_agent_skill", lambda *a, **k: "SKILL", raising=False)
        monkeypatch.setattr(r, "_build_shared_skills_text", lambda *a, **k: "공유", raising=False)
        return r

    def test_warms_once_before_fan_out(self, tmp_path, monkeypatch):
        r = self._runner(tmp_path, monkeypatch)
        calls = []
        monkeypatch.setattr(r, "_find_claude_cli", lambda: "/bin/echo", raising=False)

        def fake_run(cmd, **kw):
            calls.append(cmd)
            class P:
                returncode = 0
                stdout = '{"type":"result","usage":{}}'
                stderr = ""
            return P()

        monkeypatch.setattr("subprocess.run", fake_run)
        r._warm_chapter_cache({"agent": "script-director", "mode": "chapters"})

        assert len(calls) == 1, "워밍은 딱 한 번"
        assert "--append-system-prompt-file" in calls[0], "정적 블록을 실어야 캐시가 구워진다"

    def test_warming_failure_does_not_stop_the_run(self, tmp_path, monkeypatch):
        """워밍은 최적화다. 실패해도 본 작업은 그대로 간다."""
        r = self._runner(tmp_path, monkeypatch)
        monkeypatch.setattr(r, "_find_claude_cli", lambda: "/nonexistent", raising=False)

        def boom(*a, **kw):
            raise FileNotFoundError("CLI 없음")

        monkeypatch.setattr("subprocess.run", boom)
        r._warm_chapter_cache({"agent": "script-director", "mode": "chapters"})  # 예외가 새면 실패


class TestChaptersRuleReachesChaptersMode:
    """「chapters 모드 처리 규칙」이 chapters 모드에 도착해야 한다.

    caption 마커(`<!-- caption: ... -->`)를 **쓰는** 것은 manuscript 모드 일이고,
    그것을 씬의 `items` 에 **넣는** 것은 chapters 모드 일이다. 그런데 후자의 규칙이
    「모드 1.5(manuscript)」 섹션 안에 적혀 있어서 슬라이싱이 거꾸로 배달했다 —
    필요한 chapters 에는 없고, `items`/`headline` 을 손대는 것이 금지된 manuscript
    에는 있었다.
    """

    def _slice(self, mode: str) -> str:
        import pathlib
        from auto_agent.orchestrator.skill_slicer import slice_agent_skill
        full = pathlib.Path(
            "auto_agent/data/skills/agents/script-director/SKILL.md"
        ).read_text(encoding="utf-8")
        return slice_agent_skill(full, "script-director", mode)

    RULE = "각 항목을 그 씬의 `items` 배열에"

    def test_chapters_mode_gets_the_rule(self):
        assert self.RULE in self._slice("chapters")

    def test_manuscript_mode_does_not_get_it(self):
        """manuscript 는 items/headline 을 손대는 것이 금지다 — 이 규칙을 주면 안 된다."""
        assert self.RULE not in self._slice("manuscript")

    def test_manuscript_still_learns_to_write_the_marker(self):
        """마커를 **쓰는** 법은 manuscript 일이다. 그건 남아 있어야 한다."""
        assert "caption:" in self._slice("manuscript")
