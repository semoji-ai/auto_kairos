import json
from pathlib import Path
from backend.router import handle_request
from backend.jobs import JobRegistry

ROOT = Path(__file__).resolve().parents[1] / "projects"


def _ctx():
    return {"root": ROOT, "jobs": JobRegistry()}


def _poll(ctx, body):
    """비동기 응답 검증 + 잡 폴링 → 완료된 job dict 반환."""
    import time
    assert body["status"] == "running" and body["job_id"]
    jid = body["job_id"]
    for _ in range(200):
        _, jb = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
        if jb["status"] != "running":
            return jb
        time.sleep(0.02)
    raise AssertionError("job timeout")


def test_health():
    code, body = handle_request("GET", "/health", {}, None, _ctx())
    assert code == 200
    assert body["backend_status"] == "connected"


def test_health_includes_root(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/health", {}, None, ctx)
    assert code == 200 and body["root"] == str(tmp_path)


def test_projects_list():
    code, body = handle_request("GET", "/api/projects", {}, None, _ctx())
    assert code == 200
    assert any(p["project_id"] == "demo01" for p in body["projects"])


def test_project_load():
    code, body = handle_request("POST", "/api/projects/load", {},
                                {"project_id": "demo01"}, _ctx())
    assert code == 200
    assert body["project_id"] == "demo01"


def test_unknown_404():
    code, body = handle_request("GET", "/nope", {}, None, _ctx())
    assert code == 404


def test_skills_run_returns_job_id(monkeypatch, tmp_path):
    import backend.router as r
    proj = tmp_path / "demoX"
    proj.mkdir()
    (proj / "final_manuscript.md").write_text("원고 텍스트.", encoding="utf-8")

    def fake_run(prompt, cwd, **kw):
        out = kw.get("output_last")
        if out:
            from pathlib import Path as _P
            _P(out).write_text(
                '{"version":"adobe-0.1","project_id":"demoX","total_scenes":0,"scenes":[]}',
                encoding="utf-8")
        return {"returncode": 0, "session_id": "sess-1", "output_last": out}

    monkeypatch.setattr(r.llm, "run_orchestrator", fake_run)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/skills/run", {},
                                {"project_id": "demoX", "skill_name": "scene-decompose"}, ctx)
    assert code == 200
    jid = body["job_id"]
    code2, jbody = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
    assert code2 == 200
    assert jbody["status"] == "completed"
    assert any("scenes.json" in a for a in jbody["artifact_paths"])


def test_skills_run_missing_manuscript_422(tmp_path):
    proj = tmp_path / "noman"
    proj.mkdir()
    (proj / "plan.md").write_text("# 제목", encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/skills/run", {},
                                {"project_id": "noman", "skill_name": "scene-decompose"}, ctx)
    assert code == 422
    assert "final_manuscript.md" in body["error"]


def test_projects_file_returns_manuscript():
    ctx = _ctx()
    code, body = handle_request("GET", "/api/projects/file",
                                {"project_id": "demo01", "name": "final_manuscript.md"}, None, ctx)
    assert code == 200
    assert body["name"] == "final_manuscript.md"
    assert "카지노" in body["content"]


def test_projects_file_rejects_traversal():
    ctx = _ctx()
    code, body = handle_request("GET", "/api/projects/file",
                                {"project_id": "demo01", "name": "../../backend/app.py"}, None, ctx)
    assert code == 400


def test_projects_file_404_missing():
    ctx = _ctx()
    code, body = handle_request("GET", "/api/projects/file",
                                {"project_id": "demo01", "name": "nope.md"}, None, ctx)
    assert code == 404


def test_projects_file_rejects_absolute(tmp_path):
    proj = tmp_path / "p1"; proj.mkdir()
    (proj / "final_manuscript.md").write_text("원고", encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects/file",
                                {"project_id": "p1", "name": "/etc/hosts"}, None, ctx)
    assert code == 400


def test_images_generate_from_references(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "references.json").write_text(
        '{"project_id":"p","references":[{"id":"ref_1","subject":"차","image_prompt":"전기차"}]}',
        encoding="utf-8")

    def fake_gen(proj_dir, rel_out, image_prompt, **kw):
        out = proj_dir / "images" / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_gen)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/images/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 200
    jb = _poll(ctx, body)
    assert jb["status"] == "completed" and jb["result"]["generated"] == 1


