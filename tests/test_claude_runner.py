import json
from pathlib import Path
from backend import claude_runner


def test_clean_env_pops_nesting(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setenv("KEEP", "1")
    e = claude_runner._clean_env()
    assert "CLAUDECODE" not in e and "CLAUDE_CODE_ENTRYPOINT" not in e and e.get("KEEP") == "1"


def test_run_claude_writes_output_last(tmp_path, monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd; calls["input"] = kw.get("input"); calls["env"] = kw.get("env")
        class R: returncode = 0; stdout = json.dumps({"type": "result", "result": '{"elements":[]}'}); stderr = ""
        return R()

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    out = tmp_path / "o.json"
    res = claude_runner.run_claude("프롬프트", tmp_path, output_schema=tmp_path / "s.json", output_last=str(out))
    assert res["returncode"] == 0
    assert out.read_text(encoding="utf-8") == '{"elements":[]}'      # result → output_last
    assert "claude" in calls["cmd"][0]
    assert "--json-schema" not in calls["cmd"]                       # 헤드리스 행 이슈로 미사용
    assert calls["input"] == "프롬프트"                               # stdin
    assert "CLAUDECODE" not in (calls["env"] or {})


def test_extract_json_strips_fence_and_prose():
    assert claude_runner._extract_json('```json\n{"a":1}\n```') == '{"a":1}'
    assert claude_runner._extract_json('설명입니다.\n{"a":1, "b":[2,3]}\n끝.') == '{"a":1, "b":[2,3]}'
    assert claude_runner._extract_json('[{"x":1}]') == '[{"x":1}]'
    assert claude_runner._extract_json('json 없음') == 'json 없음'    # 못 찾으면 원문


def test_run_claude_output_schema_extracts_json(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = json.dumps({"type": "result",
                                 "result": '여기 결과입니다:\n```json\n{"score_total":92,"verdict":"PASS"}\n```'})
            stderr = ""
        return R()
    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    out = tmp_path / "o.json"
    claude_runner.run_claude("p", tmp_path, output_schema=tmp_path / "s.json", output_last=str(out))
    data = json.loads(out.read_text(encoding="utf-8"))               # 펜스·머리말 제거 후 파싱 성공
    assert data["score_total"] == 92 and data["verdict"] == "PASS"


def test_run_claude_no_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: None)
    res = claude_runner.run_claude("p", tmp_path)
    assert res["returncode"] != 0


def test_run_claude_plain_text_when_not_json(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "그냥 텍스트"; stderr = ""
        return R()
    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    out = tmp_path / "o.txt"
    claude_runner.run_claude("p", tmp_path, output_last=str(out))
    assert out.read_text(encoding="utf-8") == "그냥 텍스트"           # 엔벨로프 아니면 원문


def test_run_claude_resume_and_session_extract(tmp_path, monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        class R:
            returncode = 0
            stdout = json.dumps({"type": "result", "result": "ok", "session_id": "cl-sess-9"})
            stderr = ""
        return R()

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    res = claude_runner.run_claude("p", tmp_path, session_id="prev-1")
    assert "--resume" in calls["cmd"] and "prev-1" in calls["cmd"]
    assert res["session_id"] == "cl-sess-9"
