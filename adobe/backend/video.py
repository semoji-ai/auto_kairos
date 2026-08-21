"""씬 비디오 생성 — 힉스필드 CLI(`higgsfield generate create`) 연동.

**모델 스펙은 우리가 적지 않는다.** `higgsfield model get <job_type>` 산출을
`data/higgsfield/<job_type>.json` 에 그대로 굳혀 두고 그것을 읽는다. 손으로
옮겨 적으면 힉스필드가 파라미터를 바꿀 때마다 어긋나고, 어긋난 줄도 모른 채
생성이 실패한다.

모델마다 받는 것이 크게 다르다 — 첨부 가능한 이미지 수도, 해상도 목록도,
`start_image`/`end_image` 허용 여부도. 그 차이를 UI 가 알아야 하므로 규칙까지
함께 내보낸다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# 이 편에서 쓰기로 한 모델. 힉스필드에는 더 있지만 목록을 좁혀 둔다 —
# 스물여덟 개를 다 내놓으면 고르는 것이 일이 된다.
MODELS = [
    "seedance1_5",
    "seedance_2_0_mini",
    "seedance_2_0",
    "seedance_2_5",
    "minimax_h3",
    "gemini_omni",
]

_SPEC_DIR = Path(__file__).resolve().parents[1] / "data" / "higgsfield"

# 이미지를 붙일 수 있는 파라미터 이름. 모델마다 있는 것과 없는 것이 갈린다.
IMAGE_PARAMS = ("start_image", "end_image", "image_references")


def cli() -> str | None:
    return shutil.which("higgsfield") or shutil.which("hf")


def load_specs() -> list:
    """모델 목록 + 파라미터. UI 가 이것만 보고 화면을 짠다."""
    out = []
    for jt in MODELS:
        f = _SPEC_DIR / f"{jt}.json"
        if not f.is_file():
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        params = {p["name"]: p for p in d.get("params", [])}
        out.append({
            "job_type": d.get("job_type", jt),
            "display_name": d.get("display_name", jt),
            "params": d.get("params", []),
            "rules": [r.get("message", "") for r in d.get("rules", [])],
            # UI 가 곧바로 쓰는 요약 — 매번 params 를 뒤지지 않게
            "image_slots": [k for k in IMAGE_PARAMS if k in params],
            "max_images": _max_images(d),
        })
    return out


def _max_images(spec: dict) -> int | None:
    """규칙 문구에서 이미지 첨부 한도를 읽는다.

    스펙이 CEL 식과 사람 말 문구로 오는데, 식을 해석하는 것보다 문구에서
    숫자를 집는 편이 안전하다 — 식 문법이 바뀌어도 문구는 남는다.
    한도를 못 읽으면 `None` 을 돌려 UI 가 제한을 걸지 않는다(막는 것보다
    보내 보고 실패하는 편이 낫다 — 우리 추측으로 못 하게 하면 안 된다).
    """
    import re
    best = None
    for r in spec.get("rules", []):
        msg = r.get("message", "")
        m = re.search(r"at most (\d+) image", msg, re.I)
        if not m:
            continue
        n = int(m.group(1))
        # **가장 큰 값을 쓴다.** 작은 값은 대개 조건부다 — gemini_omni 는
        # 「비디오 참조가 있으면 5장」과 「최대 7장」이 함께 오는데, 작은 쪽을
        # 잡으면 비디오를 안 붙이는 보통 경우에 2장을 못 쓰게 막는다.
        # 조건부 제한은 힉스필드가 거절해 주므로 우리가 미리 막지 않는다.
        best = n if best is None else max(best, n)
    return best


def generate(proj_dir: Path, job_type: str, params: dict, *,
             images: dict | None = None, on_line=None,
             timeout: int = 1800) -> dict:
    """비디오 한 편 생성. `--wait` 로 끝날 때까지 기다린다.

    `images` 는 {파라미터 이름: [프로젝트 상대 경로…]}. CLI 가 로컬 경로를
    받아 알아서 업로드하므로 따로 올리지 않는다.
    """
    exe = cli()
    if not exe:
        return {"status": "failed", "error": "higgsfield CLI 를 찾을 수 없습니다"}
    if job_type not in MODELS:
        return {"status": "failed", "error": f"지원하지 않는 모델: {job_type}"}
    if not (params.get("prompt") or "").strip():
        return {"status": "failed", "error": "prompt 필요"}

    cmd = [exe, "generate", "create", job_type, "--json", "--wait",
           "--wait-timeout", f"{timeout}s"]
    for k, v in params.items():
        if v is None or v == "":
            continue
        cmd += [f"--{k.replace('_', '-')}", str(v)]

    # 이 모델이 받는 이미지 칸만 넘긴다. 화면에서 걸러도 여기서 한 번 더 본다 —
    # gemini_omni 처럼 `start_image` 가 아예 없는 모델에 그것을 보내면 CLI 가
    # 거절하는데, 왜 거절됐는지는 로그를 봐야 알 수 있어 원인을 찾기 어렵다.
    spec = next((m for m in load_specs() if m["job_type"] == job_type), None)
    allowed = set(spec["image_slots"]) if spec else set(IMAGE_PARAMS)
    dropped = [k for k in (images or {}) if k not in allowed]

    for slot, paths in (images or {}).items():
        if slot not in allowed:
            continue
        flag = "--" + slot.replace("_", "-")
        for rel in paths or []:
            fp = (proj_dir / rel).resolve()
            # 프로젝트 밖을 가리키는 경로는 받지 않는다
            if fp.is_file() and proj_dir.resolve() in fp.parents:
                cmd += [flag, str(fp)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=timeout + 120)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": f"{timeout}초 초과"}
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if on_line:
        for ln in log.splitlines():
            if ln.strip():
                on_line(ln)
    if proc.returncode != 0:
        return {"status": "failed", "error": "CLI 실패", "log_tail": log[-600:]}

    urls = _result_urls(proc.stdout or "")
    if not urls:
        return {"status": "failed", "error": "결과 URL 없음", "log_tail": log[-600:]}
    out = {"status": "completed", "urls": urls, "log_tail": log[-400:]}
    if dropped:
        # 조용히 버리지 않는다 — 붙였다고 생각한 것이 안 들어갔으면 알아야 한다
        out["dropped_slots"] = dropped
    return out


def _result_urls(stdout: str) -> list:
    """JSON 응답에서 결과 URL 을 긁는다. 응답 모양이 판마다 조금씩 다르다."""
    import re
    try:
        d = json.loads(stdout)
    except Exception:
        # JSON 이 아니면 본문에서 URL 을 집는다 — 실패로 떨어뜨리기 전에 해 본다
        return re.findall(r"https?://\S+\.(?:mp4|mov|webm)", stdout)
    found: list = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and v.startswith("http") and (
                        "url" in k.lower() or v.endswith((".mp4", ".mov", ".webm"))):
                    found.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(d)
    return list(dict.fromkeys(found))


def download(url: str, out: Path, *, timeout: int = 600) -> dict:
    """결과를 프로젝트 안으로 받아 둔다. 원격 URL 은 만료되므로 링크만 두면 안 된다."""
    import urllib.request
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        return {"status": "failed", "error": f"내려받기 실패: {e}"}
    return {"status": "completed", "path": str(out)}
