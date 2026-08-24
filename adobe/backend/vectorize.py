"""Recraft vectorize API 호출 — 레이어 PNG를 SVG로.

목적은 AE에서 확대해도 깨지지 않는 레이어다. SVG를 얹은 뒤 연속 래스터화를 켜야
효과가 나며 그 처리는 build_scene.jsx가 한다.

새 의존성 없이 stdlib urllib만 쓴다(fal_api.py와 같은 방식).
"""
from __future__ import annotations

import json
import os
import re
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


# 벡터화에 넣을 원본의 가로 상한. **기본은 끔(0).**
#
# 「원본을 줄여 넣으면 SVG 도 작아지지 않겠나」를 실제로 재 봤는데 아니었다.
# 리크래프트가 내부에서 정규화하는지, 넣는 해상도를 3분의 1로 줄여도 결과가
# 거의 같다.
#
#     넣은 가로   SVG      path
#     1792(원본)  512KB    924
#     1200        512KB    986
#      900        519KB   1001
#      600        473KB    884     ← 8% 줄자고 화질을 버릴 값어치가 없다
#
# 색을 줄이는 것은 **더 나빴다** — 띠가 생겨 면이 잘게 쪼개진다.
#
#     32색  712KB · path 1337
#     16색  740KB · path 1411
#
# 무게를 정하는 것은 해상도도 색 수도 아니라 **그림의 결**이다. 종이 질감이
# 깔린 배경판은 어떻게 넣어도 path 가 900개 넘게 나온다.
# 그래서 진짜 답은 **배경을 벡터화하지 않는 것**이다(요소는 10~40KB 로 가볍다).
#
# 넣는 값을 바꿔 보고 싶을 때를 위해 손잡이만 남긴다.
VECTORIZE_MAX_W = int(os.environ.get("AK_VECTORIZE_MAX_W", "0"))

# SVG 를 선언 크기의 몇 분의 1로 들여올지. **기본 1 — 나누지 않는다.**
#
# ⚠️ 한때 10 이었고, 그것이 「벡터화한 SVG 가 컴프에 안 보인다」의 뿌리였다.
# 작게 선언하려면 그림 좌표를 그만큼 줄여야 하는데, 좌표를 직접 곱하면 색
# 값까지 곱해져 무너지므로 `<g transform>` 으로 감쌌다. 렌더러는 그 변환을
# 따라가지만 **애프터이펙트의 「쉐이프로 펴기」는 따라가지 않는다.** 2048
# 좌표계의 패스가 77×87 창에 들어가 통째로 창 밖으로 나갔다 — 화면에는
# 배경만 남았다(배경은 펴지 않으므로 멀쩡했고, 그래서 원인이 오래 가려졌다).
#
# 무게를 줄이자고 켠 손잡이 하나가 기능 자체를 죽였다. 되돌린다.
#
# 벡터라 확대해도 깨지지 않으니 작게 들여와 배율로 키우면 AE 가 가볍다.
# 배치는 매니페스트가 SVG 머리말을 직접 읽어 맞추므로 자리는 어긋나지 않고,
# PNG 로 대체될 때는 build_scene.jsx 가 그 배율을 되돌린다.
#
# ⚠️ **연속 래스터화가 꺼지면 그대로 흐려진다.** 벡터 레이어에는
# `collapseTransformation` 을 켜 두지만, 그 스위치는 블렌딩 모드와 일부
# 이펙트를 무시하므로 사람이 끄는 일이 있다. 흐리게 보이면 그 스위치부터
# 확인하고, 그래도 안 되면 AK_VECTORIZE_DIVISOR=1 로 되돌린다.
VECTORIZE_DIVISOR = max(1, int(os.environ.get("AK_VECTORIZE_DIVISOR", "1")))

# 정규화를 아예 끄고 리크래프트 산출 그대로 두기 — 문제를 가를 때 쓴다.
VECTORIZE_NORMALIZE = os.environ.get("AK_VECTORIZE_NORMALIZE", "1") != "0"


def _downscaled(src: Path, max_w: int) -> tuple:
    """가로가 상한을 넘으면 줄인 바이트를 돌려준다. (바이트, 원래크기, 넣은크기)"""
    raw = src.read_bytes()
    if max_w <= 0:
        return raw, None, None
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(raw)) as im:
            w, h = im.size
            if w <= max_w:
                return raw, (w, h), (w, h)
            nh = max(1, round(h * max_w / w))
            buf = io.BytesIO()
            im.convert("RGBA").resize((max_w, nh), Image.LANCZOS).save(buf, "PNG")
            return buf.getvalue(), (w, h), (max_w, nh)
    except Exception:
        return raw, None, None       # 못 줄이면 원본 그대로 — 막지는 않는다


