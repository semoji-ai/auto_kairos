"""로컬 파일 도구 구현 — Anthropic SDK tool_use 연동용.

script-director처럼 로컬 파일(Read/Write/Edit/Glob)만 사용하는 에이전트를
SDK 모드로 전환할 때 사용한다.

WebSearch / WebFetch / Task / Bash 등 외부 도구가 필요한 에이전트
(research-orchestrator, assembly-director)는 계속 Claude CLI를 사용한다.
"""
from __future__ import annotations

import glob as _glob
from pathlib import Path

# ── Tool 스키마 (Anthropic API 형식) ─────────────────────────────────────

LOCAL_TOOL_SCHEMAS: list[dict] = [
    {
        "name": "Read",
        "description": (
            "파일 내용을 읽습니다. 줄 번호(1-based)와 함께 반환합니다. "
            "offset/limit으로 일부만 읽을 수 있습니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "읽을 파일의 절대 경로",
                },
                "offset": {
                    "type": "integer",
                    "description": "시작 줄 번호 (0-based, 생략 시 처음부터)",
                },
                "limit": {
                    "type": "integer",
                    "description": "읽을 최대 줄 수 (생략 시 전체)",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "Write",
        "description": (
            "파일에 내용을 씁니다. 기존 파일이 있으면 덮어씁니다. "
            "부모 디렉토리가 없으면 자동 생성합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "쓸 파일의 절대 경로",
                },
                "content": {
                    "type": "string",
                    "description": "파일에 쓸 전체 내용",
                },
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "Edit",
        "description": (
            "파일의 특정 텍스트를 교체합니다. "
            "old_string이 파일에 없으면 오류를 반환합니다. "
            "고유한 문자열만 사용하세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "편집할 파일의 절대 경로",
                },
                "old_string": {
                    "type": "string",
                    "description": "교체할 기존 텍스트 (파일 내에서 고유해야 함)",
                },
                "new_string": {
                    "type": "string",
                    "description": "대체할 새로운 텍스트",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        },
    },
    {
        "name": "Glob",
        "description": "glob 패턴으로 파일을 검색합니다. 수정 시간순으로 정렬하여 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "glob 패턴 (예: **/*.json, *.md)",
                },
                "path": {
                    "type": "string",
                    "description": "검색 기준 디렉토리 (생략 시 현재 디렉토리)",
                },
            },
            "required": ["pattern"],
        },
    },
]


# ── 디스패처 ─────────────────────────────────────────────────────────────

def handle_local_tool(tool_name: str, tool_input: dict) -> str:
    """도구 이름 기반 디스패치. 결과를 문자열로 반환."""
    handlers = {
        "Read": _tool_read,
        "Write": _tool_write,
        "Edit": _tool_edit,
        "Glob": _tool_glob,
    }
    handler = handlers.get(tool_name)
    if handler is None:
        return f"[ERROR] 지원하지 않는 도구: {tool_name}"
    return handler(tool_input)


# ── 개별 도구 구현 ────────────────────────────────────────────────────────

def _tool_read(inp: dict) -> str:
    path = Path(inp["file_path"])
    if not path.exists():
        return f"[ERROR] 파일 없음: {path}"
    if path.is_dir():
        return f"[ERROR] 디렉토리입니다 (파일 경로를 지정하세요): {path}"
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except Exception as exc:
        return f"[ERROR] 읽기 실패: {exc}"

    offset = int(inp.get("offset") or 0)
    limit = inp.get("limit")
    selected = lines[offset: offset + limit] if limit else lines[offset:]

    # Claude Code 스타일: "줄번호\t내용"
    return "".join(f"{i + 1 + offset}\t{line}" for i, line in enumerate(selected))


def _tool_write(inp: dict) -> str:
    path = Path(inp["file_path"])
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = inp["content"]
        path.write_text(content, encoding="utf-8")
        return f"파일 작성 완료: {path} ({len(content):,} chars)"
    except Exception as exc:
        return f"[ERROR] 쓰기 실패: {exc}"


def _tool_edit(inp: dict) -> str:
    path = Path(inp["file_path"])
    if not path.exists():
        return f"[ERROR] 파일 없음: {path}"
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"[ERROR] 읽기 실패: {exc}"

    old = inp["old_string"]
    new = inp["new_string"]

    if old not in content:
        preview = old[:80].replace("\n", "\\n")
        return f"[ERROR] 텍스트를 찾을 수 없음: {preview!r}"

    count = content.count(old)
    if count > 1:
        preview = old[:60].replace("\n", "\\n")
        return (
            f"[ERROR] old_string이 {count}곳에 존재합니다 — "
            f"더 고유한 문자열을 사용하세요: {preview!r}"
        )

    updated = content.replace(old, new, 1)
    try:
        path.write_text(updated, encoding="utf-8")
    except Exception as exc:
        return f"[ERROR] 쓰기 실패: {exc}"
    return f"편집 완료: {path}"


def _tool_glob(inp: dict) -> str:
    pattern = inp["pattern"]
    base = inp.get("path") or "."
    try:
        matches = _glob.glob(pattern, root_dir=base, recursive=True)
    except Exception as exc:
        return f"[ERROR] glob 실패: {exc}"

    if not matches:
        return "일치하는 파일 없음"

    # 수정 시간순 정렬 (최신 먼저)
    base_path = Path(base)
    try:
        matches.sort(
            key=lambda f: (base_path / f).stat().st_mtime,
            reverse=True,
        )
    except Exception:
        matches.sort()

    return "\n".join(matches)
