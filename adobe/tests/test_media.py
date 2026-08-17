from backend import media


def test_list_media(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "images").mkdir(); (p / "images" / "ref_1.png").write_bytes(b"\x89PNG")
    (p / "images" / "search").mkdir(); (p / "images" / "search" / "s.jpg").write_bytes(b"x")
    (p / "storyboard").mkdir(); (p / "storyboard" / "sb_1.png").write_bytes(b"x")
    (p / "video_sources").mkdir(); (p / "video_sources" / "v.mp4").write_bytes(b"x")
    items = media.list_media(p)
    rels = {i["rel"]: i["type"] for i in items}
    assert rels["images/ref_1.png"] == "image"
    assert rels["images/search/s.jpg"] == "image"
    assert rels["storyboard/sb_1.png"] == "image"
    assert rels["video_sources/v.mp4"] == "video"
    assert all(i["dir"] == str(p) for i in items)


def test_set_scene_image_links_no_copy(tmp_path):
    import json as _j
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":2,"sceneId":"s2","image_prompt":"x"}]}', encoding="utf-8")
    (p / "images").mkdir(); (p / "images" / "pick.png").write_bytes(b"\x89PNG")
    res = media.set_scene_image(p, 2, "images/pick.png")
    assert res["ok"] is True
    sc = _j.loads((p / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == "images/pick.png"        # 링크만
    assert not (p / "storyboard").exists()            # 복사 안 함


def test_set_scene_image_rejects_traversal(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"s1"}]}', encoding="utf-8")
    assert "error" in media.set_scene_image(p, 1, "../../etc/hosts")


def test_set_scene_image_missing_src(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"s1"}]}', encoding="utf-8")
    assert "error" in media.set_scene_image(p, 1, "images/nope.png")
