import json
from pathlib import Path
from backend import motion


def _proj(tmp_path, scenes_arr):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": scenes_arr}, ensure_ascii=False), encoding="utf-8")
    return d


def test_motion_path():
    assert motion.motion_path(Path("/x"), "ab12") == Path("/x/motion_ab12.json")


def test_plan_scene_motion(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "m1", "narration": "차가 등장한다"}])
    lay = d / "layers"; lay.mkdir()
    (lay / "m1__0_차.png").write_bytes(b"\x89PNG")
    (lay / "m1__bg.png").write_bytes(b"\x89PNG")
    cap = {}

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        cap["prompt"] = prompt
        Path(output_last).write_text(json.dumps({
            "layers": [{"layer": "m1__0_차", "moves": [
                {"type": "slide_in", "start": 0, "duration": 0.8, "direction": "left"}]}],
            "camera": {"type": "slow_zoom_in", "amount": 6}}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    res = motion.plan_scene_motion(d, 1)
    assert res["camera"]["type"] == "slow_zoom_in"
    assert (d / "motion_m1.json").is_file()
    assert "m1__0_차" in cap["prompt"]                 # 레이어 목록이 프롬프트에
    assert "차가 등장한다" in cap["prompt"]              # 내레이션 포함
    assert "m1__bg" not in json.dumps(res)            # 배경은 모션 대상에서 제외 권고(프롬프트에 명시)


def test_plan_scene_motion_no_layers(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "m2", "narration": "n"}])
    res = motion.plan_scene_motion(d, 1)
    assert "error" in res                              # 레이어 없으면 모션 불가


def test_plan_scene_motion_clamps_time(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "m3", "narration": "n",
                          "duration_estimate_sec": 4}])
    lay = d / "layers"; lay.mkdir(); (lay / "m3__0_a.png").write_bytes(b"x")

    def fake_run(prompt, cwd, **kw):
        Path(kw["output_last"]).write_text(json.dumps({
            "layers": [{"layer": "m3__0_a", "moves": [
                {"type": "fade_in", "start": 3.5, "duration": 9.0}]}],   # 씬 길이 초과
            "camera": {"type": "none"}}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    res = motion.plan_scene_motion(d, 1)
    mv = res["layers"][0]["moves"][0]
    assert mv["start"] + mv["duration"] <= 4.0 + 1e-6  # 씬 길이로 클램프


def test_clamp_normalizes_camera_amount():
    plan = {"layers": [], "camera": {"type": "slow_zoom_in", "amount": 0.06}}
    out = motion._clamp_plan(plan, 5.0)
    assert out["camera"]["amount"] == 6.0          # 비율 → 퍼센트


def test_clamp_camera_pan_range():
    plan = {"layers": [], "camera": {"type": "pan_left", "amount": 500}}
    out = motion._clamp_plan(plan, 5.0)
    assert out["camera"]["amount"] == 160.0        # 팬 상한


def test_plan_filters_by_kind_allowed_moves(tmp_path, monkeypatch):
    """kinds 사이드카 있으면 종류별 허용 목록으로 거른다 — 인물은 bob/zoom_emphasis만,
    사물은 사물 목록만(pop은 허용, shake는 인물에 비허용)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ch", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    (lay / "ch__0_남자.png").write_bytes(b"x")
    (lay / "ch__1_책상.png").write_bytes(b"x")
    (lay / "ch__kinds.json").write_text(
        '{"ch__0_남자":"character","ch__1_책상":"object"}', encoding="utf-8")
    cap = {}

    def fake_run(prompt, cwd, **kw):
        cap["prompt"] = prompt
        Path(kw["output_last"]).write_text(json.dumps({
            "layers": [
                {"layer": "ch__0_남자", "moves": [
                    {"type": "bob", "start": 0, "duration": 5},
                    {"type": "shake", "start": 1, "duration": 1}]},      # 인물엔 shake 비허용 → 제거
                {"layer": "ch__1_책상", "moves": [
                    {"type": "pop", "start": 0, "duration": 1}]}],       # 사물엔 pop 허용 → 유지
            "camera": {"type": "none"}}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    res = motion.plan_scene_motion(d, 1)
    assert "ch__1_책상" in cap["prompt"]                    # 사물도 LLM에 제시된다
    by_layer = {L["layer"]: [m["type"] for m in L["moves"]] for L in res["layers"]}
    assert by_layer == {"ch__0_남자": ["bob"], "ch__1_책상": ["pop"]}


def test_plan_excludes_removed_layers(tmp_path, monkeypatch):
    """removed 플래그가 있는 레이어는 매니페스트에서 빠지므로 모션 플랜 대상에서도 빠져야 한다."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "rm", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    (lay / "rm__0_남자.png").write_bytes(b"x")
    (lay / "rm__1_지운차.png").write_bytes(b"x")
    (lay / "rm__elements.json").write_text(json.dumps([
        {"layer": "rm__0_남자", "name_en": "man", "kind": "character"},
        {"layer": "rm__1_지운차", "name_en": "car", "kind": "character", "removed": True},
    ], ensure_ascii=False), encoding="utf-8")
    cap = {}

    def fake_run(prompt, cwd, **kw):
        cap["prompt"] = prompt
        Path(kw["output_last"]).write_text(json.dumps({
            "layers": [{"layer": "rm__0_남자", "moves": [
                {"type": "bob", "start": 0, "duration": 3}]}],
            "camera": {"type": "none"}}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    res = motion.plan_scene_motion(d, 1)
    assert "rm__1_지운차" not in cap["prompt"]           # 제거된 레이어는 LLM에 제시도 안 함
    assert [L["layer"] for L in res["layers"]] == ["rm__0_남자"]


def test_plan_object_only_scene_does_not_error(tmp_path, monkeypatch):
    """캐릭터 없이 사물만 있어도 이제는 에러가 아니다 — 사물도 모션 대상."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ob", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    (lay / "ob__0_책상.png").write_bytes(b"x")
    (lay / "ob__kinds.json").write_text('{"ob__0_책상":"object"}', encoding="utf-8")

    def fake_run(prompt, cwd, **kw):
        Path(kw["output_last"]).write_text(json.dumps({
            "layers": [{"layer": "ob__0_책상", "moves": [
                {"type": "drift", "start": 0, "duration": 1}]}],
            "camera": {"type": "none"}}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    res = motion.plan_scene_motion(d, 1)
    assert "error" not in res
    assert res["layers"][0]["layer"] == "ob__0_책상"


def test_plan_error_when_no_elements_at_all(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "no", "narration": "n"}])
    (d / "layers").mkdir()
    res = motion.plan_scene_motion(d, 1)
    assert "error" in res
