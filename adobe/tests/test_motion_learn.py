import json
from pathlib import Path
from scripts.motion_learn import state


def test_state_roundtrip(tmp_path):
    ref = tmp_path / "abc123"
    state.set_stage(ref, "collected", {"title": "Test"})
    s = state.get_state(ref)
    assert s["stage"] == "collected" and s["title"] == "Test"
    state.set_stage(ref, "analyzed")
    assert state.get_state(ref)["stage"] == "analyzed"
    assert state.get_state(ref)["title"] == "Test"   # 기존 필드 보존


def test_state_missing(tmp_path):
    assert state.get_state(tmp_path / "none") == {}


def test_slug_stable():
    from scripts.motion_learn import collect
    s1 = collect.slug_for("https://youtu.be/AbC123xyz")
    s2 = collect.slug_for("https://youtu.be/AbC123xyz")
    assert s1 == s2 and len(s1) == 12 and s1.isalnum()


def test_collect_skips_existing(tmp_path, monkeypatch):
    from scripts.motion_learn import collect
    calls = []
    monkeypatch.setattr(collect, "_run_ytdlp", lambda url, out: (calls.append(url), out.write_bytes(b"x"))[-1])
    monkeypatch.setattr(collect, "_probe_meta", lambda p: {"title": "T", "duration": 10.0, "width": 1920, "height": 1080})
    refs = tmp_path / "refs"
    r1 = collect.collect(["https://youtu.be/AbC123xyz"], refs)
    assert len(r1) == 1 and len(calls) == 1
    r2 = collect.collect(["https://youtu.be/AbC123xyz"], refs)   # 이미 받음 → 스킵
    assert len(calls) == 1 and r2[0]["slug"] == r1[0]["slug"]


def test_merge_presets(tmp_path):
    from scripts.motion_learn import merge_presets
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {"props": ["opacity"], "ease": "easeOut"}}}), encoding="utf-8")
    candidates = [
        {"name": "wipe_in", "props": ["trimEnd"], "ease": "easeInOut", "params": {}},
        {"name": "fade_scale_in", "props": ["opacity"], "ease": "easeOut"},   # 중복 → 스킵
        {"name": "particle_burst", "props": ["particles"], "ease": "easeOut"}  # 새 props → 빌더확장 플래그
    ]
    res = merge_presets.merge(lib, candidates, approved=["wipe_in", "fade_scale_in", "particle_burst"])
    d = json.loads(lib.read_text())
    assert "wipe_in" in d["presets"]
    assert res["skipped_duplicate"] == ["fade_scale_in"]
    assert res["needs_builder"] == ["particle_burst"]
    assert "particle_burst" in d["presets"]


def test_merge_known_props_only():
    from scripts.motion_learn import merge_presets
    assert merge_presets.is_builder_supported({"props": ["opacity", "scale"]})
    assert not merge_presets.is_builder_supported({"props": ["particles"]})


def test_analyze_splits_output(tmp_path, monkeypatch):
    """gemini 응답(JSON)을 motion.json + new_presets.json으로 분리 저장."""
    from scripts.motion_learn import analyze, state
    refs = tmp_path / "refs"; ref = refs / "slug1"; ref.mkdir(parents=True)
    (refs / "slug1.mp4").write_bytes(b"x")
    state.set_stage(ref, "collected", {"url": "u"})
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {}}}), encoding="utf-8")
    fake = {"cuts": [{"type": "cut", "start": 0, "dur": 1, "layers": []}],
            "new_presets": [{"name": "wipe_in", "props": ["trimEnd"], "ease": "easeInOut"}]}
    monkeypatch.setattr(analyze, "_gemini_analyze", lambda mp4, lib_keys: fake)
    res = analyze.analyze("slug1", refs, lib)
    assert json.loads((ref / "motion.json").read_text())["cuts"][0]["dur"] == 1
    assert json.loads((ref / "new_presets.json").read_text())[0]["name"] == "wipe_in"
    assert state.get_state(ref)["stage"] == "analyzed"
    assert res["new_preset_count"] == 1


