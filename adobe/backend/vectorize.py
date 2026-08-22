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
            # 받은 그대로 두면 무겁다. 좌표 자릿수를 줄이고 군더더기를 걷는다 —
            # 배경 한 장이 512KB 였고, AE 에서 연속 래스터화를 켜면 배율마다
            # 그걸 다시 그리므로 눈에 띄게 느려진다.
            r = slim_svg_file(svg_path)
            if on_event and r.get("saved"):
                on_event({"layer": stem, "status": "slim",
                          "before": r["before"], "after": r["after"]})
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


# ---- SVG 다이어트 -------------------------------------------------------
#
# 리크래프트가 돌려주는 SVG 는 좌표를 소수 셋째 자리까지 적는다. 배경 한 장이
# path 924개 · 숫자 55,000개 · **512KB** 였고, 애프터이펙트에서 연속 래스터화를
# 켜면 배율마다 이걸 다시 그리므로 눈에 띄게 무거워진다.
#
# 벡터의 값어치는 확대해도 안 깨지는 것이지 소수점 셋째 자리가 아니다.
# viewBox 2048 폭을 1792 로 그리므로 **1 단위가 화면에서 0.9px** 다 —
# 소수 첫째 자리면 0.09px, 눈으로 볼 수 없다.
#
# 1 미만 값은 3자리를 남긴다. 그래디언트 정지점(offset)과 불투명도가 거기 있어
# 반올림하면 색이 튄다.

def _round_num(m, precision: int) -> str:
    v = float(m.group(0))
    p = precision if abs(v) >= 1 else 3
    s = f"{v:.{p}f}".rstrip("0").rstrip(".")
    return s or "0"


def _compact_path(d: str) -> str:
    """`d` 안의 없어도 되는 구분자를 뺀다. **파일의 85%가 여기다.**

        M 631.6 525.8 L 660.2 526.1   →   M631.6 525.8L660.2 526.1

    · 명령 글자 뒤의 공백은 필요 없다
    · 음수 앞의 공백도 필요 없다 — 마이너스가 곧 구분자다
    문법은 그대로라 모양이 바뀌지 않는다.
    """
    import re as _re
    d = _re.sub(r"\s+", " ", d).strip()
    d = _re.sub(r"([MmLlHhVvCcSsQqTtAaZz])\s+", r"\1", d)
    d = _re.sub(r"\s+([-.])", r"\1", d)
    return d


def slim_svg(text: str, *, precision: int = 1) -> str:
    """좌표 자릿수를 줄이고 군더더기 공백을 걷는다. 모양은 그대로다."""
    import re as _re
    out = _re.sub(r"-?\d+\.\d+", lambda m: _round_num(m, precision), text)
    out = _re.sub(r'd="([^"]*)"', lambda m: 'd="' + _compact_path(m.group(1)) + '"', out)
    out = _re.sub(r">\s+<", "><", out)          # 태그 사이 들여쓰기
    out = _re.sub(r"[ \t]{2,}", " ", out)
    out = _re.sub(r"\s*\n\s*", "", out)
    return out.strip()


def slim_svg_file(path, *, precision: int = 1) -> dict:
    """파일을 제자리에서 줄인다. 커지면 되돌린다(그럴 일은 없지만 확인은 싸다)."""
    p = Path(path)
    before = p.stat().st_size
    try:
        new = slim_svg(p.read_text(encoding="utf-8"), precision=precision)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    data = new.encode("utf-8")
    if len(data) >= before:
        return {"ok": True, "before": before, "after": before, "saved": 0}
    p.write_bytes(data)
    return {"ok": True, "before": before, "after": len(data),
            "saved": before - len(data)}
