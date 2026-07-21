"""생성 이미지 후처리 — Upscayl 로컬 CLI(upscayl-bin, Real-ESRGAN 계열) 업스케일 연동.
API 키 불필요·로컬 GPU. 콘텐츠 타입에 맞는 모델 자동 선택:
생성 이미지(illustration)=digital-art, 실사(photo)=upscayl-standard.
이미지 생성(codex $imagegen)과는 별개의 후처리 단계 — 씬 이미지 배치 완료 후 순차 실행 전제.

env로 바이너리/모델 경로를 매 호출 조회 (모듈 상수로 캐싱하지 않음 — 테스트에서 monkeypatch.setenv로 제어 가능).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# 설치 위치 기본값 — env 우선, 없으면 표준 위치. (install.sh --upscayl가 여기에 받음)
_HOME_SHARE = Path.home() / ".local" / "share" / "upscayl"

# 콘텐츠 타입 → 모델. illustration=평면 벡터(스타일 보존), photo=실사(그레인/아티팩트 제거).
_MODEL_BY_CONTENT = {
    "illustration": "digital-art-4x",
    "photo": "upscayl-standard-4x",
    "photo_detail": "remacri-4x",  # 질감 더 보존(덜 매끈)
}
DEFAULT_CONTENT = "illustration"


def _bin_path() -> str:
    """env UPSCAYL_BIN 우선, 없으면 표준 설치 위치."""
    return os.environ.get("UPSCAYL_BIN") or str(_HOME_SHARE / "bin" / "upscayl-bin")


def _models_dir() -> str:
    """env UPSCAYL_MODELS 우선, 없으면 표준 설치 위치."""
    return os.environ.get("UPSCAYL_MODELS") or str(_HOME_SHARE / "models")


def _bin() -> str | None:
    bin_path = _bin_path()
    if os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
        return bin_path
    return shutil.which("upscayl-bin")


def upscayl_available() -> bool:
    """upscayl-bin 실행 가능 여부. env UPSCAYL_BIN 우선, 없으면 shutil.which 폴백."""
    return _bin() is not None


def available_models() -> list:
    """models 폴더의 설치된 모델명(.param 기준)."""
    d = Path(_models_dir())
    if not d.is_dir():
        return []
    return sorted({p.stem for p in d.glob("*.param")})


def _pick_model(content: str, model: str | None) -> str | None:
    """명시 model 우선(설치돼 있으면), 없으면 content로 자동. 미설치면 설치된 것 중 폴백."""
    installed = available_models()
    if model and model in installed:
        return model
    want = _MODEL_BY_CONTENT.get(content or DEFAULT_CONTENT, _MODEL_BY_CONTENT[DEFAULT_CONTENT])
    if want in installed:
        return want
    # 폴백: illustration이면 아무 art류, photo면 아무 standard류, 그래도 없으면 첫 모델
    for m in installed:
        if content == "photo" and "art" not in m:
            return m
        if content != "photo" and "art" in m:
            return m
    return installed[0] if installed else None


def upscale_image(src_png, out_png=None, *, content: str = DEFAULT_CONTENT,
                   model: str | None = None, scale: int = 2, timeout: int = 600) -> dict:
    """src를 업스케일해 out(기본: src 옆 _up 접미사)으로. {status, path, model, scale}|{status:failed,error}.
    content: 'illustration'(생성 이미지) / 'photo'(실사). model 명시하면 우선."""
    b = _bin()
    if not b:
        return {"status": "failed", "error": "upscayl-bin 미설치"}
    src = Path(src_png)
    if not src.is_file():
        return {"status": "failed", "error": f"입력 없음: {src_png}"}
    m = _pick_model(content, model)
    if not m:
        return {"status": "failed", "error": "설치된 업스케일 모델 없음"}
    out = Path(out_png) if out_png else src.with_name(f"{src.stem}_up{src.suffix or '.png'}")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [b, "-i", str(src), "-o", str(out), "-n", m, "-m", _models_dir(),
           "-s", str(int(scale)), "-f", "png"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "업스케일 타임아웃"}
    if p.returncode != 0 or not out.is_file():
        tail = ((p.stdout or "") + (p.stderr or ""))[-300:]
        return {"status": "failed", "error": "업스케일 실패", "log_tail": tail}
    return {"status": "completed", "path": str(out), "model": m, "scale": int(scale)}