def vectorize_png(png_path, *, timeout: int = 300, max_w: int | None = None,
                  on_line=None) -> bytes:
    """PNG 1장을 SVG 바이트로. 실패 시 VectorizeError.

    키 값은 어떤 메시지에도 넣지 않는다."""
    key = api_key()
    if not key:
        raise VectorizeError(f"{KEY_NAME} 없음 — .env 또는 환경변수에 넣어 주세요")
    src = Path(png_path)
    if not src.is_file():
        raise VectorizeError(f"이미지 없음: {src.name}")
    raw, was, now = _downscaled(src, VECTORIZE_MAX_W if max_w is None else max_w)
    if on_line and was and now and was != now:
        on_line(f"  줄여서 넣습니다 {was[0]}x{was[1]} → {now[0]}x{now[1]}")
    body, ctype = _multipart({"response_format": "url"}, "file", raw, src.name)
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
            # **좌표계를 먼저 맞춘다.** 리크래프트 SVG 는 선언 크기와 viewBox 가
            # 달라(582x850 인데 viewBox 는 1402x2048), AE 가 어느 쪽을 footage
            # 크기로 읽느냐에 따라 배치가 2.4배 어긋난다.
            if VECTORIZE_NORMALIZE:
                normalize_svg_file(svg_path, divisor=VECTORIZE_DIVISOR)
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
    """좌표 자릿수를 줄이고 군더더기 공백을 걷는다.

    **`d` 안에서만 숫자를 건드린다.** 처음에는 본문의 모든 숫자를 반올림했는데,
    그러면 `rgb(245,222,193)` 의 색 값과 그래디언트 정지점·불투명도까지 걸린다.
    줄일 것은 좌표뿐이다 — 색은 손대지 않는다.
    """
    import re as _re

    def _one(m):
        d = m.group(1)
        d = _re.sub(r"-?\d+\.\d+", lambda x: _round_num(x, precision), d)
        return 'd="' + _compact_path(d) + '"'

    out = _re.sub(r'd="([^"]*)"', _one, text)
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


# ---- 좌표계 정규화 ------------------------------------------------------
#
# 리크래프트 SVG 는 **선언 크기와 viewBox 가 다르다.**
#
#     width="582" height="850"   viewBox="0 0 1402 2048"
#
# 애프터이펙트가 둘 중 어느 쪽을 footage 크기로 읽는지에 따라 배치가 2.4배
# 어긋난다. 매니페스트는 PNG 픽셀 크기로 좌표와 배율을 계산하므로, 들어온
# 크기가 그것과 다르면 자리가 통째로 밀린다.
#
# 그래서 **viewBox 를 선언 크기에 맞춘다.** path 좌표를 그 비로 곱하면
# 그림은 그대로이고 두 값이 같아져 해석의 여지가 없어진다.
#
# `divisor` 로 더 줄일 수 있다. 벡터라 확대해도 깨지지 않으므로 작은 footage
# 로 들여와 배율로 키우는 편이 애프터이펙트에 가볍다 — 다만 매니페스트가
# 그만큼 배율을 곱해 줘야 자리가 맞는다(`vectorDivisor` 로 함께 내보낸다).

def unwrap_svg(text: str) -> tuple:
    """전에 감싸 둔 `<g transform="matrix(...)">` 를 걷어내고 그리기 좌표를 창으로 삼는다.

    애프터이펙트의 「쉐이프로 펴기」는 그룹 변환을 따라가지 않는다. 그래서
    2048 좌표계의 패스가 77×87 창에 들어가 통째로 창 밖으로 나갔다.

    되돌리는 것은 산술이다 — 감쌀 때 쓴 배율로 원래 좌표 공간을 되찾는다.
    **다시 벡터화하지 않는다**(크레딧 0). 반환 (새 텍스트, (w, h) 또는 None).
    """
    m = re.search(r'(<svg\b[^>]*>)\s*<g transform="matrix\(\s*'
                  r'([-\d.eE]+),\s*0,\s*0,\s*([-\d.eE]+),\s*'
                  r'([-\d.eE]+),\s*([-\d.eE]+)\s*\)"\s*>', text)
    if not m:
        return text, None
    head, sx, sy, tx, ty = m.group(1), *(float(m.group(i)) for i in range(2, 6))
    if sx == 0 or sy == 0:
        return text, None
    mw = re.search(r'\swidth="([\d.]+)"', head)
    mh = re.search(r'\sheight="([\d.]+)"', head)
    if not (mw and mh):
        return text, None
    # 감쌀 때: 그린 좌표 × s + t = 창 좌표. 되돌리면 그린 좌표 공간이 나온다.
    vw = float(mw.group(1)) / sx
    vh = float(mh.group(1)) / sy
    vx, vy = -tx / sx, -ty / sy
    tw, th = max(1, int(round(vw))), max(1, int(round(vh)))

    close = text.rindex("</svg>")
    body = text[m.end():close]
    gclose = body.rindex("</g>")          # 감쌀 때 붙인 마지막 닫음
    inner = body[:gclose] + body[gclose + 4:]

    head2 = re.sub(r'\swidth="[\d.]+"', f' width="{tw}"', head)
    head2 = re.sub(r'\sheight="[\d.]+"', f' height="{th}"', head2)
    head2 = re.sub(r'viewBox="[^"]*"',
                   f'viewBox="{vx:.6g} {vy:.6g} {vw:.6g} {vh:.6g}"', head2)
    return head2 + inner + text[close:], (tw, th)


