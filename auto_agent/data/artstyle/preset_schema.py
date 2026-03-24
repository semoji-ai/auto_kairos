"""아트스타일 프리셋 스키마 검증."""
from pathlib import Path
from typing import List, Optional, Union
import json

REQUIRED_SECTIONS = ["image", "voice", "creative", "scenes", "guidelines"]
REQUIRED_IMAGE = ["staging", "reference_image", "scene_style_description"]
REQUIRED_VOICE = ["voice_id"]
VALID_STAGING = ["cinematic", "flat"]


def validate_preset(preset: dict) -> List[str]:
    """프리셋 검증. 누락/오류 목록 반환. 빈 리스트면 통과."""
    errors = []
    for section in REQUIRED_SECTIONS:
        if section not in preset:
            errors.append(f"섹션 누락: {section}")

    image = preset.get("image", {})
    for field in REQUIRED_IMAGE:
        if not image.get(field):
            errors.append(f"image.{field} 누락")
    if image.get("staging") and image["staging"] not in VALID_STAGING:
        errors.append(f"image.staging 유효하지 않음: {image['staging']} (허용: {VALID_STAGING})")

    voice = preset.get("voice", {})
    for field in REQUIRED_VOICE:
        if not voice.get(field):
            errors.append(f"voice.{field} 누락")

    if not preset.get("guidelines"):
        errors.append("guidelines 비어있음")

    return errors


def load_preset(path: Union[str, Path]) -> dict:
    """프리셋 JSON 로드. 기존 형식이면 자동 래핑."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "image" not in data and "style" in data:
        data = _migrate_legacy(data)
    return data


def _migrate_legacy(legacy: dict) -> dict:
    """기존 아트스타일 JSON -> 확장 프리셋 형식으로 래핑."""
    migrated = {
        "id": legacy.get("id", legacy.get("name", "unknown")),
        "name": legacy.get("name", ""),
        "description": legacy.get("description", ""),
        "channel": None,
        "image": {
            "staging": "cinematic",
            "reference_image": legacy.get("reference_image", ""),
            "scene_style_description": legacy.get("scene_style_description", ""),
            "style": legacy.get("style", {}),
            "critical_requirements": legacy.get("technical", {}).get("critical_requirements", []),
            "prompt_language": "ko",
        },
        "voice": {"voice_id": "", "voice_settings": {}},
        "creative": {},
        "scenes": {},
        "guidelines": "",
    }
    # 원본 필드 보존 (하위 호환) -- image/voice/creative/scenes/guidelines와 겹치지 않는 것만
    preserve_keys = {"reference_image", "scene_style_description", "style", "technical",
                     "historical_period", "prompt_overrides"}
    for k, v in legacy.items():
        if k not in migrated and k not in preserve_keys:
            migrated[k] = v
    return migrated
