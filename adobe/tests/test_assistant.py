import json
from pathlib import Path
from backend import assistant


def _proj(tmp_path, scenes_arr):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": scenes_arr}, ensure_ascii=False), encoding="utf-8")
    return d


def test_catalog_names():
    assert set(assistant.ACTION_HANDLERS) == {
        "generate_missing_images", "edit_images",
        "split_layers", "tts_all", "plan_motion", "assemble"}


def test_edit_images_needs_instruction(tmp_path):
    """무엇을 바꿀지 없으면 아무것도 하지 않는다 — 빈 지시로 그림을 건드리면 안 된다."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "e1", "imageRef": "storyboard/a.png"}])
    r = assistant._h_edit_images(d, instruction="")
    assert r["edited"] == 0 and "error" in r


def test_edit_images_reports_scenes_without_image(tmp_path, monkeypatch):
    """고칠 그림이 없는 씬은 **조용히 넘기지 않는다.** 왜 안 됐는지 알아야 한다."""
    d = _proj(tmp_path, [{"sceneNumber": 7, "sceneId": "e7"}])      # 이미지 없음
    r = assistant._h_edit_images(d, instruction="안경을 뺀다")
    assert r["edited"] == 0 and r.get("no_image") == [7]


def test_plan_motion_handler(tmp_path, monkeypatch):
    d = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "pa", "narration": "n"},          # 레이어 없음 → 스킵
        {"sceneNumber": 2, "sceneId": "pb", "narration": "n"},          # 레이어 있음 → 대상
        {"sceneNumber": 3, "sceneId": "pc", "narration": "n"},          # 모션 파일 이미 있음 → 스킵
    ])
    lay = d / "layers"; lay.mkdir()
    (lay / "pb__0_a.png").write_bytes(b"x")
    (lay / "pc__0_a.png").write_bytes(b"x")
    (d / "motion_pc.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr(assistant.motion, "plan_scene_motion",
                        lambda proj_dir, sn, **kw: (calls.append(sn) or {"layers": [], "camera": {"type": "none"}}))
    res = assistant._h_plan_motion(d)
    assert calls == [2] and res == {"planned": 1}


def test_project_status_summary(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "n",
                          "imageRef": "storyboard/sb_a.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    st = assistant.project_status(d)
    assert "1" in st and "이미지" in st


def test_plan_actions_parses(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        Path(output_last).write_text('{"actions":[{"action":"tts_all","reason":"음성"},'
                                     '{"action":"assemble","reason":"합치기"}]}', encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    planned = assistant.plan_actions(d, "음성 입혀서 합쳐줘")
    assert [a["action"] for a in planned["actions"]] == ["tts_all", "assemble"]
    assert planned["reply"] is None


def test_plan_actions_failure_returns_empty(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    monkeypatch.setattr(assistant.llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert assistant.plan_actions(d, "뭐든") == {"actions": [], "reply": None}


def test_run_assistant_dispatches_in_order(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    calls = []
    handlers = {
        "tts_all": lambda proj_dir, on_event=None: calls.append("tts") or {"done": 1},
        "assemble": lambda proj_dir, on_event=None: calls.append("asm") or {"path": "m.json"},
    }
    out = assistant.run_assistant(
        d, "x",
        planner=lambda proj_dir, instr, on_line=None: [
            {"action": "tts_all", "reason": "r1"}, {"action": "assemble", "reason": "r2"}],
        handlers=handlers)
    assert calls == ["tts", "asm"]
    assert [r["action"] for r in out["results"]] == ["tts_all", "assemble"]
    assert out["results"][0]["result"] == {"done": 1}


def test_run_assistant_unknown_action_skipped(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    out = assistant.run_assistant(
        d, "x",
        planner=lambda proj_dir, instr, on_line=None: [{"action": "nope", "reason": "?"}],
        handlers={})
    assert out["results"][0]["result"]["status"] == "skipped"


def test_generate_missing_images_only_missing(tmp_path, monkeypatch):
    from backend import imagegen, scenes as sc
    d = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "a", "image_prompt": "그림1", "imageRef": "storyboard/sb_a.png"},
        {"sceneNumber": 2, "sceneId": "b", "image_prompt": "그림2", "imageRef": ""}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    gen = []

    def fake_gen(proj_dir, rel_out, prompt, *, subdir="images", **kw):
        gen.append(prompt)
        (proj_dir / subdir).mkdir(parents=True, exist_ok=True)
        (proj_dir / subdir / rel_out).write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(proj_dir / subdir / rel_out)}

    monkeypatch.setattr(imagegen, "generate_one", fake_gen)
    res = assistant.ACTION_HANDLERS["generate_missing_images"](d)
    assert gen == ["그림2"] and res["generated"] == 1     # 씬2만(씬1은 이미 이미지 있음)


def test_tts_all_handler(tmp_path, monkeypatch):
    from backend import tts as _tts
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "안녕"},
                         {"sceneNumber": 2, "sceneId": "b", "narration": ""}])
    monkeypatch.setattr(_tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: {"status": "completed"})
    res = assistant.ACTION_HANDLERS["tts_all"](d)
    assert res["generated"] == 1                          # 내레이션 있는 씬만


def test_assemble_handler(tmp_path, monkeypatch):
    from backend import manifest
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    monkeypatch.setattr(manifest, "build_manifest",
                        lambda proj_dir, only_scenes=None: {"path": "m.json", "scenes": 1})
    assert assistant.ACTION_HANDLERS["assemble"](d)["scenes"] == 1


def test_tts_all_handler_prefers_narration_tts(tmp_path, monkeypatch):
    from backend import tts as _tts
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "원문",
                          "narration_tts": "교정본"}])
    seen = []
    monkeypatch.setattr(_tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: seen.append(text) or
                        {"status": "completed"})
    res = assistant.ACTION_HANDLERS["tts_all"](d)
    assert res["generated"] == 1 and seen == ["교정본"]


def test_plan_actions_question_returns_reply(tmp_path, monkeypatch):
    """질문이면 actions 비우고 reply 답변 — 비서가 상담 모드로 응답."""
    d = _proj(tmp_path, [{"sceneNumber": 2, "sceneId": "q1", "narration": "씬 둘"}])
    cap = {}

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        cap["prompt"] = prompt
        Path(output_last).write_text(
            '{"actions":[],"reply":"씬 2는 인물 2명 + 전경 책상 1 + 강조 사물 1로 4개 분리를 권합니다."}',
            encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    out = assistant.run_assistant(d, "2번 씬은 레이어 몇 개로 나누면 좋을까?")
    assert out["reply"].startswith("씬 2는")
    assert out["plan"] == [] and out["results"] == []
    assert "질문" in cap["prompt"] and "씬2" in cap["prompt"].replace(" ", "")   # 씬별 상태 제공


def test_run_assistant_legacy_list_planner_compat(tmp_path):
    """구형(list 반환) 주입 플래너 호환 유지."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    out = assistant.run_assistant(
        d, "x",
        planner=lambda proj_dir, instr, on_line=None: [{"action": "assemble", "reason": "r"}],
        handlers={"assemble": lambda proj_dir, on_event=None: {"scenes": 0}})
    assert out["plan"][0]["action"] == "assemble" and out["reply"] is None


