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

# ═══════════════════════════════════════
# Director Agent 전용 도구 스키마
# ═══════════════════════════════════════

DIRECTOR_TOOL_SCHEMAS = [
    {
        "name": "get_pipeline_state",
        "description": "현재 파이프라인 상태를 조회합니다. 완료/실패/스킵된 스텝 목록과 현재 phase/step을 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_step_info",
        "description": "pipeline.json에서 특정 스텝의 정의(에이전트, 모듈, 입출력, 옵션 등)를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "조회할 스텝 ID (예: step_1, step_5)",
                },
            },
            "required": ["step_id"],
        },
    },
    {
        "name": "run_step",
        "description": "단일 스텝을 실행합니다. _execute_step + _validate_step을 호출하고 상태를 업데이트합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "실행할 스텝 ID",
                },
                "feedback": {
                    "type": "string",
                    "description": "에이전트에 전달할 Director 피드백 (선택)",
                },
            },
            "required": ["step_id"],
        },
    },
    {
        "name": "run_steps_parallel",
        "description": "여러 스텝을 ThreadPoolExecutor로 동시 실행합니다. 독립적인 스텝들을 병렬로 처리할 때 사용합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "동시 실행할 스텝 ID 배열",
                },
            },
            "required": ["step_ids"],
        },
    },
    {
        "name": "retry_step",
        "description": "실패한 스텝을 재실행합니다. 실패 목록에서 제거 후 feedback을 주입하여 다시 실행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "재실행할 스텝 ID",
                },
                "feedback": {
                    "type": "string",
                    "description": "재실행 시 에이전트에 전달할 피드백/지시사항",
                },
            },
            "required": ["step_id"],
        },
    },
    {
        "name": "skip_step",
        "description": "스텝을 건너뜁니다. skipped_steps에 추가하고 메신저에 알림을 보냅니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "건너뛸 스텝 ID",
                },
                "reason": {
                    "type": "string",
                    "description": "건너뛰는 이유",
                },
            },
            "required": ["step_id", "reason"],
        },
    },
    {
        "name": "review_output",
        "description": "프로젝트 디렉토리 기준 상대경로로 파일을 읽습니다. 5000자 초과 시 앞뒤만 요약합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "프로젝트 디렉토리 기준 상대 경로 (예: scene_specs.json)",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "log_preference",
        "description": "Director 학습 메모를 .vault/preferences/에 기록합니다. 프리셋별로 축적됩니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "기록할 학습 메모/선호 사항",
                },
                "preset_id": {
                    "type": "string",
                    "description": "프리셋 ID (기본: general)",
                },
            },
            "required": ["note"],
        },
    },
    {
        "name": "send_message",
        "description": "대시보드 메신저에 메시지를 전송합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "전송할 메시지 텍스트",
                },
                "level": {
                    "type": "string",
                    "enum": ["info", "success", "warning", "error"],
                    "description": "메시지 레벨 (기본: info)",
                },
            },
            "required": ["text"],
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