def test_characters_generate(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()

    def fake_char(proj_dir, name, looks, **kw):
        out = proj_dir / "characters" / f"char_{name}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_character", fake_char)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/characters/generate", {},
                                {"project_id": "p", "name": "지오", "looks": "갈색 머리"}, ctx)
    assert code == 200
    assert body["character"]["status"] == "completed"
    assert (proj / "characters" / "char_지오.png").exists()


def test_characters_generate_requires_fields(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/characters/generate", {},
                                {"project_id": "p", "name": "지오"}, ctx)
    assert code == 400


def test_characters_list(tmp_path):
    proj = tmp_path / "p"; (proj / "characters").mkdir(parents=True)
    (proj / "characters" / "char_지오.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/characters/list",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    assert "char_지오.png" in body["images"]


def test_storyboard_passes_character_ref(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sidAA001","image_prompt":"장면1"}]}', encoding="utf-8")
    (proj / "characters").mkdir()
    (proj / "characters" / "char_지오.png").write_bytes(b"\x89PNG")
    seen = {}

    def fake_many(proj_dir, items, *, subdir="images", concurrency=4, on_event=None, character_ref=None):
        seen["character_ref"] = character_ref
        return {rel: {"status": "completed"} for rel, _ in items}

    monkeypatch.setattr(r.imagegen, "generate_many", fake_many)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/storyboard/generate", {},
                                {"project_id": "p", "character": "지오"}, ctx)
    assert code == 200
    jb = _poll(ctx, body)
    assert jb["status"] == "completed"
    assert seen["character_ref"] == str(proj / "characters" / "char_지오.png")


def test_images_list(tmp_path):
    proj = tmp_path / "p"; (proj / "images").mkdir(parents=True)
    (proj / "images" / "ref_1.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/images/list",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    assert "ref_1.png" in body["images"]


def test_storyboard_generate_from_scenes(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"project_id":"p","total_scenes":2,"scenes":['
        '{"sceneNumber":1,"sceneId":"sidB0001","title":"A","narration":"가","image_prompt":"장면1"},'
        '{"sceneNumber":2,"sceneId":"sidB0002","title":"B","narration":"나","image_prompt":"장면2"}]}',
        encoding="utf-8")

    def fake_gen(proj_dir, rel_out, image_prompt, **kw):
        assert kw.get("subdir") == "storyboard"
        out = proj_dir / "storyboard" / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_gen)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/storyboard/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 200
    jb = _poll(ctx, body)
    assert jb["status"] == "completed" and jb["result"]["generated"] == 2


def test_storyboard_generate_requires_scenes(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/storyboard/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 422


def test_storyboard_list(tmp_path):
    proj = tmp_path / "p"; (proj / "storyboard").mkdir(parents=True)
    (proj / "storyboard" / "sb_1.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/storyboard/list",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    assert "sb_1.png" in body["images"]


def test_projects_create(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/create", {},
                                {"title": "새 영상", "channel": "semoji", "duration": "1분"}, ctx)
    assert code == 200
    pid = body["project_id"]
    assert (tmp_path / pid / "plan.md").exists()


def test_projects_create_requires_title(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/create", {}, {"title": ""}, ctx)
    assert code == 400


def test_projects_files_list(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("기획", encoding="utf-8")
    (proj / "final_manuscript.md").write_text("원고", encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects/files",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    labels = [g["label"] for g in body["groups"]]
    assert "기획" in labels and "원고" in labels


def test_projects_files_missing_project(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects/files",
                                {"project_id": "nope"}, None, ctx)
    assert code == 200
    assert body["groups"] == []


def test_scenes_get(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"project_id":"p","scenes":[{"sceneNumber":1,"title":"A","narration":"가","image_prompt":"장면1"}]}',
        encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/scenes", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["scenes"][0]["sceneNumber"] == 1
    assert body["dir"] == str(proj)


def test_scenes_update_narration(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"narration":"옛","image_prompt":"x"}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/narration", {},
                                {"project_id": "p", "sceneNumber": 1, "narration": "새"}, ctx)
    assert code == 200 and body["ok"] is True
    import json as _j
    assert _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]["narration"] == "새"


def test_scenes_image_sets_imageref(tmp_path, monkeypatch):
    import json as _j
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":3,"sceneId":"sid333","image_prompt":"전기차 공장"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt)
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 3}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"].startswith("scene_sid333_") and seen["subdir"] == "storyboard"
    sc = _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == "storyboard/" + seen["rel_out"]   # 생성 후 링크됨


def test_scenes_unlink_image(tmp_path):
    import json as _j
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"s1","imageRef":"images/a.png"}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/unlink-image", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["ok"] is True
    sc = _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == ""


def test_scenes_image_unknown_scene(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 9}, ctx)
    assert code == 404


def test_media_list(tmp_path):
    proj = tmp_path / "p"; (proj / "images").mkdir(parents=True)
    (proj / "images" / "a.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/media", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["items"][0]["rel"] == "images/a.png"


def test_search_images_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    monkeypatch.setattr(r.search, "search_images",
                        lambda q, engine="serper", count=12: {"images": [{"url": "u", "thumb": "t", "title": "x", "source": engine}]})
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/search-images",
                                {"project_id": "p", "q": "전기차", "engine": "serper"}, None, ctx)
    assert code == 200 and body["images"][0]["url"] == "u"


def test_search_images_requires_query(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/search-images",
                                {"project_id": "p", "q": ""}, None, ctx)
    assert code == 400


def test_search_save_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    monkeypatch.setattr(r.search, "save_image",
                        lambda proj_dir, url, name, **kw: {"status": "completed", "rel": "images/search/x.jpg"})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/search-images/save", {},
                                {"project_id": "p", "url": "http://x/a.jpg", "name": "x.jpg"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"


def test_scene_set_image_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    monkeypatch.setattr(r.media, "set_scene_image",
                        lambda proj_dir, n, src: {"status": "completed", "rel": f"storyboard/sb_{n}.png"})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/set-image", {},
                                {"project_id": "p", "sceneNumber": 2, "src": "images/a.png"}, ctx)
    assert code == 200 and body["result"]["rel"] == "storyboard/sb_2.png"


def test_assets_generate_background(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    seen = {}

    def fake_asset(proj_dir, rel_out, image_prompt, *, char_ref=None, subdir="images", **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt, char_ref=char_ref)
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_asset", fake_asset)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "background", "prompt": "작업실 배경"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"].startswith("background_") and seen["subdir"] == "images"
    assert seen["char_ref"] is None        # 캐릭터 미지정


def test_assets_generate_with_character_style(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "characters").mkdir(); (proj / "characters" / "char_지오.png").write_bytes(b"\x89PNG")
    seen = {}

    def fake_asset(proj_dir, rel_out, image_prompt, *, char_ref=None, subdir="images", **kw):
        seen["char_ref"] = char_ref
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_asset", fake_asset)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "prop", "prompt": "렌치", "character": "지오"}, ctx)
    assert code == 200
    assert seen["char_ref"] == str(proj / "characters" / "char_지오.png")


def test_assets_generate_requires_prompt(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "prop", "prompt": ""}, ctx)
    assert code == 400


def test_assets_generate_bad_category(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "scene", "prompt": "x"}, ctx)
    assert code == 400        # background/prop만 허용(scene/character는 전용 엔드포인트)


