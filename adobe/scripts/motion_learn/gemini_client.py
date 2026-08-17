"""gemini File API 공유 클라이언트 — analyze(단일 영상)/verify(듀얼 영상) 공용.
모델 폴백 + JSON 응답. 단일 client로 업로드·생성을 묶어 파일 핸들 유효성 보장."""
from __future__ import annotations

import json
import time

DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]


def _client():
    from google import genai
    return genai.Client()


def _upload(client, path: str):
    f = client.files.upload(file=path)
    while f.state.name == "PROCESSING":
        time.sleep(5)
        f = client.files.get(name=f.name)
    return f


def _generate_json(client, contents: list, models=None) -> dict:
    from google.genai import errors, types
    cfg = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000)
    last = None
    for m in (models or DEFAULT_MODELS):
        try:
            resp = client.models.generate_content(model=m, contents=contents, config=cfg)
            return json.loads(resp.text)
        except (errors.ServerError, json.JSONDecodeError) as e:
            last = e
            continue
    raise RuntimeError("gemini 생성 실패: " + str(last))


def analyze_video(mp4_path: str, prompt: str, *, models=None) -> dict:
    client = _client()
    f = _upload(client, mp4_path)
    return _generate_json(client, [f, prompt], models=models)


def compare_videos(path_a: str, path_b: str, prompt: str, *, models=None) -> dict:
    client = _client()
    fa = _upload(client, path_a)
    fb = _upload(client, path_b)
    return _generate_json(client, [fa, fb, prompt], models=models)