def test_history_roundtrip_and_prompt_inclusion(tmp_path, monkeypatch):
    """대화 이력이 저장되고 다음 플래닝 프롬프트에 포함 — 이어지는 상의 가능."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "h1", "narration": "n"}])
    cap = {}

    def fake_run(prompt, cwd, **kw):
        cap["prompt"] = prompt
        Path(kw["output_last"]).write_text('{"actions":[],"reply":"씬 1부터 보시죠."}', encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    assistant.run_assistant(d, "어떤 씬부터 작업할까?")
    out2 = assistant.run_assistant(d, "그럼 그 다음은?")
    assert "어떤 씬부터 작업할까?" in cap["prompt"]       # 이전 사용자 발화 포함
    assert "씬 1부터 보시죠." in cap["prompt"]            # 이전 비서 답변 포함
    assert "이전 대화" in cap["prompt"]
    assert out2["reply"] == "씬 1부터 보시죠."


def test_prompt_defaults_to_consult(tmp_path, monkeypatch):
    """프롬프트가 상담 기본 + 명확한 명령만 실행 원칙을 명시."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "c2"}])
    cap = {}

    def fake_run(prompt, cwd, **kw):
        cap["prompt"] = prompt
        Path(kw["output_last"]).write_text('{"actions":[],"reply":"r"}', encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    assistant.plan_actions(d, "음")
    assert "기본은 '대화'" in cap["prompt"]
    assert "명확하게 실행을 지시" in cap["prompt"]
    assert "실행할까요?" in cap["prompt"]                  # 모호하면 제안만


def test_session_persists_and_resumes(tmp_path, monkeypatch):
    """첫 호출=풀 프롬프트+세션 저장, 둘째 호출=resume(짧은 프롬프트+session_id 전달)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "s1"}])
    calls = []

    def fake_run(prompt, cwd, *, session_id=None, output_schema=None, output_last=None, on_line=None, **kw):
        calls.append({"sid": session_id, "prompt": prompt})
        Path(output_last).write_text('{"actions":[],"reply":"네."}', encoding="utf-8")
        return {"returncode": 0, "session_id": "sess-abc"}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    monkeypatch.setattr(assistant.llm, "get_orchestrator", lambda: "codex")
    assistant.plan_actions(d, "첫 질문")
    assistant.plan_actions(d, "이어지는 질문")
    assert calls[0]["sid"] is None and "응답 규칙" in calls[0]["prompt"]      # 새 세션=풀 프롬프트
    assert calls[1]["sid"] == "sess-abc"                                     # resume
    assert "응답 규칙" not in calls[1]["prompt"] and "이어지는 질문" in calls[1]["prompt"]


def test_session_reset_on_engine_switch(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "s2"}])
    assistant._save_session(d, "claude", "old-claude-sess")
    seen = {}

    def fake_run(prompt, cwd, *, session_id=None, output_last=None, **kw):
        seen["sid"] = session_id
        Path(output_last).write_text('{"actions":[],"reply":"r"}', encoding="utf-8")
        return {"returncode": 0, "session_id": "new"}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    monkeypatch.setattr(assistant.llm, "get_orchestrator", lambda: "codex")  # 엔진 변경
    assistant.plan_actions(d, "q")
    assert seen["sid"] is None                            # 다른 엔진 세션은 무시(새 세션)


def test_stale_session_retries_fresh(tmp_path, monkeypatch):
    """저장된 세션이 죽어 있으면(resume 실패) 새 세션으로 1회 재시도."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "s3"}])
    assistant._save_session(d, "codex", "dead-sess")
    calls = []

    def fake_run(prompt, cwd, *, session_id=None, output_last=None, **kw):
        calls.append(session_id)
        if session_id == "dead-sess":
            return {"returncode": 1, "session_id": None}   # resume 실패
        Path(output_last).write_text('{"actions":[],"reply":"복구됨"}', encoding="utf-8")
        return {"returncode": 0, "session_id": "fresh"}

    monkeypatch.setattr(assistant.llm, "run_orchestrator", fake_run)
    monkeypatch.setattr(assistant.llm, "get_orchestrator", lambda: "codex")
    out = assistant.plan_actions(d, "q")
    assert calls == ["dead-sess", None] and out["reply"] == "복구됨"
    assert assistant._load_session(d)["session_id"] == "fresh"


def test_targets_narrow_scope(tmp_path):
    """'1씬만' 지시가 전 씬 생성으로 번지지 않아야 한다."""
    import json as _j
    from backend import assistant
    (tmp_path / "scenes.json").write_text(_j.dumps({"scenes": [
        {"sceneNumber": i, "sceneId": f"s{i}", "image_prompt": "p"} for i in range(1, 6)
    ]}), encoding="utf-8")
    data = {"scenes": _j.loads((tmp_path / "scenes.json").read_text())["scenes"]}
    assert [s["sceneNumber"] for s in assistant._target_scenes(data, [1])] == [1]
    assert [s["sceneNumber"] for s in assistant._target_scenes(data, [2, 4])] == [2, 4]
    assert len(assistant._target_scenes(data, [])) == 5        # 빈 배열 = 전체(명시적 전체 지시)
    assert len(assistant._target_scenes(data, None)) == 5


def test_run_assistant_passes_targets_and_cancel(tmp_path):
    from backend import assistant
    seen = {}

    def _h(proj_dir, on_event=None, targets=None, should_cancel=None):
        seen["targets"] = targets
        seen["cancellable"] = should_cancel is not None
        return {"ok": True}

    res = assistant.run_assistant(
        tmp_path, "1씬 이미지 만들어줘",
        planner=lambda d, i: {"actions": [{"action": "gen", "reason": "r", "targets": [1]}], "reply": None},
        handlers={"gen": _h}, should_cancel=lambda: False)
    assert seen["targets"] == [1] and seen["cancellable"] is True
    assert res["results"][0]["targets"] == [1]


def test_cancel_stops_between_items():
    from backend import assistant
    from backend.jobs import JobCancelled
    import pytest as _p
    with _p.raises(JobCancelled):
        assistant._check(lambda: True, 3)
    assistant._check(lambda: False, 3)          # 취소 아니면 통과
    assistant._check(None, 0)
