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


def test_panel_opens_favorites_first():
    """열면 즐겨찾기부터 — 1044장을 깔지 않는다."""
    js = (PANEL / "js" / "gallery.js").read_text(encoding="utf-8")
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'srcView("fav")' in js
    assert 'data-v="fav"' in html and 'data-v="proj"' in html
    # 프로젝트 쪽에는 폴더 열기 — 끌어다 쓰라고
    assert 'id="srcFolders"' in html and 'data-d="storyboard"' in html
    assert "function revealFolder(" in js
    # 프로젝트 칸의 ☆ 로 담는다
    assert "function favAdd(" in js and 'class="fav-star"' in js