def test_cli_help_lists_commands():
    """CLI가 collect/analyze/merge 서브커맨드를 제공."""
    import scripts.motion_learn.__main__ as cli
    p = cli.build_parser()
    sub = p._subparsers._group_actions[0].choices
    assert "collect" in sub and "analyze" in sub and "merge" in sub


def test_cli_merge_syncs_jsx(tmp_path, monkeypatch):
    """merge 후 jsx 빌더 복사본 동기화 — 새 프리셋이 빌더에도 반영."""
    import scripts.motion_learn.__main__ as cli
    # ROOT 하위 구조 모킹
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    lib = tmp_path / "data" / "artstyle" / "motion" / "motion_presets.json"; lib.parent.mkdir(parents=True)
    lib.write_text(json.dumps({"presets": {}}), encoding="utf-8")
    monkeypatch.setattr(cli, "LIB", lib)
    jsxdir = tmp_path / "cep" / "com.autokairos.pd" / "jsx" / "tylenol"; jsxdir.mkdir(parents=True)
    ref = tmp_path / "refs" / "s1"; ref.mkdir(parents=True)
    monkeypatch.setattr(cli, "REFS", tmp_path / "refs")
    (ref / "new_presets.json").write_text(json.dumps([{"name": "wipe_in", "props": ["trimEnd"], "ease": "easeInOut"}]), encoding="utf-8")
    cli.main(["merge", "--slug", "s1", "--approve", "wipe_in"])
    assert "wipe_in" in json.loads((jsxdir / "motion_presets.json").read_text())["presets"]


def test_smoothness_to_influence_anchors():
    from scripts.motion_learn.curve import smoothness_to_influence
    assert smoothness_to_influence(0.0) == 0
    assert smoothness_to_influence(0.5) == 33
    assert smoothness_to_influence(0.75) == 75
    assert smoothness_to_influence(0.9) == 90
    assert smoothness_to_influence(1.0) == 95


def test_smoothness_to_influence_interp_and_clamp():
    from scripts.motion_learn.curve import smoothness_to_influence
    # 0.5~0.75 구간 중앙(0.625): 33 + (75-33)*0.5 = 54
    assert smoothness_to_influence(0.625) == 54
    # 범위 밖 클램프
    assert smoothness_to_influence(-1.0) == 0
    assert smoothness_to_influence(2.0) == 95
    # .5 경계 반올림은 jsx Math.round(half-up)와 일치해야 함 (Python 기본 round=banker's면 92)
    assert smoothness_to_influence(0.95) == 93  # 90 + 5*0.5 = 92.5 → half-up 93


def test_gemini_client_compare_videos(monkeypatch):
    from scripts.motion_learn import gemini_client as gc
    monkeypatch.setattr(gc, "_client", lambda: object())
    monkeypatch.setattr(gc, "_upload", lambda client, p: "FILE:" + p)
    captured = {}
    monkeypatch.setattr(gc, "_generate_json",
                        lambda client, contents, models=None: (captured.update(contents=contents), {"score": 88})[1])
    out = gc.compare_videos("orig.mp4", "render.mp4", "PROMPT")
    assert out == {"score": 88}
    assert captured["contents"] == ["FILE:orig.mp4", "FILE:render.mp4", "PROMPT"]


def test_gemini_client_analyze_video(monkeypatch):
    from scripts.motion_learn import gemini_client as gc
    monkeypatch.setattr(gc, "_client", lambda: object())
    monkeypatch.setattr(gc, "_upload", lambda client, p: "F:" + p)
    monkeypatch.setattr(gc, "_generate_json",
                        lambda client, contents, models=None: {"cuts": [], "contents_len": len(contents)})
    out = gc.analyze_video("v.mp4", "PROMPT")
    assert out["contents_len"] == 2  # [file, prompt]


def test_verify_structural_check():
    from scripts.motion_learn.verify import structural_check
    lib = {"presets": {"fade_scale_in": {}, "slide_in": {}}}
    motion_ok = {"cuts": [{"layers": [{"anim": [{"preset": "fade_scale_in"}]}]}]}
    r = structural_check(motion_ok, lib)
    assert r["pass"] is True and r["cut_count"] == 1 and r["issues"] == []
    motion_bad = {"cuts": [{"layers": [{"anim": [{"preset": "nope"}]}]}]}
    r2 = structural_check(motion_bad, lib)
    assert r2["pass"] is False and any("nope" in i for i in r2["issues"])
    r3 = structural_check({"cuts": []}, lib)
    assert r3["pass"] is False


