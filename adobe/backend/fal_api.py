"""fal 이미지 편집 API 호출 — 레이어 분리 전용.

CLAUDE.md의 '이미지 생성은 codex $imagegen 전용' 규칙의 명시적 예외.
씬 이미지·캐릭터 생성은 여전히 codex를 쓰고, 레이어 분리만 이 경로를 탄다.
새 의존성 없이 stdlib urllib만 사용(tts.py의 ElevenLabs 호출과 같은 방식).
"""
from __future__ import annotations

import base64
import json
import mimetypes
import urllib.request
from pathlib import Path

from backend import env

# edit_image은 현재 레이어 분리 경로에서 호출되지 않는다 — 향후 용도를 위해 남겨둔다(테스트만 사용 중).
ENDPOINT = "https://fal.run/xai/grok-imagine-image/v2.0/edit"
MAX_INPUT_IMAGES = 3          # 모델 상한 — 초과분은 앞에서부터 자른다
# auto_kairos_v3의 .env는 같은 키를 FAL_API_KEY로 갖고 있다. 비밀값을 두 벌로 복사해 두면
# 한쪽만 교체됐을 때 조용히 어긋나므로, 이름 두 개를 다 받아들인다.
KEY_NAMES = ("FAL_KEY", "FAL_API_KEY")


class FalError(Exception):
    """fal 호출 실패 — 키 없음·비200·응답 이상. 상위 잡이 실패로 표면화한다."""


def api_key() -> str:
    """FAL_KEY 우선, 없으면 FAL_API_KEY. 둘 다 없으면 ''."""
    for name in KEY_NAMES:
        val = env.get_key(name)
        if val:
            return val
    return ""


def data_uri(path: Path) -> str:
    """로컬 이미지를 base64 data URI로. fal 입력이 URL이라 로컬 파일을 그대로 못 넘긴다."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def edit_image(prompt: str, image_paths: list, *, output_format: str = "png",
               resolution: str = "2k", timeout: int = 180) -> bytes:
    """참조 이미지들을 두고 prompt대로 편집한 이미지 1장을 바이트로 반환."""
    key = api_key()
    if not key:
        raise FalError("FAL_KEY(또는 FAL_API_KEY) 없음 — auto_kairos .env 또는 환경변수")
    paths = [Path(p) for p in (image_paths or []) if Path(p).is_file()]
    if not paths:
        raise FalError("입력 이미지 없음")
    body = json.dumps({
        "prompt": prompt,
        "image_urls": [data_uri(p) for p in paths[:MAX_INPUT_IMAGES]],
        "num_images": 1,
        "output_format": output_format,
        "resolution": resolution,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except FalError:
        raise
    except Exception as e:                       # HTTPError·URLError·타임아웃·파싱 실패
        raise FalError(f"fal 호출 실패: {str(e)[:200]}") from e
    images = data.get("images") or []
    if not images or not images[0].get("url"):
        raise FalError(f"fal 응답에 이미지 없음: {str(data)[:200]}")
    try:
        img_req = urllib.request.Request(images[0]["url"])
        with urllib.request.urlopen(img_req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        raise FalError(f"fal 결과 내려받기 실패: {str(e)[:200]}") from e


LAYERIZE_ENDPOINT = "https://fal.run/bytedance/seedream/v5/pro/layerize"


def build_layerize_prompt(names: list) -> str:
    """분리할 요소 이름을 영어로 나열한다.

    이 모델은 프롬프트에 적은 이름대로 쪼갠다 — 적지 않은 것은 배경에 남는다.
    'background'는 절대 넣지 않는다: 넣으면 하늘·도로가 뚫린 배경 요소 레이어가
    한 장 더 오는데, 우리가 쓰는 배경은 z_index 0의 인페인팅된 판이다."""
    joined = ", ".join(n for n in names if n)
    return ("Separate this illustration into transparent layers. "
            f"Extract each of these as its own layer: {joined}. "
            "Keep each element whole and in its original position.")


def layerize(image_path, names: list, *, timeout: int = 600) -> list:
    """씬 이미지를 레이어로 분리. z_index 오름차순 목록을 돌려준다.

    각 항목 {name(z0은 None), z, bbox(z0은 None), data(PNG 바이트)}.
    배경판(인페인팅된 정사각형)은 name이 None인 항목으로 식별된다.
    응답의 image.width/height는 null로 오므로 크기는 호출자가 PNG에서 읽는다."""
    key = api_key()
    if not key:
        raise FalError("FAL_KEY(또는 FAL_API_KEY) 없음 — auto_kairos .env 또는 환경변수")
    picked = [n for n in (names or []) if n]
    if not picked:
        raise FalError("분리할 요소 이름 없음")
    src = Path(image_path)
    if not src.is_file():
        raise FalError(f"씬 이미지 없음: {src}")
    body = json.dumps({
        "image_url": data_uri(src),
        "prompt": build_layerize_prompt(picked),
        "image_size": "auto",
    }).encode("utf-8")
    req = urllib.request.Request(
        LAYERIZE_ENDPOINT, data=body, method="POST",
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except FalError:
        raise
    except Exception as e:
        raise FalError(f"layerize 호출 실패: {str(e)[:200]}") from e
    raw = data.get("layers") or []
    if not raw:
        raise FalError(f"layerize 응답에 레이어 없음: {str(data)[:200]}")

    def _zkey(L):
        z = L.get("z_index")
        return (z is None, z if z is not None else 0)

    out = []
    for L in sorted(raw, key=_zkey):
        url = ((L.get("image") or {}).get("url") or "").strip()
        if not url:
            raise FalError(f"레이어에 이미지 URL 없음: z={L.get('z_index')} name={L.get('name')}")
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:
                blob = resp.read()
        except Exception as e:
            raise FalError(f"레이어 내려받기 실패: {str(e)[:200]}") from e
        bb = (L.get("bounding_box") or {}).get("absolute")
        out.append({"name": L.get("name"), "z": L.get("z_index"),
                    "bbox": list(bb) if bb else None, "data": blob})
    if not out:
        raise FalError("layerize 응답에 내려받을 이미지가 없음")
    return out
