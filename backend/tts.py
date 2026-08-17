"""씬 내레이션 TTS.

기본 엔진: **ElevenLabs**(MP3 — CEP/Chromium 재생·AE 가져오기 호환).
ELEVENLABS_API_KEY 없으면 macOS `say`(WAV)로 폴백(개발용).
길이는 afinfo(초). stdlib만 사용(urllib).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from backend import env

# ElevenLabs 기본값(v3 narrator와 동일 계열 — semoji)
DEFAULT_VOICE_ID = "W7FnAxJNpD5WGjrF5GLp"
DEFAULT_MODEL = "eleven_multilingual_v2"
VOICE_SETTINGS = {
    "stability": 1.0, "similarity_boost": 0.9, "style": 0.9,
    "use_speaker_boost": True, "speed": 1.1,
}
SAY_VOICE = os.environ.get("TTS_SAY_VOICE", "Yuna")     # 폴백용 한국어 보이스

_VOICES_FILE = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "voices.json"


def load_voice_presets() -> dict:
    try:
        return json.loads(_VOICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"default_style": "semoji", "presets": {}}


def _tts_config_path(proj_dir: Path) -> Path:
    return Path(proj_dir) / "tts_config.json"


def get_tts_config(proj_dir: Path) -> dict:
    """프로젝트 tts_config.json(없으면 {})."""
    p = _tts_config_path(proj_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def set_tts_config(proj_dir: Path, *, style=None, voice_id=None, model=None, voice_settings=None) -> dict:
    """프로젝트 TTS 설정 저장(부분 갱신). 반환=effective_voice."""
    proj_dir = Path(proj_dir)
    cfg = get_tts_config(proj_dir)
    if style is not None:
        cfg["style"] = style
    if voice_id is not None:
        cfg["voice_id"] = voice_id          # 빈 문자열이면 override 해제(스타일 프리셋 사용)
        if voice_id == "":
            cfg.pop("voice_id", None)
    if model is not None:
        cfg["model"] = model
    if voice_settings is not None:
        cfg["voice_settings"] = voice_settings
    _tts_config_path(proj_dir).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return effective_voice(proj_dir)


def effective_voice(proj_dir: Path) -> dict:
    """유효 voice 설정 해석: 프로젝트 override → 스타일 프리셋 → semoji 기본.
    반환 {style, voice_id, model, voice_settings}."""
    presets = load_voice_presets()
    table = presets.get("presets", {})
    default_style = presets.get("default_style", "semoji")
    cfg = get_tts_config(proj_dir)
    style = cfg.get("style") or default_style
    base = table.get(style) or table.get(default_style) or {}
    voice_id = cfg.get("voice_id") or base.get("voice_id") or DEFAULT_VOICE_ID
    voice_settings = cfg.get("voice_settings") or base.get("voice_settings") or VOICE_SETTINGS
    model = cfg.get("model") or base.get("model") or DEFAULT_MODEL
    return {"style": style, "voice_id": voice_id, "model": model, "voice_settings": voice_settings}


def _engine() -> str:
    """ELEVENLABS_API_KEY 있으면 elevenlabs, 없으면 say."""
    return "elevenlabs" if env.get_key("ELEVENLABS_API_KEY") else "say"


def _ext() -> str:
    return "mp3" if _engine() == "elevenlabs" else "wav"


def scene_audio_name(sid: str) -> str:
    return f"tts_{sid}.{_ext()}"


def _clean_text(text: str) -> str:
    """TTS 전 가벼운 정리 — 지문(괄호)·이모지 제거. 한국어 발음 교정은 미적용(필요 시 확장)."""
    t = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", "", text or "")
    t = re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _parse_afinfo_duration(text: str) -> float:
    m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", text)
    return float(m.group(1)) if m else 0.0


_DUR_CACHE: dict = {}      # (경로, mtime_ns, size) -> 길이. 파일이 바뀌면 키가 달라져 자동 무효화


def _timestamps_duration(path: Path) -> float:
    """ElevenLabs 사이드카(<stem>.timestamps.json)의 마지막 end. 가장 정확하고 OS 무관."""
    side = Path(path).parent / (Path(path).stem + ".timestamps.json")
    if not side.is_file():
        return 0.0
    try:
        ends = json.loads(side.read_text(encoding="utf-8")).get("ends") or []
        return round(float(ends[-1]), 3) if ends else 0.0
    except (json.JSONDecodeError, OSError, ValueError, TypeError, IndexError):
        return 0.0


def _ffprobe_duration(path: Path) -> float:
    """ffprobe(있으면). 윈도우·리눅스에서 afinfo 대신 쓰는 경로."""
    if shutil.which("ffprobe") is None:
        return 0.0
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=20)
        return round(float((r.stdout or "").strip()), 3)
    except (ValueError, OSError, subprocess.SubprocessError):
        return 0.0


def _afinfo_duration(path: Path) -> float:
    """afinfo — macOS 전용. 다른 OS에서는 파일이 없어 그냥 실패한다."""
    if shutil.which("afinfo") is None:
        return 0.0
    try:
        r = subprocess.run(["afinfo", str(path)], capture_output=True, text=True, timeout=20)
        return _parse_afinfo_duration(r.stdout)
    except (OSError, subprocess.SubprocessError):
        return 0.0


def audio_duration(path: Path) -> float:
    """오디오 길이(초). 실패 시 0.0.

    순서: 타임스탬프 사이드카 → ffprobe → afinfo → mp3 비트레이트 추정.
    afinfo는 macOS 전용이라 이것만 쓰면 윈도우에서 항상 0.0이 되고,
    그러면 씬 길이가 통째로 기본값으로 떨어진다(컴프·자막·타임라인 전부 어긋남).

    씬이 100개 넘는 프로젝트는 시트를 열 때마다 외부 프로세스를 그만큼 띄우게 되므로
    (경로, mtime, 크기) 기준으로 캐시한다."""
    path = Path(path)
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return 0.0
    if key in _DUR_CACHE:
        return _DUR_CACHE[key]
    dur = _timestamps_duration(path) or _ffprobe_duration(path) or _afinfo_duration(path)
    if not dur and path.suffix.lower() == ".mp3":
        dur = round(st.st_size * 8 / 128000, 3)      # 128kbps 가정 — 마지막 수단
    if dur:
        _DUR_CACHE[key] = dur
    return dur


def _eleven_fetch(text: str, cfg: dict | None = None):
    """ElevenLabs with-timestamps — (MP3 bytes, alignment dict|None). 실패 시 일반 엔드포인트 폴백."""
    cfg = cfg or {}
    key = env.get_key("ELEVENLABS_API_KEY")
    vid = cfg.get("voice_id") or DEFAULT_VOICE_ID
    model = cfg.get("model") or DEFAULT_MODEL
    settings = cfg.get("voice_settings") or VOICE_SETTINGS
    body = json.dumps({"text": text, "model_id": model, "voice_settings": settings}).encode("utf-8")
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        import base64
        return base64.b64decode(data["audio_base64"]), data.get("alignment") or data.get("normalized_alignment")
    except Exception:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={**headers, "Accept": "audio/mpeg"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read(), None


def _synth_say(text: str, out_path: Path, voice: str | None) -> None:
    cmd = ["say", "-v", voice or SAY_VOICE, "-o", str(out_path),
           "--data-format=LEI16@22050", "--file-format=WAVE", text]
    subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)


def synthesize(text: str, out_path: Path, cfg: dict | None = None) -> dict:
    """text를 out_path로 합성. 엔진(elevenlabs/say)은 키 유무로 결정. {status, path, duration, engine}."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    eng = _engine()
    clean = _clean_text(text)
    align = None
    try:
        if eng == "elevenlabs":
            audio, align = _eleven_fetch(clean, cfg)
            out_path.write_bytes(audio)
            if align:
                side = out_path.parent / (out_path.stem + ".timestamps.json")
                side.write_text(json.dumps({
                    "text": clean,
                    "characters": align.get("characters", []),
                    "starts": align.get("character_start_times_seconds", []),
                    "ends": align.get("character_end_times_seconds", []),
                }, ensure_ascii=False), encoding="utf-8")
        else:
            if shutil.which("say") is None:
                return {"status": "failed", "error": "say 없음·ElevenLabs 키 없음", "path": str(out_path), "duration": 0.0}
            _synth_say(clean, out_path, SAY_VOICE)
    except Exception as e:
        return {"status": "failed", "error": str(e)[:200], "path": str(out_path), "duration": 0.0, "engine": eng}
    if not out_path.exists() or out_path.stat().st_size == 0:
        return {"status": "failed", "error": "출력 없음", "path": str(out_path), "duration": 0.0, "engine": eng}
    ends = (align or {}).get("character_end_times_seconds") or []
    if ends:                                        # alignment가 가장 정확
        dur = round(float(ends[-1]), 3)
    else:
        dur = audio_duration(out_path)
        if dur == 0.0 and eng == "elevenlabs":      # afinfo 실패 시 비트레이트 추정(128kbps)
            dur = round(out_path.stat().st_size * 8 / 128000, 3)
    return {"status": "completed", "path": str(out_path), "duration": dur, "engine": eng}


def generate_scene_tts(proj_dir: Path, sid: str, text: str, voice: str | None = None) -> dict:
    """씬 오디오 audio/tts_{sid}.{ext} 생성(갱신). 빈 텍스트면 failed."""
    if not (text or "").strip():
        return {"status": "failed", "error": "내레이션 비어있음"}
    cfg = effective_voice(proj_dir)
    if voice:
        cfg = {**cfg, "voice_id": voice}
    out = Path(proj_dir) / "audio" / scene_audio_name(sid)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = synthesize(text, out, cfg=cfg)
    if res.get("status") == "completed":
        res["rel"] = f"audio/{out.name}"
        res["voice_id"] = cfg["voice_id"]
    return res