def normalize_svg(text: str, *, divisor: int = 1, target=None) -> tuple:
    """선언 크기를 **그리기 좌표 공간에 맞춘다.** 반환 (새 텍스트, (w, h)).

    좌표는 한 글자도 건드리지 않는다. 창(viewBox)을 그림에 맞추는 것이지
    그림을 창에 맞추는 것이 아니다 — 그래야 애프터이펙트가 「쉐이프로 펴기」를
    했을 때 패스가 제자리에 온다.

    ⚠️ **감싸지 않는다.** 전에는 `<g transform="scale(...)">` 로 감싸 작게
    선언했는데(본문의 숫자를 곱하면 `rgb(245,222,193)` 의 색 값까지 곱해져
    무너지기 때문이었다), 애프터이펙트가 그 변환을 무시해 그림이 창 밖으로
    나갔다. 색을 지키려다 그림을 잃었다. 감싸는 대신 **창을 넓힌다.**

    `divisor`·`target` 은 옛 호출부와의 호환으로 받기만 하고 쓰지 않는다.
    """
    mw = re.search(r'\swidth="([\d.]+)"', text)
    mh = re.search(r'\sheight="([\d.]+)"', text)
    mv = re.search(r'viewBox="\s*([\d.-]+)\s+([\d.-]+)\s+([\d.]+)\s+([\d.]+)\s*"', text)
    if not (mw and mh and mv):
        return text, None
    vx, vy, vw, vh = (float(mv.group(i)) for i in range(1, 5))
    if vw <= 0 or vh <= 0:
        return text, None
    # 이미 감싸 둔 것이면 먼저 걷어낸다 — 여러 번 돌려도 결과가 같아야 한다
    if '<g transform="matrix(' in text[:text.index(">") + 400]:
        return unwrap_svg(text)
    # **정수로 만든다.** 애프터이펙트 footage 는 정수 픽셀이어야 한다 —
    # 179.2 x 102.4 로 내보냈더니 SVG 4장이 통째로 안 들어왔다.
    tw, th = max(1, int(round(vw))), max(1, int(round(vh)))
    # **정확히 같을 때만 건너뛴다.** 「거의 같으면 됐다」로 두었더니 179.2 가
    # 179 로 안 고쳐진 채 통과했다 — 애프터이펙트는 그 소수 하나에 파일을
    # 통째로 거절한다(SVG 4장이 그렇게 안 들어왔다).
    if float(mw.group(1)) == tw and float(mh.group(1)) == th:
        return text, (tw, th)
    head_end = text.index(">") + 1
    head = text[:head_end]
    head = re.sub(r'\swidth="[\d.]+"', f' width="{tw}"', head)
    head = re.sub(r'\sheight="[\d.]+"', f' height="{th}"', head)
    head = re.sub(r'viewBox="[^"]*"',
                  f'viewBox="{vx:.6g} {vy:.6g} {vw:.6g} {vh:.6g}"', head)
    return head + text[head_end:], (tw, th)


def normalize_svg_file(path, *, divisor: int = 1, png_path=None) -> dict:
    """파일 하나를 그리기 좌표 공간에 맞춘다. 여러 번 돌려도 결과가 같다.

    이미 `<g transform>` 으로 감싸 둔 옛 파일이면 걷어낸다 — **다시 벡터화하지
    않으므로 크레딧이 들지 않는다.** `divisor`·`png_path` 는 옛 호출부와의
    호환으로 받기만 한다(이제 PNG 크기로 창을 정하지 않는다 — 그림이 정한다).
    """
    p = Path(path)
    before = p.stat().st_size
    try:
        text = p.read_text(encoding="utf-8")
        out, size = normalize_svg(text)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if size is None:
        return {"ok": False, "error": "머리말을 읽지 못했습니다(건드리지 않음)"}
    changed = out != text
    if changed:
        p.write_text(out, encoding="utf-8")
    return {"ok": True, "size": list(size), "changed": changed,
            "before": before, "after": p.stat().st_size}
