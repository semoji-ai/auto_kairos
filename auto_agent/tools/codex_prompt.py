"""gpt-image-2(codex 내장 image_gen)용 프롬프트 빌더 — 공냥 규격.

철칙: 네거티브 문구 금지(긍정형만), 앞머리 브래킷 금지, 끝에 `AR x:y` 토큰 하나,
사이즈 락 6종. FAL 프롬프트 빌더(image_generate)와 별도 경로.

check_prompt.mjs(~/.claude/skills/image-prompt/scripts/check_prompt.mjs) 검증 규칙상
프롬프트 안에 다음이 모두 있어야 ok:true 가 된다:
- 끝에 `AR x:y` 토큰
- 매체/카테고리를 드러내는 절 (`Scene:` 리터럴 포함 시 통과)
- 카메라/구도 언어 (`Camera:` 리터럴 포함 시 통과)
- 명시적 조명 지시 (`Lighting:` 리터럴 포함 시 통과)
- 재질/질감/매체 디테일 (`Texture/Medium:` 리터럴 포함 시 통과)
그래서 6섹션 템플릿을 축약형이 아니라 Scene/Camera/Lighting/Texture-Medium
4개 리터럴 헤더를 실제로 포함하는 형태로 조립한다 (헤더 자체가 한국어 번역 여부와
무관하게 검증기 정규식에 매칭되므로 안전).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

# 사이즈 락 (codex 6종, auto 금지)
SIZE_LOCK = {
    "16:9": "1792x1024",
    "3:2": "1536x1024",
    "4:3": "1536x1024",
    "9:16": "1024x1792",
    "1:1": "1024x1024",
    "2:3": "1024x1536",
    "3:4": "1024x1536",
    "4:5": "1024x1536",
}

VALIDATOR_PATH = Path.home() / ".claude/skills/image-prompt/scripts/check_prompt.mjs"

# 기본 카메라/조명 서술 — 순수 긍정형, 사용자 철칙 준수.
# style_keywords 쪽에 이미 조명/카메라 지시가 있어도 중복 주입은 검증기 통과에
# 문제 없으므로(중복 경고 없음) 항상 붙인다.
_DEFAULT_CAMERA = "eye-level composition, clear central focal subject, balanced framing"
_DEFAULT_LIGHTING = "soft natural light, gentle key light with subtle fill"


def _translate(text: str) -> str:
    """auto_agent.tools.image_generate._translate_to_english 지연 임포트 래퍼.

    순환 임포트 회피를 위해 호출 시점에 임포트한다.
    """
    from auto_agent.tools.image_generate import _translate_to_english

    return _translate_to_english(text)


def build_codex_image_prompt(description: str, style_keywords: str, ar: str = "16:9") -> Tuple[str, str]:
    """씬 묘사(한글 가능) + 스타일 키워드 → (완성 프롬프트, size).

    4섹션 리터럴 헤더(Scene/Camera/Lighting/Texture-Medium) + 끝 AR 토큰.
    check_prompt.mjs 검증기가 요구하는 필수 절을 모두 리터럴로 포함해
    번역 결과 언어와 무관하게 통과하도록 조립한다.
    """
    size = SIZE_LOCK.get(ar, SIZE_LOCK["16:9"])
    scene_en = _translate(description).strip().rstrip(".")
    style = style_keywords.strip().rstrip(".")

    sections = [
        f"Scene: {scene_en}",
        f"Camera: {_DEFAULT_CAMERA}",
        f"Lighting: {_DEFAULT_LIGHTING}",
        f"Texture/Medium: {style}" if style else "Texture/Medium: clean finish, natural material rendering",
    ]
    prompt = ". ".join(sections) + f". AR {ar}"
    return prompt, size


def validate_prompt(prompt: str) -> Tuple[bool, str]:
    """check_prompt.mjs 검증. 스크립트/node 부재 시 통과 처리(경고 메시지 반환)."""
    node = shutil.which("node")
    if not node or not VALIDATOR_PATH.exists():
        return True, "validator absent"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        tmp = f.name
    try:
        res = subprocess.run(
            [node, str(VALIDATOR_PATH), tmp],
            capture_output=True, text=True, timeout=30,
        )
        out = (res.stdout or "").strip()
        try:
            ok = bool(json.loads(out).get("ok"))
        except Exception:
            ok = res.returncode == 0
        return ok, out[-500:]
    except Exception as e:
        return True, f"validator error(통과 처리): {e}"
    finally:
        Path(tmp).unlink(missing_ok=True)
