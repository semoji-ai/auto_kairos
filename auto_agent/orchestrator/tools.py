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

