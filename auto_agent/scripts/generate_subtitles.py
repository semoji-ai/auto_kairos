"""
Subtitle Sync Script -- Hybrid (WhisperX + Gemini)

1차: WhisperX forced alignment (정밀 word-level)
2차: 품질 검증 -> 실패 시 Gemini segment timestamps로 교정
"""
import json
import os
import sys
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple

from dotenv import load_dotenv

from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")

from auto_agent.scripts.project_paths import get_project_dir

MAX_CHARS_PER_LINE = 30
PAUSE_THRESHOLD = 0.25


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# Korean josa/clause patterns for natural splitting
JOSA_PATTERNS = re.compile(r'(?<=[가-힣])(은|는|이|가|을|를|에서|에게|으로|로|와|과|의|도|만|까지|부터|보다|마저|조차|밖에)')
CLAUSE_PATTERNS = re.compile(r'(지만|는데|면서|하고|하며|고서|어서|아서|니까|으니|때문에|위해|위해서)')


def find_split_points(text: str) -> List[Tuple[int, int]]:
    """Find natural split points in Korean text. Returns [(position, priority)]."""
    points = []
    for m in re.finditer(r'[.!?]', text):
        pos = m.start()
        char = text[pos]
        if char == '.':
            before_digit = pos > 0 and text[pos - 1].isdigit()
            after_digit = pos + 1 < len(text) and text[pos + 1].isdigit()
            if before_digit and after_digit:
                continue
        end_pos = m.end()
        if end_pos < len(text) and text[end_pos] in '"\u201D\u300D':
            end_pos += 1
        points.append((end_pos, 1))
    for m in re.finditer(r',', text):
        pos = m.start()
        # 숫자 사이 쉼표(1,500 등)는 분할 대상에서 제외
        before_digit = pos > 0 and text[pos - 1].isdigit()
        after_digit = pos + 1 < len(text) and text[pos + 1].isdigit()
        if before_digit and after_digit:
            continue
        points.append((m.end(), 2))
    for m in CLAUSE_PATTERNS.finditer(text):
        points.append((m.end(), 3))
    for m in JOSA_PATTERNS.finditer(text):
        points.append((m.end(), 4))
    return sorted(points, key=lambda x: x[0])


def smart_split(text: str) -> List[str]:
    """Split text into lines of max MAX_CHARS_PER_LINE chars at natural boundaries."""
    if len(text) <= MAX_CHARS_PER_LINE:
        return [text.strip()]

    lines = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= MAX_CHARS_PER_LINE:
            lines.append(remaining.strip())
            break

        split_points = find_split_points(remaining[:MAX_CHARS_PER_LINE + 10])
        valid_points = [(pos, pri) for pos, pri in split_points
                        if 5 <= pos <= MAX_CHARS_PER_LINE + 5]

        if valid_points:
            best = min(valid_points, key=lambda x: (x[1], -x[0]))
            pos = best[0]
        else:
            pos = MAX_CHARS_PER_LINE
            space_pos = remaining[:MAX_CHARS_PER_LINE].rfind(' ')
            if space_pos > 10:
                pos = space_pos + 1

        lines.append(remaining[:pos].strip())
        remaining = remaining[pos:].strip()

    return [l for l in lines if l]


