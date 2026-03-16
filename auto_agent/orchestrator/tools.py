"""
Anthropic API tool_use 도구 정의 및 실행.

역할:
  - Claude CLI의 Read/Write/Glob/WebSearch/WebFetch 도구를
    Anthropic API tool_use 스키마로 재정의
  - 각 도구의 실제 실행 로직 구현
  - 보안 검증 (경로 제한)
"""

import glob as glob_module
import json
import os
import re
from pathlib import Path
from typing import Any

import requests

# ═══════════════════════════════════════
# 도구 스키마 (Anthropic tool_use 형식)
# ═══════════════════════════════════════

TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "파일 내용을 읽습니다. 절대 경로를 사용하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "읽을 파일의 절대 경로",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "파일에 내용을 씁니다. 디렉토리가 없으면 자동 생성됩니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "쓸 파일의 절대 경로",
                },
                "content": {
                    "type": "string",
                    "description": "파일에 쓸 내용",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "glob_files",
        "description": "글로브 패턴으로 파일 목록을 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "글로브 패턴 (예: '**/*.json')",
                },
                "directory": {
                    "type": "string",
                    "description": "검색 시작 디렉토리 (기본: 프로젝트 디렉토리)",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": "웹 검색을 수행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 쿼리",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": "URL의 웹 페이지 내용을 가져옵니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "가져올 URL",
                }
            },
            "required": ["url"],
        },
    },
]

# Claude CLI 도구명 → API 도구명 매핑
CLI_TO_API_TOOL_MAP = {
    "Read": "read_file",
    "Write": "write_file",
    "Glob": "glob_files",
    "WebSearch": "web_search",
    "WebFetch": "web_fetch",
    "Task": None,  # 별도 처리 (순차 실행으로 단순화)
}


# ═══════════════════════════════════════
# 도구 실행기
# ═══════════════════════════════════════


class ToolExecutor:
    """도구 호출을 실제 파일 I/O / API 호출로 실행."""

    def __init__(self, workspace_root: Path, project_dir: Path):
        self.workspace_root = workspace_root.resolve()
        self.project_dir = project_dir.resolve()
        self.allowed_roots = [
            self.workspace_root,
            self.project_dir,
        ]

    def execute(self, tool_name: str, tool_input: dict) -> str:
        handler = getattr(self, f"_exec_{tool_name}", None)
        if not handler:
            return f"ERROR: 알 수 없는 도구 — {tool_name}"
        return handler(tool_input)

    def _validate_path(self, path_str: str) -> Path:
        path = Path(path_str).resolve()
        if not any(str(path).startswith(str(root)) for root in self.allowed_roots):
            raise PermissionError(
                f"경로 접근 거부: {path} "
                f"(허용: {[str(r) for r in self.allowed_roots]})"
            )
        return path

    def _exec_read_file(self, inp: dict) -> str:
        path = self._validate_path(inp["path"])
        if not path.exists():
            return f"ERROR: 파일 없음 — {path}"
        if not path.is_file():
            return f"ERROR: 파일이 아님 — {path}"
        content = path.read_text(encoding="utf-8")
        if len(content) > 500_000:
            return (
                content[:500_000]
                + f"\n\n... (truncated, total {len(content)} chars)"
            )
        return content

    def _exec_write_file(self, inp: dict) -> str:
        path = self._validate_path(inp["path"])
        content = inp["content"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return (
            f"OK: {path} 저장 완료 "
            f"({len(content)} chars, {len(content.encode('utf-8'))} bytes)"
        )

    def _exec_glob_files(self, inp: dict) -> str:
        directory = inp.get("directory", str(self.project_dir))
        self._validate_path(directory)
        matches = sorted(
            glob_module.glob(inp["pattern"], root_dir=directory, recursive=True)
        )
        if not matches:
            return "검색 결과 없음"
        result = matches[:200]
        if len(matches) > 200:
            result.append(f"... 외 {len(matches) - 200}개")
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _exec_web_search(self, inp: dict) -> str:
        return _call_web_search(inp["query"])

    def _exec_web_fetch(self, inp: dict) -> str:
        return _call_web_fetch(inp["url"])


def filter_tools_for_agent(allowed_tools: list[str]) -> list[dict]:
    """agents.json의 allowed_tools 목록으로 API 도구 스키마 필터링."""
    api_names = set()
    for cli_name in allowed_tools:
        api_name = CLI_TO_API_TOOL_MAP.get(cli_name)
        if api_name:
            api_names.add(api_name)
    return [t for t in TOOL_SCHEMAS if t["name"] in api_names]


# ═══════════════════════════════════════
# WebSearch / WebFetch 구현
# ═══════════════════════════════════════


def _call_web_search(query: str) -> str:
    """Serper API로 웹 검색."""
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return "ERROR: SERPER_API_KEY 환경변수 미설정"

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "kr", "hl": "ko", "num": 10},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return f"ERROR: 검색 실패 — {e}"

    results = []
    for item in data.get("organic", [])[:10]:
        results.append(
            f"**{item.get('title', '')}**\n"
            f"{item.get('link', '')}\n"
            f"{item.get('snippet', '')}\n"
        )
    return "\n---\n".join(results) if results else "검색 결과 없음"


def _call_web_fetch(url: str) -> str:
    """URL 내용 fetch + HTML→텍스트 변환."""
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KairosAgent/1.0)"},
        )
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 50_000:
            text = text[:50_000] + "\n\n... (truncated)"
        return text
    except requests.RequestException as e:
        return f"ERROR: {e}"
