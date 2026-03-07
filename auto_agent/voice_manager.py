"""
음성 프리셋 관리 — voices.json 기반 CRUD.

워크스페이스 루트의 voices.json에 저장.
최초 실행 시 기본 프리셋 1개 자동 생성.
"""

import json
from pathlib import Path
from typing import List, Optional

from auto_agent.paths import get_workspace_dir

DEFAULT_VOICES = [
    {
        "name": "기본 남성",
        "voice_id": "9Sj8ugvpK1DmcAXyvi3a",
        "description": "기본 한국어 남성 (ElevenLabs)",
        "voice_settings": {
            "stability": 1.0,
            "similarity_boost": 0.6,
            "style": 0.9,
            "use_speaker_boost": True,
            "speed": 1.1,
        },
    },
]


class VoiceManager:
    def __init__(self, voices_path: Path = None):
        self.path = voices_path or get_workspace_dir() / "voices.json"

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"voices": list(DEFAULT_VOICES)}

    def _save(self, data: dict):
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def list_voices(self) -> List[dict]:
        return self._load().get("voices", [])

    def add_voice(
        self,
        name: str,
        voice_id: str,
        description: str = "",
        voice_settings: dict = None,
    ) -> dict:
        """음성 프리셋 추가. 추가된 프리셋 반환."""
        data = self._load()
        entry = {
            "name": name,
            "voice_id": voice_id,
            "description": description,
        }
        if voice_settings:
            entry["voice_settings"] = voice_settings
        data.setdefault("voices", []).append(entry)
        self._save(data)
        return entry

    def remove_voice(self, name: str) -> bool:
        """이름으로 음성 프리셋 제거. 성공 시 True."""
        data = self._load()
        voices = data.get("voices", [])
        before = len(voices)
        data["voices"] = [v for v in voices if v.get("name") != name]
        if len(data["voices"]) < before:
            self._save(data)
            return True
        return False

    def get_voice(self, name: str) -> Optional[dict]:
        """이름으로 음성 프리셋 조회."""
        for v in self.list_voices():
            if v.get("name") == name:
                return v
        return None
