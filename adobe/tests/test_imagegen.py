import json

import pytest

from backend import imagegen


def test_versioned_path_first(tmp_path):
    p = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p.name == "ref_1.png"


def test_versioned_path_no_overwrite(tmp_path):
    (tmp_path / "ref_1.png").write_text("x", encoding="utf-8")
    p = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p.name == "ref_1_v2.png"
    (tmp_path / "ref_1_v2.png").write_text("x", encoding="utf-8")
    p2 = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p2.name == "ref_1_v3.png"


def test_is_rate_limited():
    assert imagegen.is_rate_limited("image_gen rate limit으로 실패") is True
    assert imagegen.is_rate_limited("OK 저장 완료") is False


def test_build_image_prompt():
    pr = imagegen.build_image_prompt("전기차 한 대", "STYLE_DESC", "images/ref_1.png")
    assert "STYLE_DESC" in pr
    assert "전기차 한 대" in pr
    assert "images/ref_1.png" in pr
    assert "image_gen" in pr


def test_build_image_prompt_nochar_forbids_base_person():
    pr = imagegen.build_image_prompt("전기차 충전 장면", "STYLE", "images/s1.png")
    assert "베이스의 인물" in pr and "포함하지 말" in pr
    assert "캐릭터 시트" not in pr


def test_build_image_prompt_character_branch():
    pr = imagegen.build_image_prompt("지오가 차를 가리킴", "STYLE", "images/s1.png",
                                     has_character_ref=True)
    assert "1번 캐릭터 시트" in pr and "100% 동일" in pr
    assert "세모지 베이스" in pr


def test_build_character_prompt_restyle():
    pr = imagegen.build_character_prompt("지오", "갈색 머리, 크림 셔츠", "characters/char_지오.png")
    assert "1번 이미지의 캐릭터를 '지오'" in pr
    assert "그대로 유지" in pr and "헤어와 의상만" in pr
    assert "characters/char_지오.png" in pr
    # 비율 텍스트 지시 금지 원칙이 프롬프트에 명시
    assert "비율을 텍스트로 새로 지정하지 말 것" in pr


def test_generate_one_attaches_base(tmp_path, monkeypatch):
    """character_ref 없으면 베이스만 첨부, has_character_ref=False로 빌드."""
    from backend import imagegen as ig
    seen = {}

    def fake_run(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        seen["images"] = images
        seen["prompt"] = prompt
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "_run_codex_image", fake_run)
    monkeypatch.setattr(ig, "base_img", lambda: tmp_path / "semoji_base.jpg")
    res = ig.generate_one(tmp_path, "ref_1.png", "전기차")
    assert res["status"] == "completed"
    assert seen["images"] == [str(tmp_path / "semoji_base.jpg")]
    assert "베이스의 인물" in seen["prompt"]


def test_generate_one_with_character_ref_order(tmp_path, monkeypatch):
    """character_ref 주면 [캐릭터, 베이스] 순서로 첨부 + 캐릭터 분기."""
    from backend import imagegen as ig
    seen = {}

    def fake_run(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        seen["images"] = images
        seen["prompt"] = prompt
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "_run_codex_image", fake_run)
    monkeypatch.setattr(ig, "base_img", lambda: tmp_path / "base.jpg")
    res = ig.generate_one(tmp_path, "s1.png", "지오가 차를 가리킴",
                          character_ref=str(tmp_path / "char_지오.png"))
    assert res["status"] == "completed"
    assert seen["images"] == [str(tmp_path / "char_지오.png"), str(tmp_path / "base.jpg")]
    assert "1번 캐릭터 시트" in seen["prompt"]


def test_generate_character_needs_base(tmp_path, monkeypatch):
    from backend import imagegen as ig
    monkeypatch.setattr(ig, "base_img", lambda: None)
    res = ig.generate_character(tmp_path, "지오", "갈색 머리")
    assert res["status"] == "failed" and "semoji_base" in res["error"]


