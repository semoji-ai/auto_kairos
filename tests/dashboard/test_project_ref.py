"""project_ref helper 단위 테스트."""
from unittest.mock import MagicMock
import pytest

from auto_agent.dashboard.project_ref import (
    is_uuid_form,
    resolve_project_ref,
    canonical_uuid_url,
)


def test_is_uuid_form_recognizes_8char_hex():
    assert is_uuid_form("9f202fb4") is True
    assert is_uuid_form("00000000") is True
    assert is_uuid_form("abcdef12") is True


def test_is_uuid_form_rejects_non_hex():
    assert is_uuid_form("포켓몬스터") is False
    assert is_uuid_form("my-slug") is False
    assert is_uuid_form("9f202fb") is False  # 7자
    assert is_uuid_form("9f202fb4a") is False  # 9자
    assert is_uuid_form("9F202FB4") is False  # 대문자 — slug로 취급
    assert is_uuid_form("ghijklmn") is False  # hex 아님


def test_resolve_by_uuid_returns_project_no_redirect():
    pm = MagicMock()
    pm.get_project.return_value = {"uuid": "9f202fb4", "slug": "포켓몬"}

    project, needs_redirect = resolve_project_ref(pm, "9f202fb4")

    assert project["uuid"] == "9f202fb4"
    assert needs_redirect is False
    pm.get_project.assert_called_once_with(uuid="9f202fb4")


def test_resolve_by_slug_returns_project_with_redirect_flag():
    pm = MagicMock()
    pm.get_project.return_value = {"uuid": "9f202fb4", "slug": "포켓몬"}

    project, needs_redirect = resolve_project_ref(pm, "포켓몬")

    assert project["uuid"] == "9f202fb4"
    assert needs_redirect is True
    pm.get_project.assert_called_once_with(slug="포켓몬")


def test_resolve_returns_none_when_not_found():
    pm = MagicMock()
    pm.get_project.return_value = None

    project, needs_redirect = resolve_project_ref(pm, "nonexistent")

    assert project is None
    assert needs_redirect is False


def test_canonical_uuid_url_replaces_first_segment_after_p():
    assert canonical_uuid_url(
        "/p/포켓몬?tab=storyboard", uuid="9f202fb4"
    ) == "/p/9f202fb4?tab=storyboard"


def test_canonical_uuid_url_handles_api_path():
    assert canonical_uuid_url(
        "/api/p/포켓몬/editor/scenes/3/select-image", uuid="9f202fb4"
    ) == "/api/p/9f202fb4/editor/scenes/3/select-image"


def test_canonical_uuid_url_preserves_query_string():
    assert canonical_uuid_url(
        "/p/my-slug?tab=studio&debug=1", uuid="abc12345"
    ) == "/p/abc12345?tab=studio&debug=1"
