"""Phase B 검증 — 헤드리스 렌더 + 듀얼 비디오 gemini 대조 + 2층 게이트.
이 파일 전반부는 순수 로직(테스트 대상), verify()는 오케스트레이션."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from scripts.motion_learn import state, gemini_client


def structural_check(motion: dict, lib: dict) -> dict:
    """motion.json 정합성: 컷 존재 + 사용 프리셋이 라이브러리에 존재하는가(결정론적)."""
    issues = []
    cuts = motion.get("cuts", []) or []
    if not cuts:
        issues.append("컷 없음")
    presets = set((lib.get("presets") or {}).keys())
    for i, c in enumerate(cuts):
        for lyr in (c.get("layers", []) or []):
            for an in (lyr.get("anim", []) or []):
                pn = an.get("preset")
                if pn and pn not in presets:
                    issues.append(f"cut{i}: 미존재 프리셋 {pn}")
    return {"pass": not issues, "issues": issues, "cut_count": len(cuts)}


def passes_gate(structural_pass: bool, score: int, threshold: int = 75) -> bool:
    return bool(structural_pass) and int(score) >= int(threshold)


def parse_verdict(raw) -> dict:
    data = raw if isinstance(raw, dict) else json.loads(raw)
    return {
        "score": int(data.get("score", 0)),
        "diffs": data.get("diffs", []) or [],
        "summary": data.get("summary", "") or "",
    }


def build_ae_command(afterfx_bin: str, jsx_path: str) -> list:
    return [afterfx_bin, "-r", jsx_path]


def build_ffmpeg_command(mov: str, mp4: str) -> list:
    return ["ffmpeg", "-y", "-i", mov, "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4]


ROOT = Path(__file__).resolve().parents[2]
AFTERFX_BIN = os.environ.get(
    "AK_AFTERFX_BIN",
    "/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app/Contents/MacOS/After Effects",
)
VERIFY_JSX = ROOT / "cep" / "com.autokairos.pd" / "jsx" / "tylenol" / "verify_render.jsx"
RUBRIC_PATH = ROOT / "docs" / "research" / "ae_motion_techniques.md"


def _next_round(verify_dir: Path) -> int:
    n = 1
    while (verify_dir / f"build_{n:02d}.aep").exists() or (verify_dir / f"render_{n:02d}.mov").exists():
        n += 1
    return n


def _compare_prompt(rubric: str) -> str:
    return (
        "두 영상의 모션그래픽 충실도를 비교한다. 첫 번째=원본 레퍼런스, 두 번째=AE 렌더 결과.\n"
        "아래 rubric의 명명된 원칙(이징/오버슈트/타이밍/폴리시)으로 판정하라. "
        "'비슷해 보임'이 아니라 'easeOut인데 overshoot 없음', 'influence 대칭이라 기계적', "
        "'anticipation 없음', '모션블러 누락' 처럼 구체적으로.\n"
        "JSON으로만 출력: {\"score\": 0~100, "
        "\"diffs\": [{\"cut\": 정수, \"kind\": \"timing|position|easing|color|missing|polish\", \"detail\": \"...\"}], "
        "\"summary\": \"...\"}\n\n=== RUBRIC ===\n" + rubric
    )


def verify(slug: str, refs_dir: Path, lib_path: Path, *, threshold: int = 75, timeout: int = 600) -> dict:
    ref_dir = Path(refs_dir) / slug
    motion_fp = ref_dir / "motion.json"
    orig = Path(refs_dir) / (slug + ".mp4")
    if not motion_fp.is_file():
        return {"error": "motion.json 없음"}
    if not orig.is_file():
        return {"error": "원본 mp4 없음"}
    motion = json.loads(motion_fp.read_text(encoding="utf-8"))
    lib = json.loads(Path(lib_path).read_text(encoding="utf-8"))
    structural = structural_check(motion, lib)

    verify_dir = ref_dir / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    rnd = _next_round(verify_dir)
    aep = verify_dir / f"build_{rnd:02d}.aep"
    mov = verify_dir / f"render_{rnd:02d}.mov"
    mp4 = verify_dir / f"render_{rnd:02d}.mp4"

    env = dict(os.environ)
    env.update({"AK_VERIFY_MOTION": str(motion_fp), "AK_VERIFY_OUT": str(mov), "AK_VERIFY_AEP": str(aep)})
    try:
        cp = subprocess.run(build_ae_command(AFTERFX_BIN, str(VERIFY_JSX)), env=env, timeout=timeout)
    except (subprocess.SubprocessError, OSError) as e:
        return {"error": "AE 렌더 실패: " + str(e), "structural": structural}
    if cp.returncode != 0:
        return {"error": f"AE 렌더 비정상 종료(code {cp.returncode})", "structural": structural}
    if not mov.exists():
        return {"error": "렌더 산출물 없음", "structural": structural}
    try:
        cp = subprocess.run(build_ffmpeg_command(str(mov), str(mp4)), timeout=timeout)
    except (subprocess.SubprocessError, OSError) as e:
        return {"error": "ffmpeg 실패: " + str(e), "structural": structural}
    if cp.returncode != 0:
        return {"error": f"ffmpeg 비정상 종료(code {cp.returncode})", "structural": structural}
    if not mp4.exists():
        return {"error": "mp4 변환 실패", "structural": structural}

    rubric = RUBRIC_PATH.read_text(encoding="utf-8") if RUBRIC_PATH.is_file() else ""
    try:
        raw = gemini_client.compare_videos(str(orig), str(mp4), _compare_prompt(rubric))
    except Exception as e:  # noqa: BLE001 — gemini 폴백 소진 등 모든 실패를 비차단 보고
        return {"error": "gemini 대조 실패: " + str(e), "structural": structural}
    v = parse_verdict(raw)
    passed = passes_gate(structural["pass"], v["score"], threshold)
    verdict = {
        "structural": structural, "score": v["score"], "diffs": v["diffs"],
        "summary": v["summary"], "threshold": threshold, "passed": passed, "round": rnd,
    }
    (verify_dir / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    state.set_stage(ref_dir, "verified" if passed else "needs_improvement",
                    {"verify_score": v["score"], "verify_round": rnd})
    return verdict
