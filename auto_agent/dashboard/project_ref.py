"""프로젝트 식별자(uuid 또는 slug) 해석 helper.

URL의 path 파라미터로 들어온 식별자를 uuid 정본으로 해석한다.
- 8자 hex(`^[a-f0-9]{8}$`)면 uuid로 조회
- 그 외는 slug로 조회 → 호출자에게 canonical redirect 신호 반환

진입 형태(uuid/slug)와 무관하게 핸들러 로직은 동일하게 동작하며,
slug 진입 시에만 301 redirect를 반환하는 책임은 호출자에게 있다.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_UUID_RE = re.compile(r"^[a-f0-9]{8}$")


def is_uuid_form(value: str) -> bool:
    """value가 uuid 형식(8자 소문자 hex)인지."""
    return bool(_UUID_RE.match(value))


def resolve_project_ref(pm, project_ref: str) -> Tuple[Optional[dict], bool]:
    """project_ref(uuid 또는 slug) → (project, needs_redirect).

    Returns:
        (project, needs_redirect)
        - project: dict 또는 None(미발견)
        - needs_redirect: True면 호출자가 301 redirect 응답 반환해야 함
    """
    if is_uuid_form(project_ref):
        return pm.get_project(uuid=project_ref), False
    project = pm.get_project(slug=project_ref)
    if project is None:
        return None, False
    if not project.get("uuid"):
        return project, False
    return project, True


def canonical_uuid_url(original_path: str, uuid: str) -> str:
    """URL 경로의 `/p/{...}` 첫 세그먼트를 uuid로 치환.

    `/p/포켓몬?tab=storyboard` + uuid=`9f202fb4`
        → `/p/9f202fb4?tab=storyboard`
    `/api/p/포켓몬/editor/scenes/3` + uuid=`9f202fb4`
        → `/api/p/9f202fb4/editor/scenes/3`
    """
    return re.sub(
        r"(?P<prefix>/(?:api/)?p/)[^/?]+",
        lambda m: m.group("prefix") + uuid,
        original_path,
        count=1,
    )