def match_lines_to_timestamps(lines: List[str], words: List[Dict], audio_duration: float) -> List[Dict]:
    """Match subtitle lines to word-level timestamps via fuzzy text matching."""
    if not words:
        per_line = audio_duration / max(len(lines), 1)
        entries = []
        for i, line in enumerate(lines):
            entries.append({
                "index": i + 1,
                "text": line,
                "startSec": round(i * per_line, 3),
                "endSec": round((i + 1) * per_line, 3),
            })
        return entries

    entries = []
    word_idx = 0
    total_words = len(words)

    for i, line in enumerate(lines):
        line_chars = line.replace(' ', '')
        matched_chars = 0
        start_time = words[word_idx]["start"] if word_idx < total_words else (entries[-1]["endSec"] if entries else 0)
        end_time = start_time

        while word_idx < total_words and matched_chars < len(line_chars):
            w = words[word_idx]
            matched_chars += len(w["word"].replace(' ', ''))
            end_time = w["end"]
            word_idx += 1

        entries.append({
            "index": i + 1,
            "text": line,
            "startSec": round(start_time, 3),
            "endSec": round(end_time, 3),
        })

    # Fix zero/negative-duration entries
    i = 0
    while i < len(entries):
        if entries[i]["startSec"] >= entries[i]["endSec"]:
            block_start = i
            while i < len(entries) and entries[i]["startSec"] >= entries[i]["endSec"]:
                i += 1
            block_end = i
            range_start = entries[block_start - 1]["endSec"] if block_start > 0 else 0.0
            range_end = entries[block_end]["startSec"] if block_end < len(entries) else audio_duration
            if range_end <= range_start and block_start > 0:
                range_start = entries[block_start - 1]["startSec"] + (entries[block_start - 1]["endSec"] - entries[block_start - 1]["startSec"]) * 0.5
                entries[block_start - 1]["endSec"] = round(range_start, 3)
            if range_end <= range_start and block_end < len(entries):
                range_end = entries[block_end]["endSec"]
                entries[block_end]["startSec"] = round(range_end - (entries[block_end]["endSec"] - entries[block_end]["startSec"]) * 0.5, 3)
                range_end = entries[block_end]["startSec"]
            count = block_end - block_start
            per_entry = (range_end - range_start) / max(count, 1)
            for k in range(block_start, block_end):
                entries[k]["startSec"] = round(range_start + (k - block_start) * per_entry, 3)
                entries[k]["endSec"] = round(range_start + (k - block_start + 1) * per_entry, 3)
        else:
            i += 1

    # 씬 전체를 자막으로 채우기: 첫 자막은 0.0부터, 마지막은 audio_duration까지
    if entries:
        entries[0]["startSec"] = 0.0
        entries[-1]["endSec"] = round(audio_duration, 3)

    # 자막 간 갭 제거: 각 자막의 endSec = 다음 자막의 startSec
    for j in range(len(entries) - 1):
        entries[j]["endSec"] = entries[j + 1]["startSec"]

    # 씬 내 자막 전환 선행 offset (첫 자막 제외, 0.3초 앞당김)
    SUBTITLE_LEAD_OFFSET = 0.3
    for j in range(1, len(entries)):
        entries[j]["startSec"] = round(max(
            entries[j - 1]["startSec"] + 0.1,  # 이전 자막과 최소 0.1초 간격 보장
            entries[j]["startSec"] - SUBTITLE_LEAD_OFFSET,
        ), 3)
        # 이전 자막의 endSec도 맞춰줌
        entries[j - 1]["endSec"] = entries[j]["startSec"]

    return entries


def check_alignment_quality(entries: List[Dict], audio_duration: float) -> bool:
    """WhisperX alignment 품질 검증.

    실패 조건:
    - 자막 하나가 전체 시간의 55% 이상 차지
    - 자막 하나가 1초 미만이면서 텍스트가 15자 이상
    """
    if not entries or audio_duration <= 0:
        return False

    for e in entries:
        dur = e["endSec"] - e["startSec"]
        text_len = len(e["text"].replace(' ', ''))
        # 하나가 전체의 55%+ 차지
        if dur / audio_duration > 0.55 and len(entries) > 1:
            return False
        # 긴 텍스트가 너무 짧은 시간에 몰림
        if dur < 1.0 and text_len > 15:
            return False

    return True


def get_gemini_word_timestamps(gemini_client, audio_path: Path, narration: str) -> List[Dict]:
    """Gemini로 word-level timestamps를 추출."""
    from google.genai import types

    uploaded = gemini_client.files.upload(file=audio_path)

    prompt = f"""이 한국어 오디오의 각 단어별 시작/끝 타임스탬프를 JSON으로 정확하게 추출해주세요.

원본 텍스트:
{narration}

응답 형식 (JSON 배열만, 다른 텍스트 없이):
[
  {{"word": "첫번째단어", "start": 0.0, "end": 0.5}},
  {{"word": "두번째단어", "start": 0.5, "end": 1.2}},
  ...
]

중요:
- 타임스탬프는 초 단위 소수점으로
- 모든 단어를 빠짐없이 포함
- 실제 발화 타이밍에 맞춰 정확하게"""

    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=uploaded.uri)),
                    types.Part(text=prompt),
                ]
            )
        ],
    )

    text = response.text.strip()
    # JSON 추출 (```json ... ``` 래핑 제거)
    if '```' in text:
        text = re.sub(r'```json?\s*', '', text)
        text = re.sub(r'```\s*$', '', text)

    try:
        words = json.loads(text)
        return [{"word": w["word"], "start": float(w["start"]), "end": float(w["end"])} for w in words]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def fix_decimal_splits(lines: List[str]) -> List[str]:
    """소수점에서 잘린 줄을 병합한다."""
    if len(lines) < 2:
        return lines
    merged = [lines[0]]
    for i in range(1, len(lines)):
        prev = merged[-1]
        curr = lines[i]
        if re.search(r'\d\.$', prev) and re.match(r'\d', curr):
            merged[-1] = prev + curr
        else:
            merged.append(curr)
    return merged