def test_generate_character_attaches_base(tmp_path, monkeypatch):
    from backend import imagegen as ig
    seen = {}

    def fake_run(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        seen["images"] = images
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "_run_codex_image", fake_run)
    monkeypatch.setattr(ig, "base_img", lambda: tmp_path / "base.jpg")
    res = ig.generate_character(tmp_path, "지오", "갈색 머리, 크림 셔츠")
    assert res["status"] == "completed"
    assert seen["images"] == [str(tmp_path / "base.jpg")]
    assert (tmp_path / "characters" / "char_지오.png").exists()


def test_versioned_path_in_subdir_concept(tmp_path):
    sb = tmp_path / "storyboard"; sb.mkdir()
    p = imagegen.versioned_path(sb, "sb_1.png")
    assert p.parent.name == "storyboard"
    assert p.name == "sb_1.png"


def test_generate_many_runs_all(tmp_path, monkeypatch):
    from backend import imagegen as ig
    calls = []

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", **kw):
        calls.append(rel_out)
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "generate_one", fake_one)
    items = [("a.png", "p1"), ("b.png", "p2"), ("c.png", "p3")]
    results = ig.generate_many(tmp_path, items, subdir="storyboard", concurrency=3)
    assert len(results) == 3
    assert all(r["status"] == "completed" for r in results.values())
    assert set(calls) == {"a.png", "b.png", "c.png"}


def test_generate_many_concurrency_min_one(tmp_path, monkeypatch):
    from backend import imagegen as ig
    monkeypatch.setattr(ig, "generate_one",
                        lambda proj_dir, rel_out, p, **kw: {"status": "completed", "path": rel_out})
    results = ig.generate_many(tmp_path, [("a.png", "p")], concurrency=0)
    assert len(results) == 1


