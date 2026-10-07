"""세그먼트별 ElevenLabs TTS(with-timestamps) → mp3 + 글자 정렬 json.
세모지 채널 보이스(auto_kairos_v3 artstyle/semoji.json)와 같은 설정을 쓴다.
    python3 tts.py script.json
"""
import base64, json, os, sys, urllib.request
from pathlib import Path

# 키: 환경변수 ELEVENLABS_API_KEY → 저장소 루트 .env (auto_kairos/.env)
KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ENV = Path(__file__).resolve().parents[1] / ".env"
if not KEY and ENV.is_file():
    for line in ENV.read_text().splitlines():
        if line.startswith("ELEVENLABS_API_KEY="):
            KEY = line.split("=", 1)[1].strip().strip('"')
VOICE = "W7FnAxJNpD5WGjrF5GLp"
SETTINGS = {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "speed": 1.1}
OUT = Path(__file__).parent / "video/public/audio/vo"
OUT.mkdir(parents=True, exist_ok=True)

segs = json.loads(Path(sys.argv[1]).read_text())
for s in [x for x in segs if x.get("type", "seg") == "seg"]:
    mp3 = OUT / f"{s['id']}.mp3"
    if mp3.exists() and not os.environ.get("FORCE"):
        continue
    body = json.dumps({"text": s["text"], "model_id": "eleven_multilingual_v2", "voice_settings": SETTINGS}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    mp3.write_bytes(base64.b64decode(r["audio_base64"]))
    (OUT / f"{s['id']}.json").write_text(json.dumps(r["alignment"], ensure_ascii=False))
    print("ok", s["id"], r["alignment"]["character_end_times_seconds"][-1])
