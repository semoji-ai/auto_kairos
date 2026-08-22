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

# 프레임 격자. **씬 경계는 프레임에 딱 떨어져야 한다.**
#
# 길이를 오디오 실측(소수 셋째 자리)으로 누적하니 시작점이 프레임 사이에
# 걸렸다 — 142씬 중 43씬이 그랬다. 애프터이펙트는 레이어 in·out 을 프레임으로
# 맞추므로, 씬마다 반올림 방향이 달라 이웃 씬과 한 프레임 겹치거나 벌어진다.
# 자막·음성·그림이 각자 다른 프레임으로 밀리는 원인이다.
#
# **올림으로 맞춘다.** 내림하면 음성 끝이 잘린다. 씬당 최대 한 프레임(0.033초)
# 무음이 붙지만 들리지 않고, 누적 오차는 생기지 않는다 — 시작점이 언제나
# 올림한 길이의 정확한 합이기 때문이다.
FPS = 30.0


def snap(sec: float, fps: float = FPS) -> float:
    """초를 프레임 격자에 올림으로 맞춘다."""
    import math
    if not fps or fps <= 0:
        return float(sec)
    return math.ceil(round(float(sec) * fps, 6)) / fps


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


def scene_timings(proj_dir: Path, data: dict, *, fps: float = FPS) -> list:
    """[(scene, start, duration)] — 전체 씬 기준 누적 시작 시점.

    **프레임 격자에 맞춰 낸다.** 길이를 올림하고 그 합으로 시작점을 만들므로
    시작·끝이 모두 프레임에 딱 떨어지고, 이웃 씬과 겹치거나 벌어지지 않는다.
    """
    import math
    out, frame = [], 0
    for s in data.get("scenes", []):
        # **프레임 정수로 누적한다.** 초로 더하면 1/30 이 이진수로 딱 떨어지지
        # 않아 백 씬쯤에서 오차가 쌓여 다시 격자를 벗어난다(142씬 중 29씬).
        nf = max(1, math.ceil(round(scene_duration(proj_dir, s) * fps, 6)))
        out.append((s, frame / fps, nf / fps))
        frame += nf
    return out