def test_verify_passes_gate():
    from scripts.motion_learn.verify import passes_gate
    assert passes_gate(True, 80, 75) is True
    assert passes_gate(True, 70, 75) is False
    assert passes_gate(False, 99, 75) is False


def test_verify_parse_verdict():
    from scripts.motion_learn.verify import parse_verdict
    v = parse_verdict('{"score": 82, "diffs": [{"cut": 0, "kind": "easing", "detail": "x"}], "summary": "ok"}')
    assert v["score"] == 82 and v["diffs"][0]["kind"] == "easing" and v["summary"] == "ok"
    v2 = parse_verdict({"score": "50"})
    assert v2["score"] == 50 and v2["diffs"] == []


def test_verify_commands():
    from scripts.motion_learn.verify import build_ae_command, build_ffmpeg_command
    assert build_ae_command("/AE", "/x/verify.jsx") == ["/AE", "-r", "/x/verify.jsx"]
    assert build_ffmpeg_command("a.mov", "b.mp4")[:3] == ["ffmpeg", "-y", "-i"]
    assert build_ffmpeg_command("a.mov", "b.mp4")[-1] == "b.mp4"


def test_verify_orchestration(tmp_path, monkeypatch):
    import subprocess
    from scripts.motion_learn import verify as V, gemini_client, state
    refs = tmp_path / "refs"; ref = refs / "s1"; ref.mkdir(parents=True)
    (refs / "s1.mp4").write_bytes(b"orig")
    (ref / "motion.json").write_text(json.dumps({"cuts": [{"layers": [{"anim": [{"preset": "fade_scale_in"}]}]}]}), encoding="utf-8")
    lib = tmp_path / "motion_presets.json"
    lib.write_text(json.dumps({"presets": {"fade_scale_in": {}}}), encoding="utf-8")

    # AE/ffmpeg subprocess 모킹: 호출되면 출력 파일 생성
    def fake_run(cmd, **kw):
        cmd = [str(a) for a in cmd]
        if "-r" in cmd:                      # AE 헤드리스 렌더 호출 → env 경로에 mov 생성
            p = (kw.get("env") or {}).get("AK_VERIFY_OUT")
            if p:
                open(p, "wb").write(b"mov")
        elif cmd and cmd[0] == "ffmpeg":     # ffmpeg 변환 호출 → 마지막 인자(mp4) 생성
            open(cmd[-1], "wb").write(b"mp4")
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(gemini_client, "compare_videos",
                        lambda a, b, prompt, **kw: {"score": 80, "diffs": [], "summary": "good"})

    out = V.verify("s1", refs, lib, threshold=75)
    assert out["passed"] is True and out["score"] == 80
    assert (ref / "verify" / "verdict.json").is_file()
    assert state.get_state(ref)["stage"] == "verified"


def test_verify_missing_inputs(tmp_path):
    from scripts.motion_learn import verify as V
    refs = tmp_path / "refs"; (refs / "s2").mkdir(parents=True)
    lib = tmp_path / "lib.json"; lib.write_text('{"presets":{}}', encoding="utf-8")
    out = V.verify("s2", refs, lib)
    assert "error" in out


def test_cli_verify_dispatch(tmp_path, monkeypatch):
    import scripts.motion_learn.__main__ as cli
    monkeypatch.setattr(cli, "REFS", tmp_path / "refs")
    monkeypatch.setattr(cli, "LIB", tmp_path / "lib.json")
    captured = {}
    from scripts.motion_learn import verify as V
    monkeypatch.setattr(V, "verify",
                        lambda slug, refs, lib, **kw: captured.update(slug=slug) or {"passed": True, "score": 90, "structural": {"issues": []}})
    cli.main(["verify", "--slug", "s9"])
    assert captured["slug"] == "s9"
