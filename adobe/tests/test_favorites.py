"""즐겨찾기 — 소스 칸의 쓰임을 바꾼다.

칸이 프로젝트 이미지를 통째로 깔고 있었다. 디아지오편 **1044장**이고 그중
**565장이 내용이 같은 사본**이다(1.3GB) — 개발 과정에서 `images/generated/`
와 `storyboard/` 로 두 벌씩 남았다. 그 안에서 자주 쓰는 배경 한 장을 찾는
것은 일이다.

담아 둔 것만 깔고, 프로젝트 소스는 폴더를 열어 끌어다 쓴다.
"""
import json
from pathlib import Path

import pytest

from backend import favorites

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"


@pytest.fixture(autouse=True)
def _here(tmp_path, monkeypatch):
    monkeypatch.setenv("AK_FAVORITES", str(tmp_path / "fav"))


def _png(p: Path, b=b"\x89PNG-a"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return p


def test_add_copies_the_file(tmp_path):
    """**복사한다.** 원본을 가리키기만 하면 그 프로젝트를 지웠을 때 통째로 깨진다."""
    src = _png(tmp_path / "proj" / "storyboard" / "sb_a.png")
    r = favorites.add(src, label="배경 하나")
    assert r["ok"] and not r["already"]
    kept = favorites.root() / r["item"]["name"]
    assert kept.is_file() and kept.read_bytes() == src.read_bytes()
    src.unlink()                      # 원본이 사라져도
    assert favorites.listing()["items"][0]["label"] == "배경 하나"


def test_same_picture_is_kept_once(tmp_path):
    """같은 그림을 두 번 담아도 한 벌만 — 내용으로 판정한다."""
    a = _png(tmp_path / "a.png")
    b = _png(tmp_path / "다른이름.png")      # 이름은 달라도 내용이 같다
    favorites.add(a)
    r = favorites.add(b)
    assert r["already"]
    assert len(favorites.listing()["items"]) == 1


def test_name_clash_does_not_overwrite(tmp_path):
    """이름이 겹치면 번호를 붙인다 — 덮어쓰지 않는다."""
    favorites.add(_png(tmp_path / "one" / "bg.png", b"\x89PNG-1"))
    favorites.add(_png(tmp_path / "two" / "bg.png", b"\x89PNG-2"))
    names = sorted(x["name"] for x in favorites.listing()["items"])
    assert names == ["bg.png", "bg_2.png"]


def test_remove_takes_the_copy_with_it(tmp_path):
    r = favorites.add(_png(tmp_path / "a.png"))
    n = r["item"]["name"]
    assert favorites.remove(n)["ok"]
    assert not (favorites.root() / n).exists()
    assert favorites.listing()["items"] == []


def test_missing_file_is_filtered_out(tmp_path):
    """손으로 지운 것은 조용히 목록에서 뺀다 — 깨진 칸을 보여 주지 않는다."""
    r = favorites.add(_png(tmp_path / "a.png"))
    (favorites.root() / r["item"]["name"]).unlink()
    assert favorites.listing()["items"] == []


def test_rejects_what_it_cannot_hold(tmp_path):
    p = tmp_path / "메모.txt"; p.write_text("x", encoding="utf-8")
    assert "error" in favorites.add(p)


def test_reveal_is_cross_platform():
    """맥·윈도우·리눅스가 각각 다르다 — 셋 다 있어야 한다."""
    src = (Path(__file__).resolve().parents[1] / "backend" / "favorites.py").read_text(encoding="utf-8")
    assert '"Darwin"' in src and 'open", "-R"' in src
    assert '"Windows"' in src and "explorer /select," in src
    assert "xdg-open" in src


def test_source_panel_shows_favorites_only():
    """소스 칸에 **프로젝트 이미지를 깔지 않는다.**

    디아지오편 1044장이고 그중 565장이 같은 내용의 사본이다 — 다 깔면 정작
    자주 쓰는 배경 한 장을 못 찾는다. 씬 이미지와 에셋은 이미 왼쪽 시트에
    있으니 같은 것을 오른쪽에 또 깔 이유가 없다.
    """
    js = (PANEL / "js" / "gallery.js").read_text(encoding="utf-8")
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert "loadFavorites();" in js
    assert 'data-v="proj"' not in html          # 프로젝트 탭은 없앴다
    assert "srct-title" in html
    # 프로젝트 소스는 폴더를 열어 끌어다 쓴다
    assert 'id="srcFolders"' in html and 'data-d="storyboard"' in html
    assert "function revealFolder(" in js


def test_two_ways_to_register():
    """담는 길은 둘 — 왼쪽 시트의 ☆, 그리고 파인더에서 끌어다 놓기."""
    gal = (PANEL / "js" / "gallery.js").read_text(encoding="utf-8")
    sb = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    # ① 시트의 ☆ — 씬 이미지와 레이어 양쪽에
    assert sb.count('class="fav-add"') >= 2
    assert "/api/favorites/add" in sb
    assert "sheet.__favWired" in sb          # 위임 — 행이 다시 그려져도 산다
    # ② 끌어다 놓기
    assert "function wireFavDrop(" in gal
    assert "fs[i].path" in gal               # CEP 는 실제 경로를 준다


def test_nothing_loads_the_project_gallery_anymore():
    """**부르는 곳이 하나도 없어야 한다.**

    화면을 즐겨찾기로 바꾸고도 씬 이미지가 계속 떴다. `nav.js` 가 프로젝트를
    열 때마다 `loadGallery()` 를 부르고 있었기 때문이다 — 캐시가 아니라
    코드였다. 남겨 두면 누군가(나 포함) 다시 부른다.
    """
    js_dir = PANEL / "js"
    for p in sorted(js_dir.glob("*.js")):
        src = p.read_text(encoding="utf-8")
        assert "loadGallery(" not in src, f"{p.name} 이 아직 프로젝트 갤러리를 부른다"
        assert "srcView(" not in src, p.name


def test_project_entry_loads_favorites():
    """프로젝트를 열면 즐겨찾기를 읽는다."""
    nav = (PANEL / "js" / "nav.js").read_text(encoding="utf-8")
    assert "loadFavorites()" in nav


def test_search_saves_go_to_favorites():
    """골라서 받은 것은 즐겨찾기에 담는다 — 프로젝트에만 두면 1044장 속에 묻힌다."""
    gal = (PANEL / "js" / "gallery.js").read_text(encoding="utf-8")
    seg = gal.split("function searchGallery(")[0] + gal.split("function searchGallery(")[1]
    assert seg.count("favAdd(") >= 2
