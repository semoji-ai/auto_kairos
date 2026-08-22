"""분리된 레이어 그림 고치기 — 씨드림 5.0 Pro(힉스필드 CLI).

레이어를 나눠 놓고 나면 **그 레이어 하나만 고치고 싶어진다** — 인물의 자세를
바꾸거나 표정을 바꾸는 일이다. 씬을 통째로 다시 그리면 나머지 레이어가 전부
어긋나므로 쓸 수 없고, 다시 분리하면 이번엔 요소 경계가 달라진다.

씨드림 5.0 Pro 는 투명 배경을 받고(`remove_bg`) 투명 배경으로 돌려준다.
실측으로 확인한 것:

    · 얼굴·의상·그림체는 유지된다 (눈도 검은 점 그대로)
    · 자세는 크게든 작게든 바뀐다
    · **틀은 말하지 않으면 안 지킨다** — 상반신 레이어를 전신으로 늘려 버린다
    · 결과 해상도가 원본보다 크다 (1k 로 지정해도)

그래서 두 가지를 여기서 처리한다.

    ① `keep_frame` 이 참이면 틀을 지키라는 문장을 프롬프트에 덧붙인다
    ② 받은 그림을 **원본 레이어와 같은 크기로 되돌려** 저장한다.
       애프터이펙트는 bbox 자리에 레이어를 놓으므로, 크기가 달라지면
       자리가 통째로 어긋난다

**기존 레이어는 지우지 않는다.** 새 판본으로 쌓아 둘 다 남긴다 — 원본 자세와
바꾼 자세를 함께 쓰는 것이 애초에 이 기능을 만드는 이유다.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from backend import video

JOB_TYPE = "seedream_v5_pro"

# 틀을 지키라는 지시. **이 문장이 없으면 모델이 화면을 새로 잡는다** —
# 작업대에 가려 상반신만 있던 인물이 다리까지 그려져 돌아왔다.
KEEP_FRAME = (
    " 첨부 이미지와 화면 구도, 인물의 크기와 위치, 잘린 범위를 똑같이 유지한다."
    " 인물이 차지하는 자리와 여백도 첨부와 같게 둔다."
)

# 무엇을 바꾸든 늘 지켜야 하는 것. 인물 시트 규칙과 같은 내용이다 —
# 가려져 있던 곳이 드러나면 거기서 그림체가 샌다.
STYLE_LOCK = (
    " 얼굴 생김새, 머리 모양, 의상, 색, 그림체는 첨부 그대로 둔다."
    " 눈은 작고 둥근 검은 점 하나로만 그린다."
    " 배경은 투명하게 비워 둔다."
)


def next_version(path: Path) -> Path:
    """`foo.png` → `foo_p2.png` → `foo_p3.png`. 있는 것은 건드리지 않는다."""
    stem, suffix = path.stem, path.suffix
    n = 2
    while path.with_name(f"{stem}_p{n}{suffix}").exists():
        n += 1
    return path.with_name(f"{stem}_p{n}{suffix}")


def _run(uid: str, prompt: str, aspect: str, *, timeout: int = 600) -> dict:
    exe = video.cli()
    if not exe:
        return {"error": "higgsfield CLI 를 찾을 수 없습니다"}
    cmd = [exe, "generate", "create", JOB_TYPE, "--json", "--wait",
           "--wait-timeout", f"{timeout}s",
           "--prompt", prompt,
           "--image-references", uid,
           "--remove-bg", "true",
           "--aspect-ratio", aspect,
           "--resolution", "1k"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout + 120)
    except subprocess.TimeoutExpired:
        return {"error": f"{timeout}초 초과"}
    log = (p.stdout or "") + "\n" + (p.stderr or "")
    if p.returncode != 0:
        return {"error": "CLI 실패", "log_tail": log[-500:]}
    try:
        d = json.loads(p.stdout)
    except Exception:
        return {"error": "응답을 읽지 못했습니다", "log_tail": log[-500:]}
    items = d if isinstance(d, list) else [d]
    url = next((it.get("result_url") for it in items if it.get("result_url")), None)
    if not url:
        return {"error": "결과 URL 없음", "log_tail": log[-500:]}
    return {"url": url}


def _aspect(w: int, h: int) -> str:
    """가장 가까운 지원 비율. 원본과 비가 어긋나면 인물이 늘거나 눌린다."""
    r = w / max(1, h)
    table = {"1:1": 1.0, "3:4": 0.75, "4:3": 4 / 3, "9:16": 0.5625,
             "16:9": 16 / 9, "2:3": 2 / 3, "3:2": 1.5}
    return min(table, key=lambda k: abs(table[k] - r))


def _download_png(url: str, out: Path, *, timeout: int = 300) -> dict:
    """받은 것이 PNG 인지 확인하고 저장한다.

    비디오 쪽에서 그림을 mp4 로 저장해 두는 사고가 있었다(재생만 안 되고
    무엇이 잘못됐는지 알 수 없었다). 반대 방향도 막아 둔다.
    """
    import shutil
    import urllib.request
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        return {"status": "failed", "error": f"내려받기 실패: {e}"}
    if out.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        bad = out.with_suffix(out.suffix + ".notpng")
        out.replace(bad)                     # 지우지 않고 옆으로 치운다
        return {"status": "failed", "error": f"PNG 가 아닙니다 — {bad.name} 로 남겼습니다"}
    return {"status": "completed", "path": str(out)}


def edit_layer(proj_dir: Path, layer_rel: str, instruction: str, *,
               keep_frame: bool = True, on_line=None) -> dict:
    """레이어 한 장을 고쳐 **새 판본**으로 저장한다.

    반환 {status, path, rel, size} 또는 {status: failed, error}.
    """
    proj_dir = Path(proj_dir)
    src = (proj_dir / layer_rel).resolve()
    if not (src.is_file() and proj_dir.resolve() in src.parents):
        return {"status": "failed", "error": f"레이어를 찾을 수 없습니다: {layer_rel}"}
    if not (instruction or "").strip():
        return {"status": "failed", "error": "무엇을 바꿀지 적어야 합니다"}

    from PIL import Image
    with Image.open(src) as im:
        w, h = im.size

    if on_line:
        on_line(f"· 레이어 올리는 중: {src.name} ({w}×{h})")
    uid = video.upload(src)
    if not uid:
        return {"status": "failed", "error": "레이어 업로드 실패"}

    prompt = instruction.strip() + STYLE_LOCK + (KEEP_FRAME if keep_frame else "")
    if on_line:
        on_line("· 씨드림 5.0 Pro 로 고치는 중… (1분 안팎)")
    r = _run(uid, prompt, _aspect(w, h))
    if "error" in r:
        return {"status": "failed", **r}

    out = next_version(src)
    d = _download_png(r["url"], out)
    if d.get("status") != "completed":
        return {"status": "failed", **d}

    # **원본 크기로 되돌린다.** 애프터이펙트는 bbox 자리에 레이어를 놓으므로
    # 크기가 달라지면 자리가 통째로 어긋난다. 씨드림은 1k 로 지정해도
    # 원본보다 큰 그림을 준다.
    with Image.open(out) as im:
        got = im.size
        if got != (w, h):
            im.convert("RGBA").resize((w, h), Image.LANCZOS).save(out)
    if on_line:
        on_line(f"· 완료 — {out.name} ({got[0]}×{got[1]} → {w}×{h})")
    return {"status": "completed", "path": str(out),
            "rel": out.relative_to(proj_dir).as_posix(), "size": [w, h]}
