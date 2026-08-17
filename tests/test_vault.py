import json
from pathlib import Path
from backend import vault, assistant


def _proj(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"v1"}]}', encoding="utf-8")
    return d


def test_worklog_roundtrip(tmp_path):
    d = _proj(tmp_path)
    vault.log_work(d, "split_layers", "씬1 레이어 5개 분리")
    vault.log_work(d, "tts_all", "TTS 3/3")
    txt = vault.worklog_text(d)
    assert "[split_layers]" in txt and "씬1 레이어 5개 분리" in txt and "[tts_all]" in txt


def test_context_roundtrip(tmp_path):
    d = _proj(tmp_path)
    assert vault.read_context(d) == ""
    vault.write_context(d, "# 브리핑\n- 씬5는 슬로우 줌으로 결정")
    assert "슬로우 줌" in vault.read_context(d)


def test_undistilled_incremental(tmp_path):
    d = _proj(tmp_path)
    for i in range(5):
        assistant.append_history(d, "user", f"메시지{i}")
    assert len(vault.undistilled_turns(d)) == 5
    vault.mark_distilled(d, 5)
    assert vault.undistilled_turns(d) == []
    assistant.append_history(d, "user", "새 메시지")
    assert len(vault.undistilled_turns(d)) == 1          # 증분만


def test_distill_writes_context_and_marks(tmp_path, monkeypatch):
    """새 세션 시작 시 쌓인 대화가 브리핑으로 증류됨."""
    d = _proj(tmp_path)
    for i in range(7):                                    # 임계(6) 초과
        assistant.append_history(d, "user", f"상의 {i}")

    def fake_run(prompt, cwd, *, output_last=None, **kw):
        assert "프로젝트 브리핑" in prompt and "상의 0" in prompt
        Path(output_last).write_text("# 브리핑\n- 사용자는 미니멀 연출 선호", encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    assistant._distill_to_vault(d)
    assert "미니멀 연출" in vault.read_context(d)
    assert vault.undistilled_turns(d) == []               # 증류 위치 마킹


def test_full_prompt_includes_vault(tmp_path, monkeypatch):
    d = _proj(tmp_path)
    vault.write_context(d, "- 씬5 슬로우 줌 결정")
    vault.log_work(d, "assemble", "매니페스트 5씬")
    p = assistant._full_prompt(d, "다음 뭐할까?")
    assert "프로젝트 볼트 브리핑" in p and "슬로우 줌" in p
    assert "최근 작업 이력" in p and "[assemble]" in p
