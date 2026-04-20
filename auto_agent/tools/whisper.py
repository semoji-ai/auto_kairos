"""
OpenAI Whisper STT 래퍼

auto_kairos의 subtitle_sync.py에서 이관.
Whisper API로 단어 단위 타임스탬프 분석.
"""
import os
import re
import httpx
import difflib
from pathlib import Path
from typing import Optional, List, Dict
from statistics import variance, mean

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class WhisperClient:
    """OpenAI Whisper STT 클라이언트"""

    def __init__(self, api_key: Optional[str] = None, language: str = "ko"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.language = language

        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def analyze_audio(self, audio_source: str) -> Dict:
        """
        Whisper API로 오디오 타임스탬프 분석

        Args:
            audio_source: 오디오 파일 경로 또는 URL

        Returns:
            {"text": str, "words": [...], "segments": [...], "duration": float}
        """
        if not self.client:
            raise RuntimeError("OpenAI 라이브러리 또는 API 키가 없습니다.")

        is_local_file = os.path.exists(audio_source)
        temp_path = None

        if is_local_file:
            audio_path = audio_source
        else:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(audio_source)
                response.raise_for_status()

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(response.content)
                temp_path = f.name
            audio_path = temp_path

        try:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    language=self.language,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"],
                )

            return {
                "text": transcription.text,
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end}
                    for w in (transcription.words or [])
                ],
                "segments": [
                    {"text": s.text, "start": s.start, "end": s.end}
                    for s in (transcription.segments or [])
                ],
                "duration": transcription.duration or 0,
            }
        finally:
            if temp_path:
                os.unlink(temp_path)

    def verify_tts(self, original_text: str, audio_source: str) -> Dict:
        """TTS 품질 검증"""
        whisper_result = self.analyze_audio(audio_source)
        recognized_text = whisper_result.get("text", "")
        duration = whisper_result.get("duration", 0)
        segments = whisper_result.get("segments", [])

        original_clean = re.sub(r'\s+', ' ', original_text).strip()
        recognized_clean = re.sub(r'\s+', ' ', recognized_text).strip()
        similarity = difflib.SequenceMatcher(None, original_clean, recognized_clean).ratio()

        char_count = len(original_clean.replace(" ", ""))
        chars_per_sec = char_count / duration if duration > 0 else 0

        pauses = []
        if len(segments) > 1:
            for i in range(1, len(segments)):
                gap = segments[i]["start"] - segments[i - 1]["end"]
                if gap > 0:
                    pauses.append(gap)

        issues = []
        if similarity < 0.8:
            issues.append(f"텍스트 일치율 낮음: {similarity:.1%}")
        if chars_per_sec < 4:
            issues.append(f"발화 속도 느림: {chars_per_sec:.1f} 글자/초")
        elif chars_per_sec > 9:
            issues.append(f"발화 속도 빠름: {chars_per_sec:.1f} 글자/초")

        status = "ERROR" if similarity < 0.7 else ("WARNING" if similarity < 0.9 else "OK")

        return {
            "similarity": similarity,
            "duration": duration,
            "chars_per_sec": chars_per_sec,
            "avg_pause": mean(pauses) if pauses else 0,
            "issues": issues,
            "status": status,
        }
