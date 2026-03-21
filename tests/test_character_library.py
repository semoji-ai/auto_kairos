import pytest
import sqlite3
from pathlib import Path
from PIL import Image
from auto_agent.tools.character_library import (
    CharacterLibrary, CharacterRecord, embed_png_metadata, read_png_metadata
)


@pytest.fixture
def tmp_library(tmp_path):
    """임시 라이브러리 인스턴스 (격리된 디렉토리 사용)."""
    lib = CharacterLibrary(
        library_dir=tmp_path / "characters",
        db_path=tmp_path / "characters.db",
    )
    return lib


@pytest.fixture
def sample_png(tmp_path) -> Path:
    """1×1 검은 PNG 파일."""
    p = tmp_path / "test.png"
    Image.new("RGB", (1, 1)).save(p)
    return p


def test_embed_and_read_metadata(sample_png):
    meta = {
        "character_name": "일론 머스크",
        "art_style": "quirky_cartoon",
        "tags": "기업인,테슬라",
        "features": "짧은 머리, 정장",
        "source_project": "test_proj",
    }
    embed_png_metadata(sample_png, meta)
    result = read_png_metadata(sample_png)
    assert result["character_name"] == "일론 머스크"
    assert result["art_style"] == "quirky_cartoon"
    assert result["tags"] == "기업인,테슬라"


def test_library_dir_created_on_init(tmp_path):
    lib_dir = tmp_path / "chars"
    db_path = tmp_path / "chars.db"
    assert not lib_dir.exists()
    CharacterLibrary(library_dir=lib_dir, db_path=db_path)
    assert lib_dir.exists()
    assert db_path.exists()


def test_db_schema_created(tmp_library):
    conn = sqlite3.connect(str(tmp_library.db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "characters" in tables


def test_register_adds_to_db_and_library(tmp_library, sample_png):
    meta = {
        "character_name": "홍길동",
        "art_style": "quirky_cartoon",
        "tags": "영웅,조선시대",
        "features": "갓과 도포 착용, 의협심 강한 표정",
        "source_project": "test",
    }
    record = tmp_library.register(sample_png, meta)
    assert record.name == "홍길동"
    assert Path(record.file_path).exists()
    assert Path(record.file_path).parent == tmp_library.library_dir


def test_register_duplicate_features_skips(tmp_library, sample_png):
    meta = {
        "character_name": "홍길동",
        "art_style": "quirky_cartoon",
        "tags": "영웅",
        "features": "갓과 도포",
        "source_project": "test",
    }
    r1 = tmp_library.register(sample_png, meta)
    r2 = tmp_library.register(sample_png, meta)
    assert r1.id == r2.id


def test_register_different_features_creates_new_record(tmp_library, sample_png, tmp_path):
    base_meta = {"character_name": "일론 머스크", "art_style": "quirky_cartoon", "source_project": "t"}
    png2 = tmp_path / "test2.png"
    Image.new("RGB", (1, 1)).save(png2)

    r1 = tmp_library.register(sample_png, {**base_meta, "features": "젊은 시절, 청바지", "tags": ""})
    r2 = tmp_library.register(png2,       {**base_meta, "features": "현재 모습, 정장", "tags": ""})
    assert r1.id != r2.id


def test_search_returns_exact_match(tmp_library, sample_png):
    tmp_library.register(sample_png, {
        "character_name": "김철수",
        "art_style": "watercolor",
        "tags": "학생",
        "features": "교복",
        "source_project": "s1",
    })
    result = tmp_library.search("김철수", "watercolor")
    assert result is not None
    assert result.name == "김철수"


def test_search_returns_none_for_missing(tmp_library):
    result = tmp_library.search("없는캐릭터", "any_style")
    assert result is None


def test_search_tags_score(tmp_library, sample_png, tmp_path):
    base = {"character_name": "박영희", "art_style": "comic", "source_project": "t"}
    png2 = tmp_path / "t2.png"; Image.new("RGB", (1,1)).save(png2)
    png3 = tmp_path / "t3.png"; Image.new("RGB", (1,1)).save(png3)

    tmp_library.register(sample_png, {**base, "features": "A", "tags": "과학자"})
    tmp_library.register(png2,       {**base, "features": "B", "tags": "과학자,교수,노벨상"})
    tmp_library.register(png3,       {**base, "features": "C", "tags": "교수"})

    result = tmp_library.search("박영희", "comic", tags=["과학자", "노벨상"])
    assert "노벨상" in result.tags


def test_copy_to_project(tmp_library, sample_png, tmp_path):
    record = tmp_library.register(sample_png, {
        "character_name": "테스트",
        "art_style": "comic",
        "tags": "",
        "features": "test",
        "source_project": "s",
    })
    project_dir = tmp_path / "project"
    dest = tmp_library.copy_to_project(record, project_dir)
    assert dest.exists()
    assert dest.parent == project_dir / "characters"


def test_rebuild_index_restores_db(tmp_library, sample_png, tmp_path):
    tmp_library.register(sample_png, {
        "character_name": "복원테스트",
        "art_style": "test_style",
        "tags": "a,b",
        "features": "복원 피처",
        "source_project": "x",
    })
    # DB 삭제
    tmp_library.db_path.unlink()
    tmp_library._init_db()

    count = tmp_library.rebuild_index()
    assert count == 1
    result = tmp_library.search("복원테스트", "test_style")
    assert result is not None


def test_rebuild_index_skips_no_metadata_png(tmp_library, tmp_path):
    plain_png = tmp_library.library_dir / "no_meta.png"
    Image.new("RGB", (1, 1)).save(plain_png)

    count = tmp_library.rebuild_index()
    assert count == 0
