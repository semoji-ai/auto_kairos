"""
ElevenLabs + Gemini TTS 래퍼

auto_kairos의 narrator.py에서 이관.
TTS 전처리(한국어 발음 교정) + ElevenLabs/Gemini TTS 생성.
"""
import json
import os
import re
import wave
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Literal
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class TTSResult:
    """TTS 생성 결과"""
    scene_number: int
    original_text: str
    processed_text: str
    audio_path: Optional[str] = None
    duration: float = 0.0
    alignment_path: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class NarrationResult:
    """전체 나레이션 결과"""
    topic: str
    total_scenes: int
    completed_scenes: int
    tts_results: List[TTSResult]
    output_dir: str
    voice_id: str
    model_id: str
    tts_provider: str = "elevenlabs"
    gemini_voice: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class TTSPreprocessor:
    """TTS 텍스트 전처리기 (한국어 발음 교정)"""

    def preprocess(self, text: str, language: str = "ko") -> str:
        if not text or not text.strip():
            return ""
        processed = self._basic_cleanup(text)
        if language != "ko":
            return processed
        if self._needs_symbol_processing(processed):
            processed = self._symbol_processing(processed)
        processed = self._hyphenate_numbers(processed)
        processed = self._korean_pronunciation_fix(processed)
        return processed.strip()

    def _basic_cleanup(self, text: str) -> str:
        processed = text.strip()
        processed = re.sub(r'^#\d+\s*', '', processed, flags=re.MULTILINE)
        processed = re.sub(r'^(장소|시간|배경|상황):\s*.*$', '', processed, flags=re.MULTILINE)
        processed = re.sub(r'\([^)]*\)', '', processed)
        processed = re.sub(r'\[[^\]]*\]', '', processed)
        processed = re.sub(r'\{[^}]*\}', '', processed)
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF\U00002600-\U000026FF\U00002700-\U000027BF]+",
            flags=re.UNICODE,
        )
        processed = emoji_pattern.sub('', processed)
        processed = re.sub(r"['\"][^'\"]+['\"]\.", lambda m: m.group(0)[1:-2] + ',', processed)
        processed = re.sub(r'[""""\'\'\'\'「」『』《》〈〉`´]', '', processed)
        processed = re.sub(r'[<>♪♫♬♭♮♯★☆♥♡※▶◀■□▲△▼▽○●◎◇◆]', '', processed)
        processed = re.sub(r'[!?]{2,}', lambda m: m.group(0)[0], processed)
        processed = re.sub(r'\.{3,}', '...', processed)
        processed = re.sub(r'^([^:]+):\s*', r'\1. ', processed, flags=re.MULTILINE)
        processed = re.sub(r'\s+', ' ', processed)
        return processed.strip()

    def _needs_symbol_processing(self, text: str) -> bool:
        return bool(re.search(r'[\d%~.·&/+=]', text))

    def _number_to_korean_sino(self, num: int) -> str:
        if num == 0:
            return '영'
        units = ['', '십', '백', '천']
        digits = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
        result = ''
        str_num = str(num)
        length = len(str_num)
        for i, char in enumerate(str_num):
            digit = int(char)
            unit_idx = length - i - 1
            if digit == 0:
                continue
            if digit == 1 and unit_idx > 0:
                result += units[unit_idx]
            else:
                result += digits[digit] + units[unit_idx]
        return result

    def _symbol_processing(self, text: str) -> str:
        text = re.sub(r'(\d+)\s*%', r'\1 퍼센트', text)

        def convert_decimal(match):
            int_korean = self._number_to_korean_sino(int(match.group(1)))
            dec_digits = ''.join(
                ['영', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구'][int(d)]
                for d in match.group(2)
            )
            return f'{int_korean}쩜{dec_digits}'
        text = re.sub(r'(\d+)\.(\d+)(?=[^.]|$)', convert_decimal, text)

        text = re.sub(r'(\d+)\s*~\s*(\d+)', r'\1에서\2', text)
        text = re.sub(r'(\w)\s*&\s*(\w)', r'\1앤\2', text)

        # 영어 약어
        abbreviations = {
            r'\bAI\b': '에이아이', r'\bAPI\b': '에이피아이',
            r'\bCEO\b': '씨이오', r'\bIT\b': '아이티',
            r'\bGDP\b': '지디피', r'\bIMF\b': '아이엠에프',
            r'\bOLED\b': '올레드', r'\bLED\b': '엘이디',
            r'\b5G\b': '파이브지', r'\b4G\b': '포지',
        }
        for pattern, replacement in abbreviations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 영어 단어 뒤 한글 조사 분리
        korean_josa = r'[은는이가을를와과의로에서도만]'
        text = re.sub(rf'([a-zA-Z]+)({korean_josa})', r'\1-\2', text)

        return text

    def _hyphenate_numbers(self, text: str) -> str:
        """다자리 숫자를 자릿값 하이픈으로 분리 (예: 546만명 → 5백-4십-6만명)"""
        # 콤마 제거 (69,000 → 69000)
        text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
        text = re.sub(r'(\d),(\d{3})', r'\1\2', text)

        def decompose(n):
            """숫자를 한글 자릿값 분해 (9999 이하)"""
            if n <= 0:
                return ''
            units = ['', '십', '백', '천']
            ko_digits = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
            parts = []
            tmp = n
            pos = 0
            while tmp > 0:
                digit = tmp % 10
                if digit > 0:
                    # 일십/일백/일천 → 십/백/천 (digit 1이고 단위가 있을 때 '일' 생략)
                    if digit == 1 and pos > 0:
                        parts.append(units[pos])
                    else:
                        parts.append(f'{ko_digits[digit]}{units[pos]}')
                tmp //= 10
                pos += 1
            parts.reverse()
            return '-'.join(parts)

        def hyphenate(match):
            num_str = match.group(1)
            suffix = match.group(2)
            num = int(num_str)

            if num < 100:
                return num_str + suffix

            parts = []

            # 억 단위 (1억 = 100,000,000)
            if num >= 100000000:
                eok = num // 100000000
                num %= 100000000
                parts.append(f'{decompose(eok)}억')

            # 만 단위 (1만 = 10,000)
            if num >= 10000:
                man = num // 10000
                num %= 10000
                parts.append(f'{decompose(man)}만')

            # 천 이하
            if num > 0:
                parts.append(decompose(num))

            if not parts:
                return num_str + suffix

            return '-'.join(parts) + suffix

        text = re.sub(r'(\d{2,})([\uAC00-\uD7AF]*)', hyphenate, text)
        return text

    def _korean_pronunciation_fix(self, text: str) -> str:
        # 가격(價) '가' → '까'
        text = text.replace('장난감', '장난깜')
        text = text.replace('신기록', '신끼록')
        # 삼만/삼천/삼백 발음 오류 방지
        text = re.sub(r"(?<!')삼만", "'삼'만", text)
        text = re.sub(r"(?<!')삼천", "'삼'천", text)
        text = re.sub(r"(?<!')삼백", "'삼'백", text)
        # 복합어 발음 교정: 최고지도자 → TTS가 '최고지도자'를 한 덩어리로 너무 빨리 읽음
        text = text.replace('최고지도자', '최-고-지도자')
        # 금액 연음 (제거: 오히려 어색함)
        return text


class ElevenLabsClient:
    """ElevenLabs TTS 클라이언트"""

    def __init__(
        self,
        tts_provider: Literal["elevenlabs", "gemini"] = "elevenlabs",
        elevenlabs_api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict] = None,
        gemini_api_key: Optional[str] = None,
        gemini_voice: str = "Enceladus",
    ):
        self.tts_provider = tts_provider

        # ElevenLabs
        self.api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "9Sj8ugvpK1DmcAXyvi3a")
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        self.voice_settings = voice_settings or {
            "stability": 1.0,
            "similarity_boost": 0.6,
            "style": 0.9,
            "use_speaker_boost": True,
            "speed": 1.1,
        }

        # Gemini TTS
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY", "")
        self.gemini_voice = gemini_voice
        self.gemini_client = None
        if self.tts_provider == "gemini" and self.gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except ImportError:
                pass

        self.preprocessor = TTSPreprocessor()

    def _generate_tts_elevenlabs(self, text: str, output_path: Path) -> float:
        import base64
        import requests
        headers = {"Content-Type": "application/json", "xi-api-key": self.api_key}
        body = {"text": text, "model_id": self.model_id, "voice_settings": self.voice_settings}

        # /with-timestamps 엔드포인트 시도
        try:
            url_ts = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/with-timestamps?output_format=mp3_44100_128"
            response = requests.post(url_ts, headers=headers, json=body)
            if not response.ok:
                raise Exception(f"with-timestamps API 오류: {response.status_code}")
            response_json = response.json()
            audio_bytes = base64.b64decode(response_json["audio_base64"])
            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            # 사이드카 타임스탬프 저장
            alignment = response_json.get("alignment", {})
            sidecar = {
                "characters": alignment.get("characters", []),
                "character_start_times_seconds": alignment.get("character_start_times_seconds", []),
                "character_end_times_seconds": alignment.get("character_end_times_seconds", []),
            }
            timestamps_path = output_path.with_name(output_path.stem + ".timestamps.json")
            with open(timestamps_path, "w", encoding="utf-8") as f:
                json.dump(sidecar, f, ensure_ascii=False, indent=2)

            # 타임스탬프 마지막 값 = 실제 발화 종료 시각 (가장 정확)
            end_times = alignment.get("character_end_times_seconds", [])
            if end_times:
                duration = round(end_times[-1], 3)
            else:
                try:
                    from mutagen.mp3 import MP3
                    duration = MP3(str(output_path)).info.length
                except Exception:
                    duration = len(audio_bytes) * 8 / 128000  # fallback
            return duration

        except Exception:
            # 폴백: 원래 엔드포인트
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}?output_format=mp3_44100_128"
            response = requests.post(url, headers=headers, json=body)
            if not response.ok:
                raise Exception(f"ElevenLabs API 오류: {response.status_code}")
            with open(output_path, "wb") as f:
                f.write(response.content)
            return (len(response.content) * 8) / 128000

    def _generate_tts_gemini(self, text: str, output_path: Path) -> float:
        from google.genai import types
        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.gemini_voice,
                        )
                    )
                ),
            ),
        )
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)
        return len(audio_data) / (24000 * 2)

    def generate_tts(self, text: str, output_path: Path, language: str = "ko") -> float:
        """TTS 생성 (전처리 포함)"""
        processed = self.preprocessor.preprocess(text, language)
        if self.tts_provider == "gemini" and self.gemini_client:
            return self._generate_tts_gemini(processed, output_path)
        return self._generate_tts_elevenlabs(processed, output_path)

    def generate_from_storyboard(
        self, storyboard_path: Path, output_dir: Path,
        language: str = "ko", skip_existing: bool = True,
        max_workers: int = 5,
    ) -> NarrationResult:
        """스토리보드에서 일괄 TTS 생성"""
        with open(storyboard_path, "r", encoding="utf-8") as f:
            storyboard = json.load(f)

        topic = storyboard.get("project_title", storyboard.get("topic", ""))

        # 챕터별 씬을 평면화 (또는 직접 scenes 배열 사용)
        scenes = []
        if "chapters" in storyboard:
            for chapter in storyboard.get("chapters", []):
                scenes.extend(chapter.get("scenes", []))
        elif "scenes" in storyboard:
            scenes = storyboard.get("scenes", [])
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        tts_results = []
        completed_count = 0
        results_lock = threading.Lock()

        def process_scene(scene):
            nonlocal completed_count
            # scene_number 필드가 없으면 scene_id에서 추출 (scene_001 → 1)
            scene_number = scene.get("scene_number")
            if scene_number is None:
                scene_id = scene.get("scene_id", "scene_000")
                scene_number = int(scene_id.split("_")[-1])
            original_text = scene.get("original_script_text", "")
            if not original_text.strip():
                return None

            processed_text = scene.get("processed_script_text", "")
            if not processed_text:
                processed_text = self.preprocessor.preprocess(original_text, language)

            result = TTSResult(
                scene_number=scene_number,
                original_text=original_text,
                processed_text=processed_text,
            )

            ext = "wav" if self.tts_provider == "gemini" else "mp3"
            audio_path = audio_dir / f"scene_{scene_number:03d}.{ext}"

            if skip_existing and audio_path.exists():
                result.audio_path = str(audio_path)
                result.status = "completed"
                with results_lock:
                    completed_count += 1
                return result

            try:
                if self.tts_provider == "gemini" and self.gemini_client:
                    duration = self._generate_tts_gemini(processed_text, audio_path)
                else:
                    duration = self._generate_tts_elevenlabs(processed_text, audio_path)
                    timestamps_path = audio_path.with_name(audio_path.stem + ".timestamps.json")
                    result.alignment_path = str(timestamps_path) if timestamps_path.exists() else None
                result.audio_path = str(audio_path)
                result.duration = duration
                result.status = "completed"
                with results_lock:
                    completed_count += 1
            except Exception as e:
                result.status = "failed"
                result.error_message = str(e)
            return result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_scene, s): s for s in scenes}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    tts_results.append(result)

        tts_results.sort(key=lambda x: x.scene_number)

        narration_result = NarrationResult(
            topic=topic,
            total_scenes=len(tts_results),
            completed_scenes=completed_count,
            tts_results=tts_results,
            output_dir=str(output_dir),
            voice_id=self.voice_id if self.tts_provider == "elevenlabs" else "",
            model_id=self.model_id if self.tts_provider == "elevenlabs" else "gemini-tts",
            tts_provider=self.tts_provider,
            gemini_voice=self.gemini_voice if self.tts_provider == "gemini" else "",
        )

        result_path = output_dir / "tts_results.json"
        narration_result.save(result_path)
        return narration_result
