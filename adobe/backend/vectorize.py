"""Recraft vectorize API 호출 — 레이어 PNG를 SVG로.

목적은 AE에서 확대해도 깨지지 않는 레이어다. SVG를 얹은 뒤 연속 래스터화를 켜야
효과가 나며 그 처리는 build_scene.jsx가 한다.

새 의존성 없이 stdlib urllib만 쓴다(fal_api.py와 같은 방식).
"""
from __future__ import annotations

import json
import mimetypes
import urllib.request
import uuid
from pathlib import Path

from backend import env

ENDPOINT = "https://external.api.recraft.ai/v1/images/vectorize"
KEY_NAME = "RECRAFT_API_KEY"
# 결과 URL은 브라우저 User-Agent를 요구한다 — 없으면 HTTP 403이 난다(실측).
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class VectorizeError(Exception):
    """벡터화 실패 — 키 없음·비200·응답 이상·내려받기 실패."""


def api_key() -> str:
    return env.get_key(KEY_NAME)


def _multipart(fields: dict, file_field: str, data: bytes, filename: str) -> tuple:
    """stdlib만으로 multipart/form-data 조립 — (body, content_type)."""
    boundary = "----ak" + uuid.uuid4().hex
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts = []
    for k, v in fields.items():
        parts.append(
            ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
             % (boundary, k, v)).encode("utf-8"))
    parts.append(
        ('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
         'Content-Type: %s\r\n\r\n' % (boundary, file_field, filename, mime)).encode("utf-8"))
    parts.append(data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def vectorize_png(png_path, *, timeout: int = 300) -> bytes:
    """PNG 1장을 SVG 바이트로. 실패 시 VectorizeError.

    키 값은 어떤 메시지에도 넣지 않는다."""
    key = api_key()
    if not key:
        raise VectorizeError(f"{KEY_NAME} 없음 — .env 또는 환경변수에 넣어 주세요")
    src = Path(png_path)
    if not src.is_file():
        raise VectorizeError(f"이미지 없음: {src.name}")
    body, ctype = _multipart({"response_format": "url"}, "file", src.read_bytes(), src.name)
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except VectorizeError:
        raise
    except Exception as e:
        raise VectorizeError(f"벡터화 호출 실패: {str(e)[:200]}") from e
    # 응답이 dict인지 검증 (dict가 아니면 .get() 호출 시 AttributeError)
    if not isinstance(data, dict):
        raise VectorizeError(f"응답 형식 오류(dict 필요): {str(data)[:200]}")
    url = ((data.get("image") or {}).get("url") or data.get("url") or "").strip()
    if not url:
        raise VectorizeError(f"응답에 SVG URL 없음: {str(data)[:200]}")
    dl = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA,
                                              "Accept": "image/svg+xml,*/*"})
    try:
        with urllib.request.urlopen(dl, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        raise VectorizeError(f"SVG 내려받기 실패: {str(e)[:200]}") from e


def vectorize_layers(proj_dir, sid: str, stems: list, *, subdir: str = "layers",
                     force: bool = False, on_event=None) -> dict:
    """여러 레이어를 차례로 벡터화한다. 한 장이 실패해도 나머지를 계속 처리한다.

    이미 .svg가 있거나 제거된 레이어는 건너뛴다(force면 기존 SVG를 덮어쓴다).
    반환 {"ok": [stem...], "skipped": [stem...], "failed": [{"layer", "error"}...]}."""
    from backend import imagegen
    out_base = Path(proj_dir) / subdir
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(out_base, sid)}
    ok, skipped, failed = [], [], []
    for raw in stems or []:
        stem = Path(str(raw)).stem
        svg_path = out_base / (stem + ".svg")
        if (specs.get(stem) or {}).get("removed"):
            skipped.append(stem)
            continue
        if svg_path.is_file() and not force:
            skipped.append(stem)
            continue
        png_path = out_base / (stem + ".png")
        if not png_path.is_file():
            failed.append({"layer": stem, "error": f"이미지 없음: {stem}.png"})
            if on_event:
                on_event({"layer": stem, "status": "failed", "error": f"이미지 없음: {stem}.png"})
            continue
        try:
            data = vectorize_png(png_path)
            svg_path.write_bytes(data)
        except Exception as e:
            # 예상 외 예외도 한 장의 실패로 처리 (다음 레이어 계속)
            # 예외 타입을 메시지에 포함해 원인 추적 가능하게
            error_msg = f"{type(e).__name__}: {str(e)}"[:200]
            failed.append({"layer": stem, "error": error_msg})
            if on_event:
                on_event({"layer": stem, "status": "failed", "error": error_msg})
            continue
        ok.append(stem)
        if on_event:
            on_event({"layer": stem, "status": "completed"})
    return {"ok": ok, "skipped": skipped, "failed": failed}
