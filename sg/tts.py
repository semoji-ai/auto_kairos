"""ElevenLabs TTS(세모지 보이스)와 정렬 기반 트림."""
import base64
import json
import subprocess
import urllib.request

_SKIP = set(" \t\n.,!?;:'\"…-—()[]")


def speech_bounds(al):
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    idx = [i for i, c in enumerate(ch) if c not in _SKIP]
    if not idx:
        return (0.0, en[-1] if en else 0.0)
    return (st[idx[0]], en[idx[-1]])


def load_key(env_path):
    for line in open(env_path):
        if line.startswith("ELEVENLABS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise KeyError("ELEVENLABS_API_KEY")


def synthesize(text, voice, model, lang_code, settings, key):
    body = {"text": text, "model_id": model, "language_code": lang_code, "voice_settings": settings}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192",
        data=json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    return base64.b64decode(r["audio_base64"]), (r.get("alignment") or {})


def trim(mp3_in, mp3_out, t0, t1, pad=0.03):
    a = max(0.0, t0 - pad)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{(t1 + pad) - a:.3f}", "-i", mp3_in,
                    "-c:a", "libmp3lame", "-b:a", "192k", mp3_out], check=True)
    return a
