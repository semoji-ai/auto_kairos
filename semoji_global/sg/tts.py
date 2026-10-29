"""ElevenLabs TTS(세모지 보이스)와 정렬 기반 트림."""
import base64
import hashlib
import os
import json
import subprocess
import urllib.request

_SKIP = set(" \t\n.,!?;:'\"…-—()[]，。！？；：、“”‘’《》（）")


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


def text_hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def should_synth(fit, seg_id, text, mp3_path, force=False):
    """같은 텍스트로 이미 만든 mp3가 있으면 다시 합성하지 않는다(과금 방지)."""
    if force or not os.path.exists(mp3_path):
        return True
    return fit.get(seg_id, {}).get("hash") != text_hash(text)


_ZH_DIGITS = "零一二三四五六七八九"


def _zh_small(n):
    """1~31 → 一·十一·二十一 식 한자 읽기(월·일용)."""
    t, o = divmod(n, 10)
    return ("" if t == 0 else ("" if t == 1 else _ZH_DIGITS[t]) + "十") + ("" if o == 0 and t else _ZH_DIGITS[o])


def zh_spoken(text):
    """중국어 TTS 읽기용: 네 자리 연도는 한 자씩(1831年→一八三一年), 월·일은 한자 수(4月12日→四月十二日).
    eleven_v4가 아라비아 숫자 연도를 엉뚱하게 읽는 문제(실측) 대응. 다른 숫자는 그대로."""
    import re
    text = re.sub(r"(?<!\d)(1\d{3}|20\d{2})(?=年)", lambda m: "".join(_ZH_DIGITS[int(c)] for c in m.group(1)), text)
    text = re.sub(r"(?<![\d.])(1[0-2]|[1-9])(?=月)", lambda m: _zh_small(int(m.group(1))), text)
    text = re.sub(r"(?<![\d.])(3[01]|[12]\d|[1-9])(?=日)", lambda m: _zh_small(int(m.group(1))), text)
    return re.sub(r"年(?=[一二三四五六七八九十]+月)", "年，", text)   # 연도와 월을 붙이면 뭉개짐(실측) → 쉼표로 끊음


_CLAUSE_END = "，。！？；：、,.!?;:"


def context_text(prev, text, nxt, n=10):
    """앞 문장 끝 절 + 본문 + 다음 문장 첫 절(각 최대 n자)을 이어 붙인 합성용 문장과 본문 위치 [a, b).
    짧은 구간을 단독 합성하면 첫소리·숫자가 뭉개지고, eleven_v4의 previous/next_text는 이웃 문장을 실제로 읽어 버림(실측)
    → 이웃 일부를 함께 읽히고 정렬로 본문만 잘라 낸다."""
    pre = ""
    if prev:
        p = prev.rstrip()
        body = p.rstrip(_CLAUSE_END)
        cut = max(body.rfind(c) for c in _CLAUSE_END)
        pre = body[cut + 1:][-n:] + (p[len(body):] or "，")
    post = ""
    if nxt:
        cut = min([nxt.find(c) for c in _CLAUSE_END if nxt.find(c) >= 0] or [len(nxt)])
        post = nxt[:min(cut, n)]
    return pre + text + post, len(pre), len(pre) + len(text)


def slice_alignment(al, a, b):
    return {"characters": al["characters"][a:b],
            "character_start_times_seconds": al["character_start_times_seconds"][a:b],
            "character_end_times_seconds": al["character_end_times_seconds"][a:b]}


def cut_bounds(spans, t0, t1, has_prev, has_next, win=0.5):
    """정렬로 얻은 본문 구간 [t0, t1]을 실제 쉼(발화 구간 사이 틈)에 맞춘다.
    v4 정렬은 글자 간격을 고르게 추정해 경계가 어긋남(실측) → 앞 문맥이 있으면 t0 근처 틈 뒤의 발화 시작,
    뒤 문맥이 있으면 t1 근처 틈 앞의 발화 끝. 근처(win초)에 틈이 없으면 정렬값 그대로."""
    if not spans:
        return t0, t1
    gaps = [(spans[k][1], spans[k + 1][0]) for k in range(len(spans) - 1)]
    near = lambda t, gs: min(gs, key=lambda g: abs((g[0] + g[1]) / 2 - t)) if gs else None
    tol = 0.15                                        # 정렬 오차 허용 — 본문 안쪽 쉼(쉼표 등)을 경계로 잡지 않게
    if has_prev:
        g = near(t0, [x for x in gaps if x[1] <= t0 + tol])
        a = g[1] if g and abs((g[0] + g[1]) / 2 - t0) <= win else t0
    else:
        a = spans[0][0]
    if has_next:
        g = near(t1, [x for x in gaps if x[0] >= t1 - tol])
        b = g[0] if g and abs((g[0] + g[1]) / 2 - t1) <= win else t1
    else:
        b = spans[-1][1]
    return a, b