def test_analyze_scene_layers_parses(tmp_path, monkeypatch):
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir(); img = proj / "storyboard" / "s.png"; img.write_bytes(b"\x89PNG")

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        from pathlib import Path as _P
        _P(output_last).write_text('{"elements":[{"name":"전기차","location":"왼쪽"},'
                                   '{"name":"인물","location":"오른쪽"}]}', encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(ig.llm, "run_orchestrator", fake_run)
    res = ig.analyze_scene_layers(proj, str(img))
    assert [e["name"] for e in res["elements"]] == ["전기차", "인물"]


def test_analyze_scene_layers_prompt_uses_narration(tmp_path, monkeypatch):
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir(); img = proj / "storyboard" / "s.png"; img.write_bytes(b"\x89PNG")
    cap = {}

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        cap["prompt"] = prompt
        from pathlib import Path as _P
        _P(output_last).write_text('{"elements":[]}', encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(ig.llm, "run_orchestrator", fake_run)
    ig.analyze_scene_layers(proj, str(img), narration="아이가 전기차를 향해 달려간다", context="제목: 의미")
    assert "아이가 전기차를 향해 달려간다" in cap["prompt"]   # 내레이션 주입
    assert "캐릭터" in cap["prompt"]                          # 1순위: 캐릭터 전원
    assert "가리는" in cap["prompt"]                           # 2순위: 전경 가림
    assert "판단 순서" in cap["prompt"]                         # 연출 의도에서 역산하는 판단 순서 명시
    assert "발생(새로 등장)" in cap["prompt"]                   # 내레이션 발생·제거·움직임 사물 분리 기준


def test_archive_prev_layers_moves_not_deletes(tmp_path):
    from backend import imagegen as ig
    lay = tmp_path / "layers"; lay.mkdir()
    (lay / "sid9__0_old.png").write_bytes(b"\x89PNG")
    (lay / "sid9__bg.png").write_bytes(b"\x89PNG")
    (lay / "other__0_x.png").write_bytes(b"\x89PNG")     # 다른 씬 — 유지
    moved = ig._archive_prev_layers(lay, "sid9")
    assert moved == 2
    assert not (lay / "sid9__0_old.png").exists()        # 활성 폴더에서 빠짐
    assert (lay / "_prev" / "sid9__0_old.png").exists()  # 보존됨(무삭제)
    assert (lay / "other__0_x.png").exists()             # 다른 씬 그대로


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _stub_cli(tmp_path, monkeypatch):
    """CLI 경로·키를 모킹해 _run_codex_image가 subprocess 단계까지 진입하게 함."""
    from backend import imagegen as ig
    cli = tmp_path / "image_gen.py"
    cli.write_text("x", encoding="utf-8")
    monkeypatch.setattr(ig, "_CLI_SCRIPT", cli)
    monkeypatch.setattr(ig.env, "get_key", lambda name: "sk-test")
    monkeypatch.setattr(ig.time, "sleep", lambda s: None)
    return ig


def test_run_codex_image_classifies_rate_limit(tmp_path, monkeypatch):
    ig = _stub_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(ig.subprocess, "run",
                        lambda *a, **k: _Proc(1, "openai rate limit exceeded (429)"))
    res = ig._run_codex_image(tmp_path, tmp_path / "x.png", "p", retries=1)
    assert res["status"] == "failed" and res["error"] == "rate_limit"


def test_run_codex_image_classifies_no_file(tmp_path, monkeypatch):
    ig = _stub_cli(tmp_path, monkeypatch)
    monkeypatch.setattr(ig.subprocess, "run", lambda *a, **k: _Proc(0, "done"))
    res = ig._run_codex_image(tmp_path, tmp_path / "x.png", "p", retries=0)
    assert res["status"] == "failed" and res["error"] == "no_file"


def test_run_codex_image_needs_key(tmp_path, monkeypatch):
    from backend import imagegen as ig
    monkeypatch.setattr(ig.env, "get_key", lambda name: "")
    res = ig._run_codex_image(tmp_path, tmp_path / "x.png", "p", retries=0)
    assert res["status"] == "failed" and "OPENAI_API_KEY" in res["error"]


def test_run_codex_image_success(tmp_path, monkeypatch):
    ig = _stub_cli(tmp_path, monkeypatch)
    out = tmp_path / "o.png"

    def fake_run(cmd, **k):
        out.write_bytes(b"\x89PNG-new-image")
        return _Proc(0, "Wrote " + str(out))

    monkeypatch.setattr(ig.subprocess, "run", fake_run)
    res = ig._run_codex_image(tmp_path, out, "p", retries=0)
    assert res["status"] == "completed" and out.exists()


def test_run_codex_image_copy_guard(tmp_path, monkeypatch):
    ig = _stub_cli(tmp_path, monkeypatch)
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"IDENTICAL-BYTES")
    out = tmp_path / "o.png"

    def fake_run(cmd, **k):
        out.write_bytes(b"IDENTICAL-BYTES")  # 첨부와 동일 = 복사
        return _Proc(0, "Wrote")

    monkeypatch.setattr(ig.subprocess, "run", fake_run)
    res = ig._run_codex_image(tmp_path, out, "p", images=[str(ref)], retries=0)
    assert res["status"] == "failed"


def test_run_codex_image_edit_vs_generate(tmp_path, monkeypatch):
    ig = _stub_cli(tmp_path, monkeypatch)
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"REF")
    out = tmp_path / "o.png"
    seen = {}

    def fake_run(cmd, **k):
        seen["cmd"] = cmd
        out.write_bytes(b"\x89PNG-x")
        return _Proc(0, "Wrote")

    monkeypatch.setattr(ig.subprocess, "run", fake_run)
    ig._run_codex_image(tmp_path, out, "p", images=[str(ref)], retries=0)
    assert "edit" in seen["cmd"] and "--image" in seen["cmd"]
    ig._run_codex_image(tmp_path, out, "p", retries=0)
    assert "generate" in seen["cmd"] and "--image" not in seen["cmd"]


def test_gen_semaphore_limits_concurrency(tmp_path, monkeypatch):
    """전역 세마포어 — 동시 codex 이미지 실행이 상한을 넘지 않음(초과분 대기)."""
    import threading, time
    from PIL import Image
    from backend import imagegen as ig
    monkeypatch.setattr(ig, "_GEN_SEMA", threading.BoundedSemaphore(2))
    state = {"cur": 0, "peak": 0}
    lock = threading.Lock()

    def fake_skill(prompt, cwd, **kw):
        with lock:
            state["cur"] += 1
            state["peak"] = max(state["peak"], state["cur"])
        time.sleep(0.05)
        with lock:
            state["cur"] -= 1
        return {"returncode": 1, "output_last": None}     # 파일 미생성 → 즉시 실패 경로

    monkeypatch.setattr(ig, "run_skill", fake_skill)
    outs = [tmp_path / f"o{i}.png" for i in range(6)]
    ts = [threading.Thread(target=lambda o=o: ig._run_codex_image(tmp_path, o, "p", retries=0))
          for o in outs]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert state["peak"] <= 2                              # 상한 준수