def test_scenes_analyze_layers(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","imageRef":"storyboard/sb_sa.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb_sa.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(r.imagegen, "analyze_scene_layers",
                        lambda proj_dir, img, **kw: {"elements": [{"name": "차", "location": "왼쪽"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/analyze-layers", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["elements"][0]["name"] == "차"


def test_scenes_analyze_layers_no_image(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","imageRef":""}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/analyze-layers", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 422       # 씬 이미지 없음


def test_scenes_split_layers(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sb1","imageRef":"storyboard/sb_sb1.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb_sb1.png").write_bytes(b"\x89PNG")
    seen = {}
    monkeypatch.setattr(r.imagegen, "split_scene_to_elements",
                        lambda proj_dir, img, sid, elements, **kw: seen.update(sid=sid, n=len(elements)) or {"layers": [{"rel": "layers/sb1__0_x.png", "status": "completed"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split-layers", {},
                                {"project_id": "p", "sceneNumber": 1,
                                 "elements": [{"name": "차", "location": "왼쪽"}]}, ctx)
    assert code == 200
    jb = _poll(ctx, body)
    assert jb["status"] == "completed"
    assert seen["sid"] == "sb1" and seen["n"] == 1
    assert jb["result"]["result"]["layers"][0]["rel"].startswith("layers/sb1__")


def test_scenes_image_prompt_override(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sx","image_prompt":"기본"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen["prompt"] = image_prompt
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 1, "prompt": "오버라이드 프롬프트"}, ctx)
    assert code == 200 and seen["prompt"] == "오버라이드 프롬프트"


def _mk_scenes(tmp_path, arr):
    import json as _j
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(_j.dumps({"scenes": arr}, ensure_ascii=False), encoding="utf-8")
    return proj


def test_scenes_add(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/add", {},
                                {"project_id": "p", "after": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 2


def test_scenes_delete(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}, {"sceneNumber": 2, "sceneId": "b"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/delete", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and [s["sceneId"] for s in body["scenes"]] == ["b"]


def test_scenes_split(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "하나다. 둘이다."}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 2


def test_scenes_merge(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "앞"},
                          {"sceneNumber": 2, "sceneId": "b", "narration": "뒤"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/merge", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 1


def test_scenes_add_missing_project_404(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/scenes/add", {}, {"project_id": "none"}, ctx)
    assert code == 404


def test_scenes_tts(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","narration":"안녕"}]}', encoding="utf-8")
    monkeypatch.setattr(r.tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: {"status": "completed", "rel": f"audio/tts_{sid}.wav", "duration": 1.0})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/tts", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["result"]["rel"] == "audio/tts_sa.wav"


def test_scenes_tts_no_narration_422(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","narration":""}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/scenes/tts", {},
                             {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 422


def test_assembly_manifest(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.manifest, "build_manifest",
                        lambda proj_dir, only_scene=None, only_scenes=None: {
                            "path": str(proj_dir / "manifest.json"), "scenes": 0,
                            "only_scene": only_scene, "only_scenes": only_scenes})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assembly/manifest", {}, {"project_id": "p"}, ctx)
    assert code == 200 and body["path"].endswith("manifest.json") and body["only_scene"] is None


def test_assembly_manifest_single_scene(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.manifest, "build_manifest",
                        lambda proj_dir, only_scene=None, only_scenes=None: {
                            "path": "x", "scenes": 1,
                            "only_scene": only_scene, "only_scenes": only_scenes})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assembly/manifest", {},
                                {"project_id": "p", "sceneNumber": 3}, ctx)
    assert code == 200 and body["only_scene"] == 3


def test_scenes_motion(tmp_path, monkeypatch):
    import time, backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"mt"}]}', encoding="utf-8")
    monkeypatch.setattr(r.motion, "plan_scene_motion",
                        lambda proj_dir, sn, on_line=None: {"layers": [], "camera": {"type": "none"}})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/motion", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["status"] == "running"          # 비동기 전환
    jid = body["job_id"]
    for _ in range(100):
        _, jb = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
        if jb["status"] != "running":
            break
        time.sleep(0.02)
    assert jb["status"] == "completed"
    assert jb["result"]["plan"]["camera"]["type"] == "none"


def test_scenes_motion_error_failed_job(tmp_path, monkeypatch):
    import time, backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    monkeypatch.setattr(r.motion, "plan_scene_motion",
                        lambda proj_dir, sn, on_line=None: {"error": "레이어 없음"})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/motion", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["status"] == "running"
    jid = body["job_id"]
    for _ in range(100):
        _, jb = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
        if jb["status"] != "running":
            break
        time.sleep(0.02)
    assert jb["status"] == "failed" and "레이어 없음" in jb["error"]


def test_assistant_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.assistant, "run_assistant",
                        lambda proj_dir, instr, on_event=None, should_cancel=None: {
                            "plan": [{"action": "assemble", "reason": "x"}],
                            "results": [{"action": "assemble", "reason": "x", "result": {"scenes": 0}}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assistant", {},
                                {"project_id": "p", "instruction": "합쳐줘"}, ctx)
    assert code == 200
    jb = _poll(ctx, body)
    assert jb["status"] == "completed"
    assert jb["result"]["plan"][0]["action"] == "assemble"
    assert jb["result"]["results"][0]["result"]["scenes"] == 0


def test_assistant_requires_instruction(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/assistant", {}, {"project_id": "p"}, ctx)
    assert code == 400


def test_assistant_missing_project_404(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/assistant", {},
                             {"project_id": "none", "instruction": "x"}, ctx)
    assert code == 404


def test_tts_settings_get_default(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/tts/settings", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["config"]["style"] == "semoji"
    assert body["config"]["voice_id"] == "W7FnAxJNpD5WGjrF5GLp"
    assert "semoji" in body["presets"]["presets"]


def test_tts_settings_post_style(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/tts/settings", {},
                                {"project_id": "p", "style": "lego"}, ctx)
    assert code == 200 and body["config"]["voice_id"] == "4JJwo477JUAx3HV0T7n7"


def test_tts_settings_post_voice_override(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/tts/settings", {},
                                {"project_id": "p", "voice_id": "ZZZ999"}, ctx)
    assert code == 200 and body["config"]["voice_id"] == "ZZZ999"


def test_llm_settings_get_default(tmp_path, monkeypatch):
    import backend.router as r, backend.llm as L
    monkeypatch.setattr(L, "_CFG", tmp_path / "llm.json")
    monkeypatch.delenv("AK_ORCHESTRATOR", raising=False)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/llm/settings", {}, None, ctx)
    assert code == 200 and body["orchestrator"] == "claude" and "claude" in body["choices"]


def test_llm_settings_post(tmp_path, monkeypatch):
    import backend.llm as L
    monkeypatch.setattr(L, "_CFG", tmp_path / "llm.json")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/llm/settings", {}, {"orchestrator": "codex"}, ctx)
    assert code == 200 and body["orchestrator"] == "codex"


def test_handler_exception_returns_500(tmp_path, monkeypatch):
    import backend.router as r
    def boom(root): raise RuntimeError("내부 오류")
    monkeypatch.setattr(r.projects, "scan_projects", boom)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects", {}, None, ctx)
    assert code == 500 and "error" in body


def test_split_layers_returns_running_then_completes(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"as1","imageRef":"storyboard/sb.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(r.imagegen, "split_scene_to_elements",
                        lambda *a, **k: {"layers": [{"rel": "layers/x.png", "status": "completed"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split-layers", {},
                                {"project_id": "p", "sceneNumber": 1,
                                 "elements": [{"name": "차", "location": "왼쪽"}]}, ctx)
    assert code == 200 and body["status"] == "running" and body["job_id"]
    jb = _poll(ctx, body)
    assert jb["status"] == "completed"
    assert jb["result"]["result"]["layers"][0]["status"] == "completed"


def test_assistant_async(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.assistant, "run_assistant",
                        lambda proj_dir, instr, on_event=None, should_cancel=None: {"plan": [], "results": []})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assistant", {},
                                {"project_id": "p", "instruction": "x"}, ctx)
    assert code == 200 and body["status"] == "running"
    jb = _poll(ctx, body)
    assert jb["status"] == "completed" and jb["result"] == {"plan": [], "results": []}


def test_scenes_tts_prefers_narration_tts(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"nt","narration":"원문","narration_tts":"교정본"}]}',
        encoding="utf-8")
    seen = {}
    monkeypatch.setattr(r.tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: seen.update(text=text) or
                        {"status": "completed", "rel": "audio/x.mp3", "duration": 1.0})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    handle_request("POST", "/api/scenes/tts", {}, {"project_id": "p", "sceneNumber": 1}, ctx)
    assert seen["text"] == "교정본"


def test_tts_all_prefers_narration_tts(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"nt","narration":"원문","narration_tts":"교정본"}]}',
        encoding="utf-8")
    seen = []
    monkeypatch.setattr(r.tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: seen.append(text) or
                        {"status": "completed", "rel": "audio/x.mp3", "duration": 1.0})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    _, body = handle_request("POST", "/api/tts/all", {}, {"project_id": "p"}, ctx)
    _poll(ctx, body)
    assert seen == ["교정본"]


def test_import_v3_route(tmp_path):
    v3 = tmp_path / "uuidabcd_topic"; v3.mkdir()
    (v3 / "scene_specs.json").write_text(
        '{"scenes":[{"sceneNumber":1,"title":"t","narration":"n"}]}', encoding="utf-8")
    ctx = {"root": tmp_path / "root", "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/import-v3", {}, {"path": str(v3)}, ctx)
    assert code == 200 and body["project_id"] and body["scenes"] == 1


def test_import_v3_route_no_path_400(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/projects/import-v3", {}, {}, ctx)
    assert code == 400


def test_import_v3_route_bad_dir_422(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/import-v3", {},
                                {"path": str(tmp_path / "nope")}, ctx)
    assert code == 422 and "error" in body


def test_file_save_records_edit(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("이전", encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/file/save", {},
                                {"project_id": "p", "name": "plan.md", "content": "이후"}, ctx)
    assert code == 200 and body["ok"]
    assert (proj / "edits_log.jsonl").exists()


def test_file_save_rejects_bad_path(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/projects/file/save", {},
                             {"project_id": "p", "name": "../x.md", "content": "x"}, ctx)
    assert code == 400


def test_subtitles_build_endpoint(monkeypatch, tmp_path):
    import backend.router as r
    proj = tmp_path / "demoS"
    proj.mkdir()
    called = {}

    def fake_build(proj_dir, only_scenes=None):
        called["dir"] = str(proj_dir)
        called["only_scenes"] = only_scenes
        return {"json": str(proj_dir / "subtitles.json"), "srt": str(proj_dir / "subtitles.srt"),
                "lines": 7, "scenes_no_ts": [2]}

    monkeypatch.setattr(r.subtitles, "build_subtitles", fake_build)
    monkeypatch.setattr(r.vault, "log_work", lambda *a, **k: None)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/subtitles/build", {},
                                {"project_id": "demoS"}, ctx)
    assert code == 200 and body["lines"] == 7 and body["scenes_no_ts"] == [2]
    assert called["only_scenes"] is None
    handle_request("POST", "/api/subtitles/build", {},
                   {"project_id": "demoS", "sceneNumbers": [2, 5]}, ctx)
    assert called["only_scenes"] == [2, 5]      # 체크한 씬만 빌드
    assert called["dir"] == str(proj)
    assert body["ae_tokens"].endswith("ae_tokens.json")     # manifest와 동일 토큰 경로


def test_subtitles_build_404():
    code, body = handle_request("POST", "/api/subtitles/build", {},
                                {"project_id": "no_such"}, _ctx())
    assert code == 404


def test_tokens_endpoint(tmp_path):
    """GET /api/tokens — 디자인 토큰(시트 미리보기용) 반환."""
    from backend import router
    st, res = router.handle_request("GET", "/api/tokens", {}, None, {"root": tmp_path})
    assert st == 200
    assert res.get("fonts", {}).get("body") == "OTSBAggroM"
    assert "colors" in res and "type" in res


def test_map_image_save(tmp_path):
    """POST /api/scenes/map-image — dataURL PNG 저장(버전 파일명) + imageRef 링크."""
    import base64, json as _json
    from backend import router
    from PIL import Image
    import io
    d = tmp_path / "p1"; d.mkdir()
    (d / "scenes.json").write_text(_json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "mm", "narration": "x"}]}), encoding="utf-8")
    buf = io.BytesIO(); Image.new("RGB", (4, 4)).save(buf, "PNG")
    du = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    st, res = router.handle_request("POST", "/api/scenes/map-image", {},
        {"project_id": "p1", "sceneNumber": 1, "dataUrl": du}, {"root": tmp_path})
    assert st == 200 and res.get("ok")
    assert res["imageRef"].startswith("storyboard/map_mm_")
    assert (d / res["imageRef"]).is_file()
    # geo 사이드카 미전송 시 생성 안 됨
    assert not list((d / "storyboard").glob("*.geo.json"))
    # 형식 오류 거부
    st2, res2 = router.handle_request("POST", "/api/scenes/map-image", {},
        {"project_id": "p1", "sceneNumber": 1, "dataUrl": "data:image/jpeg;base64,xx"}, {"root": tmp_path})
    assert st2 == 400


def test_tokens_has_map_theme():
    """ae_tokens.map.defaultTheme — 모던 클린(사용자 선택)."""
    from backend import router
    from pathlib import Path
    st, res = router.handle_request("GET", "/api/tokens", {}, None, {"root": Path(".")})
    assert res.get("map", {}).get("defaultTheme") == "clean_white"


def test_map_image_save_with_geo(tmp_path):
    """geo 동봉 시 {이미지}.geo.json 사이드카 저장."""
    import base64, json as _json, io
    from backend import router
    from PIL import Image
    d = tmp_path / "p2"; d.mkdir()
    (d / "scenes.json").write_text(_json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "gg", "narration": "x"}]}), encoding="utf-8")
    buf = io.BytesIO(); Image.new("RGB", (4, 4)).save(buf, "PNG")
    du = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    geo = {"markers": [{"name": "부산", "x": 1, "y": 2}], "route": [], "labelRgb": [26, 26, 26]}
    st, res = router.handle_request("POST", "/api/scenes/map-image", {},
        {"project_id": "p2", "sceneNumber": 1, "dataUrl": du, "geo": geo}, {"root": tmp_path})
    assert st == 200
    gp = d / (res["imageRef"] + ".geo.json")
    assert gp.is_file() and _json.loads(gp.read_text())["markers"][0]["name"] == "부산"


def test_chart_spec_endpoint(tmp_path, monkeypatch):
    """POST /api/scenes/chart-spec — chartagent 호출(스텁) → 사이드카 + 토큰 반환."""
    import json as _json
    from backend import router, chartgen
    d = tmp_path / "pc"; d.mkdir()
    (d / "scenes.json").write_text(_json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "cs", "layout": "bar", "headline": "t",
         "chart": {"labels": ["a", "b"], "values": [1, 2], "unit": "분"}}]}), encoding="utf-8")
    monkeypatch.setattr(chartgen, "available", lambda: True)
    def fake_gen(proj_dir, scene):
        (proj_dir / "chart_cs.spec.json").write_text("{}", encoding="utf-8")
        return {"ok": True, "tokens": {"guideLineCount": 2}, "theme_set": "gallery_infographic"}
    monkeypatch.setattr(chartgen, "gen_chart_spec", fake_gen)
    st, res = router.handle_request("POST", "/api/scenes/chart-spec", {},
        {"project_id": "pc", "sceneNumber": 1}, {"root": tmp_path})
    assert st == 200 and res.get("ok") and res["theme_set"] == "gallery_infographic"
    assert (d / "chart_cs.spec.json").is_file()

def test_themes_endpoints(tmp_path, monkeypatch):
    """GET /api/themes 목록 + set-project/set-scene."""
    import json
    from backend import router, themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "semoji.json").write_text(json.dumps({"id": "semoji", "label": "세모지",
        "colors": {}, "chart": {"theme_set": "gallery_infographic"}, "map": {"tile": "bright", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    st, res = router.handle_request("GET", "/api/themes", {}, None, {"root": tmp_path})
    assert st == 200 and any(t["id"] == "semoji" for t in res["themes"])
    d = tmp_path / "p1"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": [{"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    st, res = router.handle_request("POST", "/api/themes/set-project", {},
        {"project_id": "p1", "theme_id": "semoji"}, {"root": tmp_path})
    assert st == 200 and res["theme"] == "semoji"
    st, res = router.handle_request("POST", "/api/themes/set-scene", {},
        {"project_id": "p1", "sceneNumber": 1, "theme_id": "semoji"}, {"root": tmp_path})
    assert st == 200 and res["themeOverride"] == "semoji"


def test_pipeline_status_reports_stage_done(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    proj = tmp_path / "p1"
    (proj / "strategy").mkdir(parents=True)
    (proj / "strategy" / "options.md").write_text("x", encoding="utf-8")
    code, body = handle_request("GET", "/api/pipeline/status",
                                {"project_id": "p1"}, None, ctx)
    assert code == 200
    names = [s["name"] for s in body["stages"]]
    from backend.pipeline import PIPELINE
    assert names == PIPELINE
    by = {s["name"]: s for s in body["stages"]}
    assert by["plan-explore"]["done"] is True
    assert by["deep-research"]["done"] is False


def test_pipeline_status_project_not_found(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("GET", "/api/pipeline/status",
                             {"project_id": "nope"}, None, ctx)
    assert code == 404


def test_pipeline_run_stage_rejects_unknown_stage(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    (tmp_path / "p1").mkdir()
    code, body = handle_request("POST", "/api/pipeline/run-stage", {},
                                {"project_id": "p1", "stage": "hack"}, ctx)
    assert code == 400


def test_pipeline_run_stage_project_not_found(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/pipeline/run-stage", {},
                             {"project_id": "nope", "stage": "plan-explore"}, ctx)
    assert code == 404


def _tmp_ctx(tmp_path, scenes_list):
    proj = tmp_path / "p1"
    (proj / "audio").mkdir(parents=True)
    (proj / "scenes.json").write_text(json.dumps({"scenes": scenes_list}, ensure_ascii=False),
                                      encoding="utf-8")
    return {"root": tmp_path, "jobs": JobRegistry()}


def test_scenes_texts_endpoint(tmp_path):
    ctx = _tmp_ctx(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "원고"}])
    code, body = handle_request("POST", "/api/scenes/texts", {},
                                {"project_id": "p1", "sceneNumber": 1,
                                 "narration_tts": "발음", "subtitle_text": "자막"}, ctx)
    assert code == 200 and body["ok"]
    d = json.loads((tmp_path / "p1" / "scenes.json").read_text(encoding="utf-8"))
    assert d["scenes"][0]["narration_tts"] == "발음"
    assert d["scenes"][0]["subtitle_text"] == "자막"
    code, _ = handle_request("POST", "/api/scenes/texts", {},
                             {"project_id": "없음", "sceneNumber": 1}, ctx)
    assert code == 404


def test_assembly_manifest_scene_list(tmp_path, monkeypatch):
    """체크한 씬 여러 개 — 한 번의 호출로 목록을 넘긴다."""
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.manifest, "build_manifest",
                        lambda proj_dir, only_scene=None, only_scenes=None: {
                            "path": "x", "scenes": len(only_scenes or []),
                            "only_scene": only_scene, "only_scenes": only_scenes})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assembly/manifest", {},
                                {"project_id": "p", "sceneNumbers": [1, 4, 9]}, ctx)
    assert code == 200 and body["only_scenes"] == [1, 4, 9] and body["scenes"] == 3


def test_job_cancel_endpoint(tmp_path):
    """긴 작업을 패널에서 멈출 수 있어야 한다(예전엔 백엔드 프로세스를 죽이는 수밖에 없었음)."""
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    jid = ctx["jobs"].create("assistant", "p")
    code, body = handle_request("POST", f"/api/jobs/{jid}/cancel", {}, None, ctx)
    assert code == 200 and body["status"] == "cancelling"
    assert ctx["jobs"].is_cancelled(jid) is True
    code, _ = handle_request("POST", "/api/jobs/job_9999/cancel", {}, None, ctx)
    assert code == 404


def test_running_jobs_endpoint(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    jid = ctx["jobs"].create("assistant", "p")
    code, body = handle_request("GET", "/api/jobs", {"project_id": "p"}, None, ctx)
    assert code == 200 and [j["job_id"] for j in body["running"]] == [jid]
    ctx["jobs"].set_status(jid, "completed")
    _, body2 = handle_request("GET", "/api/jobs", {"project_id": "p"}, None, ctx)
    assert body2["running"] == []


def _layer_proj(tmp_path):
    proj = tmp_path / "lp"
    (proj / "layers").mkdir(parents=True)
    (proj / "storyboard").mkdir()
    (proj / "storyboard" / "sb_ab.png").write_bytes(b"\x89PNG")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "ab", "imageRef": "storyboard/sb_ab.png"}]}), encoding="utf-8")
    for nm in ("ab__0_인물.png", "ab__1_탁자.png", "ab__bg.png"):
        (proj / "layers" / nm).write_bytes(b"\x89PNG")
    return proj


def test_layers_regenerate_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    _layer_proj(tmp_path)
    monkeypatch.setattr(r.imagegen, "regenerate_layer",
                        lambda *a, **k: {"layer": {"name": "인물", "status": "completed"}})
    monkeypatch.setattr(r.vault, "log_work", lambda *a, **k: None)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/layers/regenerate", {},
                                {"project_id": "lp", "sceneNumber": 1, "layer": "ab__0_인물"}, ctx)
    assert code == 200 and body["status"] == "running"
    jb = _poll(ctx, body)
    assert jb["status"] == "completed"


def test_layers_endpoints_validate_input(tmp_path):
    _layer_proj(tmp_path)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/layers/regenerate", {},
                             {"project_id": "lp", "sceneNumber": 1}, ctx)
    assert code == 400                                          # layer 누락
    code, _ = handle_request("POST", "/api/layers/regenerate", {},
                             {"project_id": "lp", "sceneNumber": 99, "layer": "x"}, ctx)
    assert code == 404                                          # 씬 없음
