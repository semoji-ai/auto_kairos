"""ElevenLabs TTS + character timestamps 어댑터 (L3 — v3 의존 0).

vendored: `_vendor/elevenlabs_v3.py` + `_vendor/korean_tts_preprocessor.py`
v3 폴더 없는 머신에서도 동작.

이식된 규칙:
- 한국어 전처리 80+ 패턴(숫자/연도/단위/영문 약어/외래어/마크다운 마커)
- `with-timestamps` 엔드포인트 우선 사용 → character-level alignment 동시 수신
- 기본 voice_id `9Sj8ugvpK1DmcAXyvi3a`, 모델 `eleven_multilingual_v2`
- 환경 변수 ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID / ELEVENLABS_MODEL_ID
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path

from ._vendor.elevenlabs_v3 import ElevenLabsClient


def is_available() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


@dataclass
class TTSOutput:
    audio_path: Path
    timestamps_path: Path
    meta_path: Path
    duration_ms: int


def synth(
    text: str,
    out_dir: Path,
    *,
    unit_id: str,
    voice_id: str | None = None,
    model_id: str | None = None,
    apply_korean_preprocessing: bool = True,
) -> TTSOutput:
    """unit 텍스트 → mp3 + timestamps.json + meta.json.

    text는 원문(전처리 전). apply_korean_preprocessing=True 시 vendored KoreanTTSPreprocessor 적용.
    timestamps.json은 character 단위 alignment를 1차 데이터로 보존, words/sentences 보조 집계.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    original = text
    if apply_korean_preprocessing:
        from ._vendor.korean_tts_preprocessor import KoreanTTSPreprocessor
        pre = KoreanTTSPreprocessor()
        processed, _changes = pre.process_text(text)
    else:
        processed = text

    client = ElevenLabsClient(voice_id=voice_id, model_id=model_id)
    audio_path = out_dir / f"{unit_id}.mp3"
    duration_s = client.generate_preprocessed_tts(processed, audio_path)

    alignment_sidecar = audio_path.with_suffix(".alignment.json")
    characters: list[dict] = []
    if alignment_sidecar.exists():
        try:
            data = json.loads(alignment_sidecar.read_text(encoding="utf-8"))
            chars = data.get("characters", [])
            starts = data.get("character_start_times_seconds", [])
            ends = data.get("character_end_times_seconds", [])
            for c, s, e in zip(chars, starts, ends):
                characters.append({"char": c, "start_ms": int(s * 1000), "end_ms": int(e * 1000)})
        except (json.JSONDecodeError, OSError):
            pass

    duration_ms = int(duration_s * 1000)
    timestamps = {
        "unit_id": unit_id,
        "model": client.model_id,
        "duration_ms": duration_ms,
        "characters": characters,
        "words": _aggregate_words(characters, processed),
        "sentences": _aggregate_sentences(characters, processed),
    }
    timestamps_path = out_dir / f"{unit_id}.timestamps.json"
    timestamps_path.write_text(json.dumps(timestamps, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "unit_id": unit_id,
        "model": client.model_id,
        "voice_id": client.voice_id,
        "settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "speaker_boost": True, "speed": 1.0},
        "preprocessing_applied": {"korean_pronunciation": apply_korean_preprocessing},
        "input_text": processed,
        "original_text": original,
    }
    meta_path = out_dir / f"{unit_id}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return TTSOutput(audio_path=audio_path, timestamps_path=timestamps_path, meta_path=meta_path, duration_ms=duration_ms)


def _aggregate_words(characters: list[dict], text: str) -> list[dict]:
    """character 시퀀스에서 공백·구두점 기준 word 집계."""
    if not characters:
        return []
    words = []
    cur = []
    cur_start = None
    for i, ch in enumerate(characters):
        c = ch.get("char", "")
        if c.strip() and c not in ".,!?;:":
            if cur_start is None:
                cur_start = ch["start_ms"]
            cur.append((c, ch["end_ms"], i))
        else:
            if cur:
                text_chunk = "".join(x[0] for x in cur)
                words.append({"text": text_chunk, "start_ms": cur_start, "end_ms": cur[-1][1],
                              "char_range": [cur[0][2], cur[-1][2] + 1]})
                cur = []
                cur_start = None
    if cur:
        text_chunk = "".join(x[0] for x in cur)
        words.append({"text": text_chunk, "start_ms": cur_start, "end_ms": cur[-1][1],
                      "char_range": [cur[0][2], cur[-1][2] + 1]})
    return words


def _aggregate_sentences(characters: list[dict], text: str) -> list[dict]:
    """문장 종결(./!/?) 기준 집계."""
    if not characters:
        return []
    sentences = []
    cur = []
    cur_start = None
    for i, ch in enumerate(characters):
        c = ch.get("char", "")
        if cur_start is None and c.strip():
            cur_start = ch["start_ms"]
        cur.append((c, ch["end_ms"], i))
        if c in ".!?":
            if cur and cur_start is not None:
                text_chunk = "".join(x[0] for x in cur).strip()
                sentences.append({"text": text_chunk, "start_ms": cur_start, "end_ms": cur[-1][1],
                                  "char_range": [cur[0][2], cur[-1][2] + 1]})
                cur = []
                cur_start = None
    if cur and cur_start is not None:
        text_chunk = "".join(x[0] for x in cur).strip()
        if text_chunk:
            sentences.append({"text": text_chunk, "start_ms": cur_start, "end_ms": cur[-1][1],
                              "char_range": [cur[0][2], cur[-1][2] + 1]})
    return sentences