def fix_quote_splits(lines: List[str]) -> List[str]:
    """혼자 남은 닫는 따옴표를 이전 줄에 병합."""
    if len(lines) < 2:
        return lines
    merged = [lines[0]]
    for i in range(1, len(lines)):
        curr = lines[i].strip()
        if curr in ('"', '\u201D', '\u300D'):
            merged[-1] = merged[-1] + curr
        else:
            merged.append(lines[i])
    return [l for l in merged if l.strip()]


def generate_srt(entries: List[Dict]) -> str:
    """Generate SRT format string."""
    srt_lines = []
    for e in entries:
        srt_lines.append(str(e["index"]))
        srt_lines.append(f'{format_srt_time(e["startSec"])} --> {format_srt_time(e["endSec"])}')
        srt_lines.append(e["text"])
        srt_lines.append("")
    return "\n".join(srt_lines)


def main():
    try:
        import whisperx
        WHISPERX_AVAILABLE = True
    except Exception:
        WHISPERX_AVAILABLE = False
        whisperx = None
    from google import genai

    # PROJECT_DIR 우선 (uuid 마이그레이션 후 정확한 경로)
    project_dir_env = os.environ.get("PROJECT_DIR")
    if project_dir_env:
        project_dir = Path(project_dir_env)
    else:
        project_slug = os.environ.get("PROJECT_NAME", "")
        if project_slug:
            # DB에서 정확한 output_dir 조회
            try:
                from auto_agent.db.project_manager import ProjectManager
                pm = ProjectManager()
                project = pm.resolve_project(project_slug)
                if project:
                    project_dir = Path(project["output_dir"])
                else:
                    from auto_agent.paths import get_workspace_dir
                    project_dir = get_workspace_dir() / "output" / project_slug
            except Exception:
                from auto_agent.paths import get_workspace_dir
                project_dir = get_workspace_dir() / "output" / project_slug
        else:
            project_dir = get_project_dir()
    scene_specs_path = project_dir / "scene_specs.json"
    if not scene_specs_path.exists():
        print(f"ERROR: {scene_specs_path} 없음")
        sys.exit(1)

    AUDIO_DIR = project_dir / "audio"
    SUBTITLE_DIR = project_dir / "subtitles"
    SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)

    with open(scene_specs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data["scenes"]
    total = len(scenes)
    all_subtitles = []

    # WhisperX 정렬 모델 로드
    device = "cpu"
    model_a, metadata = None, None
    if WHISPERX_AVAILABLE:
        print("Loading WhisperX alignment model (ko)...")
        model_a, metadata = whisperx.load_align_model(language_code="ko", device=device)
        print("Model loaded.")
    else:
        print("WhisperX unavailable -- proportional fallback mode")

    # Gemini 클라이언트 (fallback용)
    api_key = os.getenv("GOOGLE_API_KEY")
    gemini_client = genai.Client(api_key=api_key) if api_key else None
    if gemini_client:
        print("Gemini fallback: enabled\n")
    else:
        print("Gemini fallback: disabled (no GOOGLE_API_KEY)\n")

    whisperx_ok = 0
    gemini_fallback = 0
    proportional_fallback = 0

    print(f"Generating subtitles for {total} scenes...")

    for i, scene in enumerate(scenes):
        num = scene.get("sceneNumber") or scene["scene_number"]
        narration = scene.get("narration", "")
        narration_tts = scene.get("narration_tts", narration)
        audio_path = AUDIO_DIR / f"scene_{num:03d}.mp3"
        srt_path = SUBTITLE_DIR / f"scene_{num:03d}.srt"

        if not narration.strip():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP (empty)")
            continue

        if not audio_path.exists():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP (no audio)")
            continue

        if srt_path.exists():
            print(f"  [{i+1}/{total}] Scene {num}: EXISTS")
            continue

        try:
            # 오디오 로드
            if WHISPERX_AVAILABLE:
                audio = whisperx.load_audio(str(audio_path))
                duration = len(audio) / 16000
            else:
                import mutagen.mp3 as _mp3
                try:
                    _info = _mp3.MP3(str(audio_path)).info
                    duration = _info.length
                except Exception:
                    duration = max(len(narration_tts) * 0.07, 3.0)  # 글자당 70ms 추정
                audio = None

            # 디스플레이용 라인 분할 (원본 narration)
            display_lines = smart_split(narration)
            display_lines = fix_decimal_splits(display_lines)
            display_lines = fix_quote_splits(display_lines)

            # TTS 라인 분할 (narration_tts -- 실제 음성과 일치)
            tts_lines = smart_split(narration_tts)
            tts_lines = fix_decimal_splits(tts_lines)
            tts_lines = fix_quote_splits(tts_lines)

            # === 1차: WhisperX forced alignment (narration_tts로 alignment) ===
            if WHISPERX_AVAILABLE:
                segments = [{"text": narration_tts, "start": 0.0, "end": duration}]
                result = whisperx.align(segments, model_a, metadata, audio, device, return_char_alignments=False)
            else:
                result = {"segments": []}

            words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    if "start" in w and "end" in w:
                        words.append({"word": w["word"], "start": w["start"], "end": w["end"]})

            # TTS 라인으로 타임스탬프 매칭 (음성과 텍스트가 일치하므로 정확)
            entries = match_lines_to_timestamps(tts_lines, words, duration)
            source = "whisperx" if WHISPERX_AVAILABLE else "proportional"

            # === 2차: 품질 검증 ===
            if not check_alignment_quality(entries, duration):
                # WhisperX 실패 -> Gemini fallback
                if gemini_client:
                    try:
                        gemini_words = get_gemini_word_timestamps(gemini_client, audio_path, narration_tts)
                        if gemini_words:
                            entries = match_lines_to_timestamps(tts_lines, gemini_words, duration)
                            source = "gemini"
                            gemini_fallback += 1
                            time.sleep(1)  # rate limiting
                        else:
                            entries = match_lines_to_timestamps(tts_lines, [], duration)
                            source = "proportional"
                            proportional_fallback += 1
                    except Exception as ge:
                        print(f"    Gemini fallback error: {ge}")
                        entries = match_lines_to_timestamps(tts_lines, [], duration)
                        source = "proportional"
                        proportional_fallback += 1
                else:
                    entries = match_lines_to_timestamps(tts_lines, [], duration)
                    source = "proportional"
                    proportional_fallback += 1
            else:
                whisperx_ok += 1

            # 디스플레이 텍스트로 교체 (타임스탬프는 유지)
            if len(display_lines) == len(entries):
                for j, entry in enumerate(entries):
                    entry["text"] = display_lines[j]
            else:
                # 라인 수 불일치 -> 전체 시간을 디스플레이 라인에 비례 분배
                total_chars = sum(len(l.replace(' ', '')) for l in display_lines)
                t_start = entries[0]["startSec"]
                t_total = entries[-1]["endSec"] - t_start
                new_entries = []
                cursor = t_start
                for j, line in enumerate(display_lines):
                    char_ratio = len(line.replace(' ', '')) / max(total_chars, 1)
                    line_dur = t_total * char_ratio
                    new_entries.append({
                        "index": j + 1,
                        "text": line,
                        "startSec": round(cursor, 3),
                        "endSec": round(cursor + line_dur, 3),
                    })
                    cursor += line_dur
                entries = new_entries

            # Write SRT
            srt_content = generate_srt(entries)
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            all_subtitles.append({
                "sceneNumber": num,
                "audioDurationSec": round(duration, 3),
                "entries": entries,
                "wordCount": len(words),
                "source": source,
            })

            print(f"  [{i+1}/{total}] Scene {num}: OK [{source}] ({len(entries)} lines, {duration:.1f}s)")

        except Exception as e:
            print(f"  [{i+1}/{total}] Scene {num}: ERROR - {e}")
            import traceback
            traceback.print_exc()

    # Write aggregate subtitles.json
    with open(project_dir / "subtitles.json", "w", encoding="utf-8") as f:
        json.dump({"scenes": all_subtitles}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"Done: {len(all_subtitles)} subtitle files generated")
    print(f"  WhisperX OK: {whisperx_ok}")
    print(f"  Gemini fallback: {gemini_fallback}")
    print(f"  Proportional fallback: {proportional_fallback}")

    # ── Supabase 즉시 업로드 + 에셋 등록 ──
    _upload_subtitles_to_supabase(project_dir, all_subtitles)


def _upload_subtitles_to_supabase(output_dir, all_subtitles: list):
    """생성된 자막 에셋을 Supabase Storage에 업로드."""
    try:
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            return
    except ImportError:
        return

    project_slug = os.environ.get("PROJECT_NAME", "")
    if not project_slug:
        return

    try:
        from auto_agent.sync import SyncManager
        sync = SyncManager(project_slug=project_slug, project_dir=Path(output_dir))
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=project_slug)
        if not project:
            return
        pid = project["id"]
    except Exception:
        return

    uploaded = 0
    subtitles_dir = Path(output_dir) / "subtitles"
    if not subtitles_dir.exists():
        return

    for srt in sorted(subtitles_dir.glob("scene_*.srt")):
        import re
        m = re.match(r"scene_(\d{3})", srt.stem)
        scene_num = int(m.group(1)) if m else None
        try:
            sync.register_asset(
                project_id=pid,
                local_path=srt,
                asset_type="subtitle",
                scene_number=scene_num,
            )
            uploaded += 1
        except Exception:
            pass

    if uploaded:
        print(f"  [SYNC] Supabase 자막 업로드 완료: {uploaded}개")


if __name__ == "__main__":
    main()
