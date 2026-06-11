"""
음악 분석 - Gemini(가사+감정) + Whisper(타임스탬프) 하이브리드

Step 1: Whisper  → 단어별 정밀 타임스탬프
Step 2: Gemini   → 정확한 가사 + 감정 (타임스탬프 요청 안 함)
Step 3: Align    → Gemini 가사를 Whisper 타임라인에 fuzzy match로 붙이기

사용법: python3 scripts/gemini_audio_analyze.py <오디오파일경로>
"""
import os
import re
import sys
import json
import time
import difflib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
except ImportError:
    print("openai 패키지 필요: pip install openai")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types as gtypes
    gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
except ImportError:
    print("google-genai 패키지 필요: pip install google-genai")
    sys.exit(1)


# ── Step 1: Whisper ───────────────────────────────────────────

def whisper_transcribe(audio_path: str) -> dict:
    """단어 단위 정밀 타임스탬프 추출"""
    print("[1/3] Whisper 타임스탬프 분석 중...")
    with open(audio_path, "rb") as f:
        result = openai_client.audio.transcriptions.create(
            file=f,
            model="whisper-1",
            language="ko",
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
    words = [
        {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
        for w in (result.words or [])
    ]
    print(f"    → {len(words)}개 단어 추출 / 총 길이 {result.duration:.1f}초")
    return {"duration": result.duration or 0, "words": words}


# ── Step 2: Gemini ────────────────────────────────────────────

GEMINI_PROMPT = """이 음악 파일의 가사와 감정을 분석해주세요.
타임스탬프는 필요 없습니다. 가사 텍스트를 최대한 정확하게 전사해주세요.

아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "type": "music 또는 speech 또는 instrumental",
  "language": "ko",
  "overall_emotion": "전체 감정",
  "overall_mood": "전반적인 분위기",
  "music_analysis": {
    "tempo": "빠름/보통/느림",
    "genre_hint": "장르",
    "instruments": ["악기1", "악기2"],
    "vocal_style": "보컬 스타일"
  },
  "segments": [
    {
      "text": "가사 한 구절 (정확하게)",
      "emotion": "감정",
      "energy": "low/medium/high",
      "notes": "코러스/브릿지/아웃트로 등 (없으면 빈 문자열)"
    }
  ]
}"""


def gemini_analyze(audio_path: str) -> dict:
    """가사 + 감정 분석 (타임스탬프 없이)"""
    print("[2/3] Gemini 가사/감정 분석 중...")
    path = Path(audio_path)
    mime_type = _get_mime_type(path.suffix)
    file_size_mb = path.stat().st_size / (1024 * 1024)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    if file_size_mb <= 19:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                GEMINI_PROMPT,
            ],
        )
    else:
        uploaded = gemini_client.files.upload(
            file=audio_path,
            config=gtypes.UploadFileConfig(mime_type=mime_type),
        )
        while uploaded.state == "PROCESSING":
            time.sleep(2)
            uploaded = gemini_client.files.get(name=uploaded.name)
        if uploaded.state == "FAILED":
            raise RuntimeError("Gemini 파일 업로드 실패")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                gtypes.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type),
                GEMINI_PROMPT,
            ],
        )
        gemini_client.files.delete(name=uploaded.name)

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])

    result = json.loads(raw)
    print(f"    → {len(result.get('segments', []))}개 세그먼트 추출")
    return result


# ── Step 3: Align ─────────────────────────────────────────────

def _normalize(text: str) -> str:
    """한글+숫자만, 공백 제거 (fuzzy match용)"""
    return re.sub(r'[^\uAC00-\uD7A3\d]', '', text)


def build_char_timeline(words: list) -> list:
    """단어 타임스탬프 → 문자 단위 타임라인
    반환: [(char, start_sec, end_sec), ...]
    """
    timeline = []
    for w in words:
        norm = _normalize(w["word"])
        for c in norm:
            timeline.append((c, w["start"], w["end"]))
    return timeline


def align_segment(seg_text: str, char_timeline: list, search_from: int) -> tuple:
    """Gemini 한 구절을 char_timeline에서 찾아 (start_sec, end_sec, next_pos) 반환"""
    seg_clean = _normalize(seg_text)
    if not seg_clean or search_from >= len(char_timeline):
        return None, None, search_from

    tl_chars = "".join(c for c, _, _ in char_timeline)
    seg_len = len(seg_clean)
    search_window = tl_chars[search_from: search_from + seg_len * 6]  # 최대 6배 앞까지 탐색

    best_score = 0.0
    best_offset = 0

    for i in range(max(1, len(search_window) - seg_len + 1)):
        candidate = search_window[i: i + seg_len]
        score = difflib.SequenceMatcher(None, seg_clean, candidate).ratio()
        if score > best_score:
            best_score = score
            best_offset = i
        if score > 0.95:
            break

    abs_start = search_from + best_offset
    abs_end = min(abs_start + seg_len - 1, len(char_timeline) - 1)

    start_sec = char_timeline[abs_start][1]
    end_sec = char_timeline[abs_end][2]
    next_pos = abs_start + seg_len  # 다음 세그먼트 탐색 시작점

    return round(start_sec, 3), round(end_sec, 3), next_pos