def test_split_scene_failed_relayerize_preserves_existing_layers(tmp_path, monkeypatch):
    """발견1 — layerize가 실패하면 아카이브(이동)가 일어나기 전이어야 기존 레이어가 살아남는다."""
    from backend import imagegen as ig, fal_api
    lay = tmp_path / "layers"; lay.mkdir()
    existing_bg = lay / "sid1__bg.png"
    existing_el = lay / "sid1__0_old.png"
    existing_bg.write_bytes(b"\x89PNG-bg")
    existing_el.write_bytes(b"\x89PNG-el")

    def fail_layerize(image_path, names, **kw):
        raise fal_api.FalError("fal 호출 실패: 429")

    monkeypatch.setattr(ig.fal_api, "layerize", fail_layerize)
    img = tmp_path / "scene.png"; img.write_bytes(b"\x89PNG")
    elements = [{"name": "차", "name_en": "car", "kind": "object"}]
    with pytest.raises(fal_api.FalError):
        ig.split_scene_to_elements(tmp_path, str(img), "sid1", elements)
    assert existing_bg.exists()
    assert existing_el.exists()
    assert not (lay / "_prev").exists()   # 아카이브 자체가 일어나지 않았어야 함


def test_regenerate_layer_legacy_sidecar_less_gets_name_en(tmp_path, monkeypatch):
    """발견1 — 사이드카 없는 옛 프로젝트도 name_en이 복원돼 layerize가 실제로 호출된다."""
    from backend import imagegen as ig
    lay = tmp_path / "layers"; lay.mkdir()
    (lay / "sid2__0_red_car.png").write_bytes(b"\x89PNG")
    (lay / "sid2__bg.png").write_bytes(b"\x89PNG-bg")
    img = tmp_path / "scene.png"; img.write_bytes(b"\x89PNG")
    called = {}

    def fake_layerize(image_path, names, **kw):
        called["names"] = list(names)
        return [{"name": None, "z": 0, "bbox": None, "data": b"\x89PNG-newbg"},
                {"name": "red car", "z": 1, "bbox": [0, 0, 10, 10], "data": b"\x89PNG-newcar"}]

    monkeypatch.setattr(ig.fal_api, "layerize", fake_layerize)
    res = ig.regenerate_layer(tmp_path, str(img), "sid2", "sid2__0_red_car")
    assert called["names"] == ["red car"]        # 빈 이름이 아니어야 layerize가 호출됨
    assert res["layer"]["status"] == "completed"


def test_kinds_json_not_overwritten_with_empty(tmp_path, monkeypatch):
    """발견1 — 새로 계산된 kinds가 비어 있으면 기존 kinds.json 내용을 지우지 않는다."""
    from backend import imagegen as ig
    lay = tmp_path / "layers"; lay.mkdir()
    kp = lay / "sid3__kinds.json"
    kp.write_text(json.dumps({"sid3__0_old_char": "character"}), encoding="utf-8")
    img = tmp_path / "scene.png"; img.write_bytes(b"\x89PNG")

    def fake_layerize(image_path, names, **kw):
        # 요청한 이름과 다른 이름을 돌려줘 매칭이 하나도 안 되게(=kinds가 빈 채로 계산됨)
        return [{"name": None, "z": 0, "bbox": None, "data": b"\x89PNG-newbg"},
                {"name": "unrelated", "z": 1, "bbox": [0, 0, 10, 10], "data": b"\x89PNG-x"}]

    monkeypatch.setattr(ig.fal_api, "layerize", fake_layerize)
    elements = [{"name": "차", "name_en": "car", "kind": "object"}]
    ig.split_scene_to_elements(tmp_path, str(img), "sid3", elements)
    kinds = json.loads(kp.read_text(encoding="utf-8"))
    assert kinds == {"sid3__0_old_char": "character"}   # 그대로 보존


