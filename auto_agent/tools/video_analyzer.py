"""
Gemini Video API로 mp4 분석 → 타임스탬프별 장면 JSON 반환

사용법:
    from auto_agent.tools.video_analyzer import analyze_video
    result = analyze_video(Path("video.mp4"))
    # result = {"duration_sec": 61.0, "scenes": [{"start": 0.0, "end": 3.0, "description": "...", "tags": [...]}]}
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    from google.genai import types as gtypes
except ImportError as e:
    raise ImportError("google-genai 패키지 필요: pip install google-genai") from e

_client: "genai.Client | None" = None

def _get_client() -> "genai.Client":
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


ANALYZE_PROMPT = """이 영상을 분석해서 장면별 타임스탬프 데이터를 JSON으로 반환하세요.

규칙:
- 의미 있는 장면 전환마다 새 항목 생성 (최소 1초 단위)
- description은 한국어로 영상 내용을 구체적으로 묘사
- tags는 영상에 등장하는 핵심 요소 (캐릭터명, 행동, 장소 등 영어 소문자)

아래 JSON 형식으로만 응답 (다른 텍스트 없이):
{
  "duration_sec": 영상_총_길이_초,
  "language": "ja 또는 en 또는 ko",
  "scenes": [
    {
      "start": 시작_초,
      "end": 종료_초,
      "description": "장면 한국어 설명",
      "tags": ["tag1", "tag2"]
    }
  ]
}"""


def _gemini_generate(video_bytes: bytes, mime_type: str) -> "gtypes.GenerateContentResponse":
    """내부 헬퍼 — 테스트에서 mock 대상."""
    client = _get_client()
    return client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            gtypes.Part.from_bytes(data=video_bytes, mime_type=mime_type),
            ANALYZE_PROMPT,
        ],
    )


def _gemini_generate_large(video_path: Path, mime_type: str) -> "gtypes.GenerateContentResponse":
    """20MB 초과 영상용 — File API 업로드 후 분석."""
    client = _get_client()
    uploaded = client.files.upload(
        file=str(video_path),
        config=gtypes.UploadFileConfig(mime_type=mime_type),
    )
    for _ in range(30):
        if uploaded.state != "PROCESSING":
            break
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state == "FAILED":
        raise RuntimeError(f"Gemini 파일 업로드 실패: {uploaded.name}")
    try:
        return client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                gtypes.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type),
                ANALYZE_PROMPT,
            ],
        )
    finally:
        client.files.delete(name=uploaded.name)


def analyze_video(video_path: Path) -> dict:
    """mp4/webm 영상을 Gemini로 분석하여 장면 타임스탬프 dict 반환."""
    suffix = video_path.suffix.lower()
    mime_map = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}
    mime_type = mime_map.get(suffix, "video/mp4")

    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    if file_size_mb <= 19:
        video_bytes = video_path.read_bytes()
        response = _gemini_generate(video_bytes, mime_type)
    else:
        response = _gemini_generate_large(video_path, mime_type)

    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)