def align_lyrics_to_timestamps(gemini_segments: list, whisper_words: list) -> list:
    """Gemini 가사 세그먼트에 Whisper 타임스탬프 붙이기"""
    print("[3/3] 가사-타임스탬프 정렬 중...")
    char_timeline = build_char_timeline(whisper_words)
    search_pos = 0
    result = []

    for seg in gemini_segments:
        start_sec, end_sec, search_pos = align_segment(seg["text"], char_timeline, search_pos)
        result.append({
            "start": _sec_to_mmss(start_sec) if start_sec is not None else "??:??",
            "end":   _sec_to_mmss(end_sec)   if end_sec   is not None else "??:??",
            "start_sec": start_sec,
            "end_sec":   end_sec,
            "text":    seg["text"],
            "emotion": seg.get("emotion", ""),
            "energy":  seg.get("energy", ""),
            "notes":   seg.get("notes", ""),
        })

    print(f"    → {len(result)}개 세그먼트 정렬 완료")
    return result


# ── Merge & Output ────────────────────────────────────────────

def build_result(whisper: dict, gemini: dict, aligned_segments: list) -> dict:
    return {
        "type":           gemini.get("type", "music"),
        "language":       gemini.get("language", "ko"),
        "duration_sec":   round(whisper["duration"], 2),
        "duration":       _sec_to_mmss(whisper["duration"]),
        "overall_emotion": gemini.get("overall_emotion", ""),
        "overall_mood":   gemini.get("overall_mood", ""),
        "music_analysis": gemini.get("music_analysis", {}),
        "segments":       aligned_segments,
        "words":          whisper["words"],  # 단어 타임스탬프 원본 보존
    }


def print_result(result: dict):
    print("\n" + "=" * 66)
    print(f"  {result['type']}  |  {result['language']}  |  {result['duration']} ({result['duration_sec']}초)")
    print(f"  감정: {result['overall_emotion']}  |  분위기: {result['overall_mood']}")
    m = result.get("music_analysis", {})
    if m:
        print(f"  장르: {m.get('genre_hint')}  |  템포: {m.get('tempo')}  |  악기: {', '.join(m.get('instruments', []))}")
        if m.get("vocal_style"):
            print(f"  보컬: {m['vocal_style']}")

    segs = result.get("segments", [])
    print(f"\n  [구간 분석] {len(segs)}개 세그먼트")
    print(f"  {'시간':13} {'감정':12} {'E':4} 가사")
    print(f"  {'-'*62}")
    for s in segs:
        t = f"{s['start']}-{s['end']}"
        em = s.get("emotion", "")[:10]
        en = s.get("energy", "")[:3]
        txt = s.get("text", "")[:32]
        note = f" [{s['notes']}]" if s.get("notes") else ""
        print(f"  {t:13} {em:12} {en:4} {txt}{note}")
    print("=" * 66)


def _sec_to_mmss(sec) -> str:
    if sec is None:
        return "??:??"
    return f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"


def _get_mime_type(suffix: str) -> str:
    return {
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".aiff": "audio/aiff",
        ".aac": "audio/aac",  ".ogg": "audio/ogg",  ".flac": "audio/flac",
        ".m4a": "audio/mp4",
    }.get(suffix.lower(), "audio/mpeg")


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/gemini_audio_analyze.py <오디오파일경로>")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.isabs(audio_path):
        audio_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), audio_path)
    if not os.path.exists(audio_path):
        print(f"파일 없음: {audio_path}")
        sys.exit(1)

    print(f"\n분석 시작: {Path(audio_path).name}  ({Path(audio_path).stat().st_size/1024/1024:.1f} MB)\n")

    whisper_data  = whisper_transcribe(audio_path)
    gemini_data   = gemini_analyze(audio_path)
    aligned       = align_lyrics_to_timestamps(gemini_data["segments"], whisper_data["words"])
    result        = build_result(whisper_data, gemini_data, aligned)

    print_result(result)

    out_path = Path(audio_path).with_suffix(".analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")
