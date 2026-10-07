"""ElevenLabs TTS 모델·보이스 설정 — 한 곳에서 모델별로 정한다.

기본 모델은 **eleven_v4** 다(2026-09-30 v4 비교 실험, 마이디어·한화편에서 확정).
v4 는 원고를 그대로 읽는다 — 숫자·연도·영문을 스스로 정규화하므로 한국어 전처리기
(`korean_tts_preprocessor`)를 거치지 않는다. 전처리기가 만든 "천-구백-육십-팔련" 같은
발음 표기는 v4 에서는 오히려 끊긴 억양을 만든다.

v4 와 v2 의 차이(요청 본문):
    v4  voice_settings = stability·similarity_boost 만. style·speed 없음, SSML(<break>) 없음.
        language_code="ko", apply_text_normalization="auto" 를 함께 보낸다.
    v2  (폴백) stability·similarity_boost·style·use_speaker_boost·speed. 전처리기 필수.

모델 선택 순서: 호출자가 준 값 → 환경변수 ELEVENLABS_MODEL_ID → eleven_v4.
보이스 설정은 모델별로 따로 둔다. 예전 설정 파일·DB 에 남은 "평평한" voice_settings
(stability 1.0·style 0.9·speed 1.1)는 **v2 튜닝값**이라 v4 에는 쓰지 않는다 —
v4 에 넘기려면 {"eleven_v4": {...}} 처럼 모델 이름 아래에 둔다.
"""
from __future__ import annotations

import os
from typing import Any

V4 = "eleven_v4"
V2 = "eleven_multilingual_v2"
DEFAULT_MODEL = V4

# 화풍(writing_style)별 보이스 — runner·generate_tts 가 따로 들고 있던 표를 합쳤다.
STYLE_VOICES: dict[str, str] = {
    "semoji": "W7FnAxJNpD5WGjrF5GLp",
    "semoji_3d": "W7FnAxJNpD5WGjrF5GLp",
    "iromism": "9Sj8ugvpK1DmcAXyvi3a",
    "default": "4JJwo477JUAx3HV0T7n7",
}

# 모델별 프로필. allowed = 그 모델이 받는 voice_settings 키.
MODEL_PROFILES: dict[str, dict[str, Any]] = {
    V4: {
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.9},
        "allowed": ("stability", "similarity_boost"),
        "extra_body": {"language_code": "ko", "apply_text_normalization": "auto"},
        "preprocess": False,
    },
    V2: {
        "voice_settings": {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9,
                           "use_speaker_boost": True, "speed": 1.1},
        "allowed": ("stability", "similarity_boost", "style", "use_speaker_boost", "speed"),
        "extra_body": {},
        "preprocess": True,
    },
}

# v2 에서만 보이스마다 다른 값 (이로미즘은 similarity 0.6)
V2_VOICE_OVERRIDES: dict[str, dict[str, Any]] = {
    "9Sj8ugvpK1DmcAXyvi3a": {"similarity_boost": 0.6},
}


def default_model() -> str:
    return (os.getenv("ELEVENLABS_MODEL_ID") or "").strip() or DEFAULT_MODEL


def resolve_model(model: str | None = None) -> str:
    return (model or "").strip() or default_model()


def is_v4(model: str | None) -> bool:
    return resolve_model(model).startswith("eleven_v4")


def profile(model: str | None) -> dict[str, Any]:
    m = resolve_model(model)
    if m in MODEL_PROFILES:
        return MODEL_PROFILES[m]
    return MODEL_PROFILES[V4] if is_v4(m) else MODEL_PROFILES[V2]


def uses_preprocessor(model: str | None = None) -> bool:
    """한국어 전처리기를 거쳐야 하는 모델인가 — v2 계열만 그렇다."""
    return bool(profile(model)["preprocess"])


def voice_settings_for(model: str | None = None, overrides: dict | None = None,
                       voice_id: str | None = None) -> dict:
    """모델에 맞는 voice_settings.

    overrides 형식:
      {"eleven_v4": {...}, "eleven_multilingual_v2": {...}}  모델별 — 해당 모델 값만 쓴다
      {"stability": ...}  평평한 옛 형식 — v2 튜닝값으로 보고 v2 에만 적용한다
    어느 경우든 모델이 받지 않는 키(v4 의 style·speed 등)는 걷어낸다."""
    m = resolve_model(model)
    prof = profile(m)
    out = dict(prof["voice_settings"])
    if not is_v4(m) and voice_id in V2_VOICE_OVERRIDES:
        out.update(V2_VOICE_OVERRIDES[voice_id])
    ov = overrides or {}
    per_model = {k: v for k, v in ov.items() if isinstance(v, dict)}
    if per_model:
        key = m if m in per_model else (V4 if is_v4(m) and V4 in per_model else
                                        (V2 if not is_v4(m) and V2 in per_model else None))
        if key:
            out.update(per_model[key])
    elif ov and not is_v4(m):
        out.update(ov)
    return {k: v for k, v in out.items() if k in prof["allowed"]}


def request_body(text: str, model: str | None = None, voice_settings: dict | None = None,
                 voice_id: str | None = None) -> dict:
    """/v1/text-to-speech 요청 본문."""
    m = resolve_model(model)
    body = {"text": text, "model_id": m,
            "voice_settings": voice_settings_for(m, voice_settings, voice_id)}
    body.update(profile(m)["extra_body"])
    return body


def style_voice(writing_style: str | None) -> str:
    ws = (writing_style or "default").lower().replace("-", "_")
    return STYLE_VOICES.get(ws, STYLE_VOICES["default"])


def strip_footnotes(text: str) -> str:
    """v4 발화문 — 각주 표시 `[1]` 만 걷는다. 원고 문장은 그대로 둔다."""
    import re
    t = re.sub(r"\[\d+\]\s*", "", text or "")
    return re.sub(r"[ \t]+", " ", t).strip()
