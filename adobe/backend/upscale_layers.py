"""레이어 PNG 업스케일 — **제자리 교체, 원본은 백업 폴더로.**

fal 이 떼어 주는 레이어는 크기가 들쭉날쭉하다. 씬 100 기준으로 재 보면
화면에 앉을 폭 대비 **최소 0.95배 · 중앙 1.59배 · 최대 4.02배**이고, 화면보다
작은 것이 118장 중 14장이다. 그 14장은 지금도 늘려 쓰고 있어 가장 티가 난다.

카메라가 밀고 들어가거나 4K 로 렌더하면 그 여유가 더 필요하다. 벡터화는
레이어당 크레딧이 들지만 **업스케일은 로컬이라 공짜**다. 패스를 손볼 씬만
벡터로 하고 나머지는 이쪽으로 해결하면 된다.

## 왜 제자리에 교체하나

매니페스트가 `<sid>__*.png` 를 통째로 훑는다. `_up` 을 붙여 옆에 두면
**레이어가 한 장 더 생긴 것으로 잡혀** 같은 인물이 두 번 올라간다.
`__elements.json` 에도 없으니 자리를 몰라 폴백을 탄다.

제자리에 교체하면 사이드카의 bbox·z·motion 이 그대로 살고, 배율은 매니페스트가
다시 계산한다 — `scale = bbox폭 ÷ PNG폭 × …` 이라 **분모가 커진 만큼 배율이
줄어 화면 크기는 그대로**다. 자리가 밀리지 않는다.

원본은 지우지 않는다. `layers/_upscale_backup/` 으로 옮겨 남긴다.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

BACKUP = "_upscale_backup"
# 컴프 높이 ÷ 씬 이미지 높이. 매니페스트의 fit 과 같은 값이라야 한다.
COMP_H = 1080


def _tools():
    """`auto_agent.tools.upscale` — 저장소 뿌리를 경로에 넣어 불러온다."""
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from auto_agent.tools import upscale
    return upscale


def _scene_h(proj_dir: Path, sid: str) -> float:
    """씬 이미지 높이 — 배경판에서 읽는다. 없으면 1024 로 본다."""
    bg = proj_dir / "layers" / f"{sid}__bg.png"
    try:
        from PIL import Image
        with Image.open(bg) as im:
            return float(im.height)
    except Exception:
        return 1024.0


def plan(proj_dir, sid: str = "", *, want: float = 2.0) -> list:
    """업스케일이 필요한 레이어를 고른다.

    `want` 는 **화면에 앉을 폭의 몇 배를 갖고 싶은가**다. 기본 2배 — 카메라가
    조금 밀고 들어가도 견딘다. 이미 그만큼 큰 것은 건드리지 않는다(시간과
    디스크를 쓸 이유가 없다).

    반환 [{stem, png, onscreen, ratio, need}] — ratio 가 작은 것부터.
    """
    from PIL import Image
    L = Path(proj_dir) / "layers"
    if not L.is_dir():
        return []
    sides = [L / f"{sid}__elements.json"] if sid else sorted(L.glob("*__elements.json"))
    out = []
    for side in sides:
        if not side.is_file():
            continue
        this_sid = side.name.split("__")[0]
        f = COMP_H / _scene_h(Path(proj_dir), this_sid)
        try:
            els = json.loads(side.read_text(encoding="utf-8"))
        except Exception:
            continue
        for e in els:
            b = e.get("bbox")
            p = L / (str(e.get("layer") or "") + ".png")
            if not (p.is_file() and b and len(b) == 4):
                continue        # 배경판·덤 레이어는 자리를 몰라 건너뛴다
            try:
                with Image.open(p) as im:
                    pw = im.width
            except Exception:
                continue
            onscreen = (float(b[2]) - float(b[0])) * f
            if onscreen <= 0:
                continue
            ratio = pw / onscreen
            if ratio >= want:
                continue
            out.append({"stem": e["layer"], "sid": this_sid, "png": pw,
                        "onscreen": round(onscreen), "ratio": round(ratio, 2),
                        "need": round(want / ratio, 2)})
    out.sort(key=lambda x: x["ratio"])
    return out


def upscale_one(proj_dir, stem: str, *, scale: int = 2,
                content: str = "illustration") -> dict:
    """레이어 하나. 원본을 백업 폴더로 옮기고 그 자리에 업스케일본을 놓는다."""
    L = Path(proj_dir) / "layers"
    src = L / f"{stem}.png"
    if not src.is_file():
        return {"ok": False, "stem": stem, "error": "파일 없음"}
    up = _tools()
    if not up.upscayl_available():
        return {"ok": False, "stem": stem, "error": "Upscayl 이 설치돼 있지 않습니다"}
    tmp = L / f"{stem}.__up_tmp.png"
    r = up.upscale_image(str(src), str(tmp), content=content, scale=scale)
    if not tmp.is_file():
        tmp.unlink(missing_ok=True)
        return {"ok": False, "stem": stem, "error": str(r)[:180]}
    # **원본을 지우지 않는다.** 백업 폴더로 옮겨 남긴다. 이미 있으면 그대로
    # 둔다 — 두 번 돌렸을 때 업스케일본이 원본 자리를 차지하면 안 된다.
    bak_dir = L / BACKUP
    bak_dir.mkdir(parents=True, exist_ok=True)
    bak = bak_dir / f"{stem}.png"
    try:
        from PIL import Image
        with Image.open(src) as im:
            was = im.size
        with Image.open(tmp) as im:
            now = im.size
        if not bak.exists():
            shutil.move(str(src), str(bak))
        else:
            src.unlink(missing_ok=True)      # 원본은 이미 백업에 있다
        tmp.replace(src)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        return {"ok": False, "stem": stem, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "stem": stem, "was": list(was), "now": list(now),
            "backup": str(bak)}


def restore(proj_dir, stem: str) -> dict:
    """백업본을 제자리로 되돌린다 — 업스케일이 마음에 안 들 때."""
    L = Path(proj_dir) / "layers"
    bak = L / BACKUP / f"{stem}.png"
    if not bak.is_file():
        return {"ok": False, "error": "백업 없음"}
    shutil.move(str(bak), str(L / f"{stem}.png"))
    return {"ok": True, "stem": stem}


def run(proj_dir, stems: list, *, scale: int = 2, on_event=None) -> dict:
    done, failed = [], []
    for s in stems or []:
        r = upscale_one(proj_dir, s, scale=scale)
        (done if r.get("ok") else failed).append(r)
        if on_event:
            on_event(r)
    return {"done": done, "failed": failed}