def test_style_forbids_grain_texture():
    """스타일 명세 — codex 그레인/노이즈/텍스처 명시 금지(평면 일러스트 화질)."""
    from backend import imagegen
    style = imagegen.load_style().lower()
    for term in ("grain", "noise", "texture", "halftone", "smooth"):
        assert term in style, term


# ── 윈도우에서 이미지 생성이 `no_file` 로만 죽던 것 ────────────────────────
#
# 원인 둘. ① `AK_IMAGE_PYTHON` 만 `os.environ` 으로 읽어 `.env` 값이 안 읽혔다
# (나머지는 전부 `env.get_key`). ② openai 미설치가 `no_file` 로 뭉뚱그려져,
# 무엇이 문제인지 안 알려 주면서 두 번을 더 재시도했다.

def test_image_python_reads_dotenv(monkeypatch):
    """`.env` 에 적은 값이 읽혀야 한다 — 여기만 os.environ 이었다."""
    from backend import env, imagegen
    monkeypatch.setattr(env, "get_key",
                        lambda n: "/opt/py311/bin/python" if n == "AK_IMAGE_PYTHON" else "")
    assert imagegen._image_python() == "/opt/py311/bin/python"


def test_image_python_falls_back_to_current(monkeypatch):
    import sys as _sys
    from backend import env, imagegen
    monkeypatch.setattr(env, "get_key", lambda n: "")
    assert imagegen._image_python() == _sys.executable


def test_openai_missing_detected():
    from backend import imagegen
    assert imagegen._openai_missing(
        "Traceback...\nModuleNotFoundError: No module named 'openai'")
    assert imagegen._openai_missing('ImportError: No module named "openai"')
    assert not imagegen._openai_missing("rate limit exceeded")
    assert not imagegen._openai_missing("")


# ── 코덱스가 딴 데 떨군 그림 거두기 ────────────────────────────────────
#
# `workspace-write` 는 작업 폴더 안에만 쓰게 한다. 백엔드가 `adobe/` 에서
# 도는데 목적지는 `output/…` 이라 그 밖이었다 — 코덱스가 그림을 만들어 놓고
# 「지정 폴더는 쓰기 권한 밖」이라며 자기 작업 폴더에 떨궜고, 우리는
# `no_file` 로 읽었다. 48,306 토큰을 쓰고 만든 그림이었다.

def test_rescue_picks_up_the_stray_file(tmp_path):
    import time as _t
    from backend import imagegen as ig
    out = tmp_path / "dst" / "scene_001.png"
    out.parent.mkdir(parents=True)
    stray = tmp_path / "scene_f14e_bda929.png"
    stray.write_bytes(b"\x89PNG-new")
    since = _t.time() - 1
    got = ig._rescue_image(out, f"완성본은 여기에 저장했습니다: {stray}", since)
    assert got == str(stray)
    assert out.is_file() and out.read_bytes() == b"\x89PNG-new"
    assert not stray.exists()          # 옮긴다 — 사본을 남기지 않는다


def test_rescue_ignores_old_files(tmp_path):
    """**이번에 생긴 것만** 거둔다.

    옛 그림을 집어 오면 「됐다」고 보고하면서 엉뚱한 화면이 들어간다.
    """
    import os, time as _t
    from backend import imagegen as ig
    out = tmp_path / "dst" / "scene_001.png"
    out.parent.mkdir(parents=True)
    old = tmp_path / "dst" / "예전.png"
    old.write_bytes(b"\x89PNG-old")
    os.utime(old, (1, 1))              # 아주 옛날 것으로
    assert ig._rescue_image(out, "", _t.time()) is None
    assert not out.exists()


def test_rescue_returns_none_when_nothing_made(tmp_path):
    import time as _t
    from backend import imagegen as ig
    out = tmp_path / "dst" / "scene_001.png"
    out.parent.mkdir(parents=True)
    assert ig._rescue_image(out, "아무것도 못 만들었습니다", _t.time()) is None


