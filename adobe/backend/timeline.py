"""씬 타이밍·컴프 이름의 단일 기준.

컴프 조립(manifest)·말자막(subtitles)·타임라인 배치가 **모두 여기 함수를 쓴다.**
각자 계산하면 셋의 씬 경계가 어긋나 자막이 밀리고 음성이 잘린다.

씬 길이 = TTS 오디오 길이 → duration_estimate_sec → DEFAULT_DUR.
씬 시작 = 앞 씬 길이의 누적합. only_scene을 줘도 시작 시점은 전체 기준과 같으므로,
한 씬만 다시 내려도 제자리에 들어간다.
"""
from __future__ import annotations

from pathlib import Path

from backend import scenes as _scenes
from backend import tts as _tts

DEFAULT_DUR = 5.0


def comp_num(scene_number) -> str:
    """컴프 이름에 쓰는 씬 번호 표기. 정수는 2자리 0채움, 소수는 점을 하이픈으로.

    씬을 삽입하면 25.25 같은 소수 번호가 생기는데, 이때 %02d는 그대로 터진다.
    구분자는 밑줄이 아니라 하이픈을 쓴다 — 밑줄을 쓰면 25.25 → "25_25"가 되어
    씬 25의 접두사 "S25_"가 씬 25.25의 레이어 이름 "S25_25_..."의 접두사도 돼 버린다.
    akRemoveSceneGroup은 접두사 매치라서, 씬 25만 다시 빌드해도 25.25 레이어까지
    통째로 지워지고 매니페스트에 없는 그 씬은 다시 만들어지지 않는다(영구 소실).
    하이픈이면 "S25-25_"라 "S25_"의 접두사가 되지 않는다."""
    try:
        n = float(scene_number)
    except (TypeError, ValueError):
        return "00"
    if n == int(n):
        return f"{int(n):02d}"
    return str(n).replace(".", "-")


def comp_name(scene: dict) -> str:
    """씬 컴프 이름(S01_abcd1234). manifest·타임라인 배치가 같은 이름을 봐야 한다."""
    existing = (scene.get("ae_comp_name") or "").strip()
    if existing:
        return existing
    return f"S{comp_num(scene.get('sceneNumber'))}_{scene.get('sceneId') or ''}"


def scene_duration(proj_dir: Path, scene: dict) -> float:
    """씬 길이(초). TTS 오디오 → duration_estimate_sec → DEFAULT_DUR."""
    rel = scene.get("_audio")
    if rel:
        d = scene.get("_audio_dur")
        if not d:
            d = _tts.audio_duration(Path(proj_dir) / rel)
        if d:
            return round(float(d), 3)
    est = scene.get("duration_estimate_sec")
    try:
        if est and float(est) > 0:
            return round(float(est), 3)
    except (TypeError, ValueError):
        pass
    return DEFAULT_DUR


def scene_timings(proj_dir: Path, data: dict) -> list:
    """[(scene, start, duration)] — 전체 씬 기준 누적 시작 시점."""
    out, offset = [], 0.0
    for s in data.get("scenes", []):
        dur = scene_duration(proj_dir, s)
        out.append((s, round(offset, 3), dur))
        offset += dur
    return out


