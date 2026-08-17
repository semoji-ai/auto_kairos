from backend import search


def test_search_serper(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY" if k == "SERPER_API_KEY" else "")
    monkeypatch.setattr(search, "_post_json",
        lambda url, payload, headers, timeout=20: {"images": [
            {"title": "차", "imageUrl": "http://x/a.jpg", "thumbnailUrl": "http://x/t.jpg"}]})
    res = search.search_images("전기차", engine="serper")
    assert res["images"][0]["url"] == "http://x/a.jpg"
    assert res["images"][0]["thumb"] == "http://x/t.jpg"
    assert res["images"][0]["source"] == "serper"


def test_search_pixabay(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY" if k == "PIXABAY_API_KEY" else "")
    monkeypatch.setattr(search, "_get_json",
        lambda url, timeout=20: {"hits": [
            {"tags": "car", "largeImageURL": "http://p/l.jpg", "previewURL": "http://p/p.jpg"}]})
    res = search.search_images("car", engine="pixabay")
    assert res["images"][0]["url"] == "http://p/l.jpg"
    assert res["images"][0]["source"] == "pixabay"


def test_search_missing_key(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "")
    res = search.search_images("x", engine="serper")
    assert "error" in res and res["images"] == []


def test_search_unknown_engine(monkeypatch):
    monkeypatch.setattr(search.env, "get_key", lambda k: "KEY")
    res = search.search_images("x", engine="bing")
    assert "error" in res


def test_save_image_downloads_versioned(monkeypatch, tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "images" / "search").mkdir(parents=True)
    (proj / "images" / "search" / "pic.jpg").write_bytes(b"old")  # 기존 → 버전 생성

    def fake_dl(url, dest, timeout=30):
        dest.write_bytes(b"\x89PNG")

    monkeypatch.setattr(search, "_download", fake_dl)
    res = search.save_image(proj, "http://x/a.jpg", "pic.jpg")
    assert res["status"] == "completed"
    assert res["rel"] == "images/search/pic_v2.jpg"      # 무삭제 버전
    assert (proj / "images" / "search" / "pic_v2.jpg").exists()