def test_codex_runs_where_it_can_write():
    """**프로젝트 폴더**를 작업 폴더로 준다 — 그래야 샌드박스 안이다.

    목적지 폴더(`images/`)만 주면 좁다. 그림을 그리려면 인물 시트·레이어·앞서
    그린 씬을 읽어야 하는데 그것들은 형제 폴더에 있다.
    """
    from pathlib import Path as _P
    src = (_P(__file__).resolve().parents[1] / "backend" / "imagegen.py").read_text(encoding="utf-8")
    seg = src.split("def _run_codex_imagegen(")[1].split("\ndef ")[0]
    assert "cwd=str(_workspace_for(out))" in seg


def test_workspace_is_the_project_folder(tmp_path):
    from backend import imagegen as ig
    proj = tmp_path / "f772e15c_슬러그"
    (proj / "images").mkdir(parents=True)
    (proj / "scene_specs.json").write_text("{}", encoding="utf-8")
    assert ig._workspace_for(proj / "images" / "scene_001.png") == proj
    # 레이어처럼 더 깊은 자리에서도 같은 뿌리를 찾는다
    (proj / "layers").mkdir()
    assert ig._workspace_for(proj / "layers" / "ab__0.png") == proj


def test_workspace_falls_back_when_no_project(tmp_path):
    """못 찾으면 목적지 폴더로 물러선다 — 저장소 뿌리까지 열어 주지 않는다."""
    from backend import imagegen as ig
    d = tmp_path / "외딴곳"; d.mkdir()
    assert ig._workspace_for(d / "a.png") == d


# ── 사이드카를 되읽지 않는다 ────────────────────────────────────────────
#
# 매니페스트를 한 번 구울 때 `load_element_specs` 가 **씬당 두 번** 불린다
# (`scenes._layer_meta` 와 `manifest._scene_layers`). 142씬이면 284번이고,
# 사이드카가 없는 씬은 폴더를 통째로 다시 훑는다(228번). 1.27초가 0.60초가
# 됐다.
#
# ⚠️ 캐시가 낡은 것을 쥐면 레이어를 새로 뗀 씬이 통째로 빈다. 그래서 키에
# **수정 시각**을 넣는다.

def test_specs_cache_reloads_when_sidecar_changes(tmp_path):
    import json as _j
    from backend import imagegen as ig
    L = tmp_path; sid = "ab"
    fp = L / f"{sid}__elements.json"
    fp.write_text(_j.dumps([{"layer": "ab__0_가", "kind": "object"}]), encoding="utf-8")
    assert [x["layer"] for x in ig.load_element_specs(L, sid)] == ["ab__0_가"]
    # 시각을 확실히 벌린 뒤 바꾼다
    import os, time as _t
    fp.write_text(_j.dumps([{"layer": "ab__0_가"}, {"layer": "ab__1_나"}]), encoding="utf-8")
    os.utime(fp, (_t.time() + 5, _t.time() + 5))
    got = [x["layer"] for x in ig.load_element_specs(L, sid)]
    assert got == ["ab__0_가", "ab__1_나"], "사이드카가 바뀌었는데 옛 목록을 줬다"


def test_specs_cache_reloads_when_layer_added(tmp_path):
    """사이드카가 없는 길도 낡으면 안 된다 — 폴더 시각을 키로 쓴다."""
    import os, time as _t
    from PIL import Image
    from backend import imagegen as ig
    L = tmp_path / "layers"; L.mkdir()
    (L / "ab__kinds.json").write_text("{}", encoding="utf-8")
    Image.new("RGBA", (4, 4)).save(L / "ab__0_가.png")
    assert len(ig.load_element_specs(L, "ab")) == 1
    Image.new("RGBA", (4, 4)).save(L / "ab__1_나.png")
    os.utime(L, (_t.time() + 5, _t.time() + 5))
    assert len(ig.load_element_specs(L, "ab")) == 2, "레이어가 늘었는데 옛 목록을 줬다"


def test_specs_cache_actually_caches(tmp_path):
    """같은 상태면 파일을 다시 읽지 않는다."""
    import json as _j
    from backend import imagegen as ig
    fp = tmp_path / "ab__elements.json"
    fp.write_text(_j.dumps([{"layer": "ab__0_가"}]), encoding="utf-8")
    a = ig.load_element_specs(tmp_path, "ab")
    b = ig.load_element_specs(tmp_path, "ab")
    assert a is b            # 같은 객체 — 다시 파싱하지 않았다
