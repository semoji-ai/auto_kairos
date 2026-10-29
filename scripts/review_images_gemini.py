#!/usr/bin/env python3
"""Deprecated filename: routes image review to GPT, never to Gemini."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_images_gpt import MODEL, REF, RUBRIC, main


def call(*args, **kwargs):
    """Fail closed for old direct Gemini API callers, including archived experiments."""
    raise RuntimeError("Gemini 이미지 검수는 폐기됐습니다. scripts/review_images_gpt.py를 사용하세요.")


if __name__ == "__main__":
    print("이전 명령입니다. Gemini 대신 GPT(Codex) 이미지 검수를 실행합니다.", file=sys.stderr)
    raise SystemExit(main())
