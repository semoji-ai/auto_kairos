"""Discord Bot API를 이용한 스레드 기반 알림.

웹훅 대신 봇 토큰으로 스레드 생성 + 메시지 전송.
Stage 0/4 크론 실행마다 스레드 1개 생성, 과정+결과를 스레드에 기록.
"""
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


class DiscordBotNotify:
    """Discord Bot 토큰 기반 알림 — 스레드 생성 지원."""

    def __init__(self, channel_id: str, bot_token: Optional[str] = None):
        self._channel_id = channel_id
        self._token = bot_token or os.getenv("KAIROS_DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN", "")
        if not self._token:
            # 플러그인 .env에서 가져오기
            plugin_env = os.path.expanduser("~/.claude/channels/discord/.env")
            if os.path.exists(plugin_env):
                for line in open(plugin_env):
                    if line.startswith("DISCORD_BOT_TOKEN="):
                        self._token = line.split("=", 1)[1].strip()
                        break

        self._headers = {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
        }
        self._thread_id: Optional[str] = None

    def create_thread(self, name: str) -> Optional[str]:
        """채널에 스레드 생성. 스레드 ID 반환."""
        # 먼저 시작 메시지를 보내고 그 메시지에 스레드 생성
        msg = self._send_message(self._channel_id, f"🧵 **{name}**")
        if not msg:
            return None

        url = f"{DISCORD_API}/channels/{self._channel_id}/messages/{msg['id']}/threads"
        payload = {
            "name": name[:100],  # 스레드 이름 100자 제한
            "auto_archive_duration": 1440,  # 24시간 후 자동 아카이브
        }
        try:
            resp = requests.post(url, json=payload, headers=self._headers, timeout=10)
            if resp.status_code in (200, 201):
                thread = resp.json()
                self._thread_id = thread["id"]
                logger.info("스레드 생성: %s (%s)", name, self._thread_id)
                return self._thread_id
            else:
                logger.warning("스레드 생성 실패: %s %s", resp.status_code, resp.text[:200])
                return None
        except Exception as e:
            logger.warning("스레드 생성 에러: %s", e)
            return None

    def send_to_thread(self, message: str):
        """현재 스레드에 메시지 전송. 스레드가 없으면 채널에 전송."""
        target = self._thread_id or self._channel_id
        self._send_message(target, message)

    def send_to_channel(self, message: str):
        """채널에 직접 메시지 전송."""
        self._send_message(self._channel_id, message)

    def _send_message(self, channel_id: str, content: str) -> Optional[dict]:
        """메시지 전송. 2000자 제한 자동 분할."""
        url = f"{DISCORD_API}/channels/{channel_id}/messages"
        chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
        last_msg = None
        for chunk in chunks:
            try:
                resp = requests.post(url, json={"content": chunk},
                                     headers=self._headers, timeout=10)
                if resp.status_code in (200, 201):
                    last_msg = resp.json()
                elif resp.status_code == 429:
                    # Rate limit
                    retry_after = resp.json().get("retry_after", 1)
                    logger.warning("Rate limited, waiting %.1fs", retry_after)
                    time.sleep(retry_after)
                    resp = requests.post(url, json={"content": chunk},
                                         headers=self._headers, timeout=10)
                    if resp.status_code in (200, 201):
                        last_msg = resp.json()
                else:
                    logger.warning("메시지 전송 실패: %s %s", resp.status_code, resp.text[:200])
            except Exception as e:
                logger.warning("메시지 전송 에러: %s", e)
        return last_msg

    @property
    def thread_id(self) -> Optional[str]:
        return self._thread_id
