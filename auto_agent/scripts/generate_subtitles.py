"""
Subtitle Sync Script — Hybrid (WhisperX + Gemini)

1차: WhisperX forced alignment (정밀 word-level)
2차: 품질 검증 → 실패 시 Gemini segment timestamps로 교정
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
    total_ms = max(0, round(seconds * 1000))
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1_000
    ms = total_ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_time(s: str) -> float:
    """SRT 타임코드 → 초. 예: '00:01:23,456' → 83.456"""
    h, m, rest = s.split(':')
    sec, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(content: str) -> List[Dict]:
    """SRT 파일 내용을 entries로 파싱.

    Returns: [{"index", "text", "startSec", "endSec"}, ...]
    멱등성 — 기존 SRT를 다시 읽을 때 사용 (subtitles.json 재생성).
    """
    entries: List[Dict] = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = [ln for ln in block.strip().split('\n') if ln.strip()]
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        time_line = lines[1].strip()
        if ' --> ' not in time_line:
            continue
        try:
            start_str, end_str = time_line.split(' --> ')
            start_sec = parse_srt_time(start_str.strip())
            end_sec = parse_srt_time(end_str.strip())
        except Exception:
            continue
        text = '\n'.join(lines[2:]).strip()
        entries.append({
            "index": idx,
            "text": text,
            "startSec": round(start_sec, 3),
            "endSec": round(end_sec, 3),
        })
    return entries


def load_existing_subtitles(project_dir: Path) -> List[Dict]:
    subs_path = project_dir / "subtitles.json"
    if not subs_path.exists():
        return []
    try:
        data = json.loads(subs_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    scenes = data.get("scenes")
    return scenes if isinstance(scenes, list) else []


def merge_subtitle_scenes(existing_scenes: List[Dict], updated_scenes: List[Dict]) -> List[Dict]:
    merged = {}
    for scene in existing_scenes or []:
        scene_number = scene.get("sceneNumber") or scene.get("scene_number")
        if scene_number is not None:
            merged[int(scene_number)] = scene
    for scene in updated_scenes or []:
        scene_number = scene.get("sceneNumber") or scene.get("scene_number")
        if scene_number is not None:
            merged[int(scene_number)] = scene
    return [merged[k] for k in sorted(merged)]


def _normalize_alignment_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _preprocess_text_for_tts_alignment(text: str) -> str:
    if not text:
        return ""
    try:
        from auto_agent.tools.korean_tts_preprocessor import KoreanTTSPreprocessor
        processed, _changes = KoreanTTSPreprocessor().process_text(text)
        return processed.strip()
    except Exception:
        return (text or "").strip()


def derive_tts_lines_from_display_lines(display_lines: List[str], narration_tts: str) -> List[str] | None:
    if not display_lines or not narration_tts:
        return None
    derived = [_preprocess_text_for_tts_alignment(line) for line in display_lines]
    if any(not line for line in derived):
        return None
    if _normalize_alignment_text("".join(derived)) != _normalize_alignment_text(narration_tts):
        return None
    return derived


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
            # 슬라이스 끝에서 after_digit이 False가 되는 경우를 막기 위해
            # 앞이 숫자면 소수점으로 간주하여 분할 제외
            if before_digit:
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
    """Split text into lines of max MAX_CHARS_PER_LINE chars at natural boundaries.

    분할 우선순위:
    1. 문장 끝(마침표/느낌표/물음표) — 30자 초과해도 문장 완결 후 분할
    2. 쉼표
    3. 절 접속어 (지만, 는데, 면서...)
    4. 조사 경계
    5. 공백/강제 분할
    """
    if len(text) <= MAX_CHARS_PER_LINE:
        return [text.strip()]

    lines = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= MAX_CHARS_PER_LINE:
            lines.append(remaining.strip())
            break

        # 1순위: 30자 이내 문장 끝 (마침표/느낌표/물음표)
        # (?<!\d) — 앞이 숫자인 소수점(3.65)은 제외; (?!\d) — 뒤가 숫자면 제외
        # remaining 슬라이스 끝에서 뒤 문자가 잘리는 경우를 막기 위해 +1 여유 포함 후 위치 필터
        sentence_end = re.search(r'(?<!\d)[.!?](?!\d)', remaining[:MAX_CHARS_PER_LINE + 1])
        if sentence_end and sentence_end.start() >= MAX_CHARS_PER_LINE:
            sentence_end = None
        if sentence_end:
            pos = sentence_end.end()
            # 닫는 따옴표가 바로 뒤에 오면 함께 포함
            if pos < len(remaining) and remaining[pos] in '"\u201D\u300D':
                pos += 1
            lines.append(remaining[:pos].strip())
            remaining = remaining[pos:].strip()
            continue

        # 2순위: MAX_CHARS_PER_LINE + 10 범위 내 자연 분할점 탐색
        split_points = find_split_points(remaining[:MAX_CHARS_PER_LINE + 10])
        valid_points = [(pos, pri) for pos, pri in split_points
                        if 5 <= pos <= MAX_CHARS_PER_LINE + 5]

        if valid_points:
            best = min(valid_points, key=lambda x: (x[1], -x[0]))
            pos = best[0]
        else:
            # 강제 분할: 단어 경계(공백) 우선 — 앞에서 찾고 없으면 뒤에서 찾음
            space_pos = remaining[:MAX_CHARS_PER_LINE].rfind(' ')
            if space_pos > 10:
                pos = space_pos + 1
            else:
                fwd = remaining.find(' ', MAX_CHARS_PER_LINE)
                if fwd != -1:
                    pos = fwd + 1
                else:
                    pos = MAX_CHARS_PER_LINE

        lines.append(remaining[:pos].strip())
        remaining = remaining[pos:].strip()

    return [l for l in lines if l]


def chars_to_words(sidecar: dict) -> list:
    """ElevenLabs 문자 타임스탬프 → 단어 단위 타임스탬프 변환.

    공백 또는 문자 배열 끝에서 단어 경계로 분리.
    match_lines_to_timestamps()와 호환되는 형식으로 반환.
    """
    chars = sidecar.get("characters", [])
    starts = sidecar.get("character_start_times_seconds", [])
    ends = sidecar.get("character_end_times_seconds", [])

    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        return []

    words = []
    word_chars = []
    word_start = None
    word_end = None

    for i, ch in enumerate(chars):
        if ch in (" ", "\n", "\t", "\r"):
            if word_chars:
                words.append({
                    "word": "".join(word_chars),
                    "start": round(word_start, 3),
                    "end": round(word_end, 3),
                })
                word_chars = []
                word_start = None
                word_end = None
        else:
            if word_start is None:
                word_start = starts[i]
            word_chars.append(ch)
            word_end = ends[i]

    # 마지막 단어 처리
    if word_chars:
        words.append({
            "word": "".join(word_chars),
            "start": round(word_start, 3),
            "end": round(word_end, 3),
        })

    return words


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

    return entries


def apply_keyword_delay(entries: List[Dict], words: List[Dict]) -> List[Dict]:
    """핵심 데이터(숫자/수치)가 줄 중간에 등장하면 해당 단어 타임스탬프로 자막 시작을 지연.

    조건: 줄 앞에 조사/전치사만 있고 숫자 표현이 이어질 때.
    이전 줄 endSec를 새 startSec로 연장하여 갭 없이 처리.
    """
    if not words or len(entries) < 2:
        return entries

    KEYWORD_RE = re.compile(r'\d[\d,]*(?:[만천백억조%명개년월일위번회달러원kmkgcm])?')
    LEADING_JOSA = re.compile(r'^[은는이가을를의도만까지부터에서에게으로로와과\s]+')

    new_entries = [dict(e) for e in entries]

    for i, entry in enumerate(new_entries):
        text = entry["text"]
        m_keyword = KEYWORD_RE.search(text)
        if not m_keyword:
            continue
        prefix = text[:m_keyword.start()]
        if not prefix.strip():
            continue
        if not LEADING_JOSA.fullmatch(prefix):
            continue

        entry_start = entry["startSec"]
        entry_end = entry["endSec"]
        keyword_clean = re.sub(r'[^\d가-힣a-zA-Z]', '', m_keyword.group(0))

        keyword_start = None
        for w in words:
            if w["start"] < entry_start - 0.15:
                continue
            if w["start"] > entry_end:
                break
            w_clean = re.sub(r'[^\d가-힣a-zA-Z]', '', w["word"])
            if keyword_clean and w_clean and (keyword_clean in w_clean or w_clean in keyword_clean):
                keyword_start = w["start"]
                break

        if keyword_start is None or keyword_start <= entry_start + 0.12:
            continue

        new_entries[i]["startSec"] = round(keyword_start, 3)
        if i > 0:
            new_entries[i - 1]["endSec"] = round(keyword_start, 3)

    return new_entries


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


def fix_dangling_connectors(lines: List[str]) -> List[str]:
    """줄 시작에 홀로 남겨진 절 접속어를 이전 줄에 병합.

    예: ["...열었는", "데, 그 결과는"] → ["...열었는데,", "그 결과는"]
    절 접속어: 는데/지만/면서/하고/하며/고서/어서/아서/니까/으니 등이 줄 시작에 오면 이전 줄 끝에 붙임.
    """
    if len(lines) < 2:
        return lines
    CONNECTOR_PREFIX = re.compile(r'^(는데|지만|면서|하고|하며|고서|어서|아서|니까|으니|기에|므로|지라|더니)(,|\.|\s|$)')
    merged = [lines[0]]
    for line in lines[1:]:
        m = CONNECTOR_PREFIX.match(line)
        if m:
            connector = m.group(1)
            rest = line[len(connector):].lstrip()
            merged[-1] = merged[-1] + connector
            if rest:
                merged.append(rest)
        else:
            merged.append(line)
    return [l for l in merged if l.strip()]


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

    # --scene N 옵션: 특정 씬만 처리 (TTS 재생성 시 전체 재처리 방지)
    target_scene = None
    argv = sys.argv[1:]
    for idx, arg in enumerate(argv):
        if arg == "--scene" and idx + 1 < len(argv):
            target_scene = int(argv[idx + 1])
            break
    if target_scene is not None:
        scenes = [s for s in scenes if (s.get("sceneNumber") or s.get("scene_number")) == target_scene]
        # 대상 씬의 기존 SRT 삭제하여 재생성 강제 (sceneId + sceneNumber 둘 다)
        sid_target = scenes[0].get("sceneId") if scenes else None
        if sid_target:
            srt_target_sid = SUBTITLE_DIR / f"scene_{sid_target}.srt"
            if srt_target_sid.exists():
                srt_target_sid.unlink()
        srt_target = SUBTITLE_DIR / f"scene_{target_scene:03d}.srt"
        if srt_target.exists():
            srt_target.unlink()

    existing_subtitles = load_existing_subtitles(project_dir) if target_scene is not None else []

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
        scene_id = scene.get("sceneId", "")
        narration = scene.get("narration", "")
        narration_tts = scene.get("narration_tts", narration)
        # sceneId.mp3 우선 → scene_NNN.mp3 폴백
        audio_path = AUDIO_DIR / (f"{scene_id}.mp3" if scene_id and (AUDIO_DIR / f"{scene_id}.mp3").exists() else f"scene_{num:03d}.mp3")
        srt_stem = scene_id if scene_id else f"scene_{num:03d}"
        srt_path = SUBTITLE_DIR / f"{srt_stem}.srt"

        if not narration.strip():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP (empty)")
            continue

        if not audio_path.exists():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP (no audio)")
            continue

        if srt_path.exists():
            # 멱등성: SRT가 이미 있어도 all_subtitles에 추가해서 subtitles.json이
            # 빈 배열로 저장되지 않도록 함. 이전 버그: continue로 빠져 all_subtitles 비었음 →
            # subtitles.json {"scenes":[]} → manifest scene.subtitles 빈 배열.
            try:
                existing_srt = srt_path.read_text(encoding="utf-8")
                existing_entries = parse_srt(existing_srt)
                if existing_entries:
                    # duration 추정: 마지막 entry endSec
                    duration = existing_entries[-1]["endSec"]
                    all_subtitles.append({
                        "sceneNumber": num,
                        "audioDurationSec": round(duration, 3),
                        "entries": existing_entries,
                        "wordCount": 0,
                        "source": "existing_srt",
                    })
                    print(f"  [{i+1}/{total}] Scene {num}: EXISTS (재파싱 {len(existing_entries)}줄)")
                else:
                    print(f"  [{i+1}/{total}] Scene {num}: EXISTS (parse failed)")
            except Exception as e:
                print(f"  [{i+1}/{total}] Scene {num}: EXISTS (재파싱 실패: {e})")
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

            # === 0차: ElevenLabs 사이드카 타임스탬프 (최우선) ===
            sidecar_path = audio_path.with_name(audio_path.stem + ".timestamps.json")
            elevenlabs_words = []
            if sidecar_path.exists():
                try:
                    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                    elevenlabs_words = chars_to_words(sidecar)
                    # 사이드카 끝 시각은 보조 정보로만 사용한다.
                    # 실제 MP3 길이가 더 길면 scene duration은 오디오 길이를 우선 유지해야
                    # 마지막 자막이 씬 종료 전에 사라지지 않는다.
                    end_times = sidecar.get("character_end_times_seconds", [])
                    if end_times:
                        duration = max(duration, round(end_times[-1], 3))
                except Exception as e:
                    print(f"    사이드카 로드 실패: {e}")

            # 디스플레이용 라인 분할 (원본 narration)
            # subtitle_lines 필드가 있으면 에이전트가 미리 분할한 결과를 사용 (우선)
            pre_split = scene.get("subtitle_lines")
            if pre_split and isinstance(pre_split, list) and len(pre_split) > 0:
                display_lines = [l.strip() for l in pre_split if l.strip()]
            else:
                display_lines = smart_split(narration)
                display_lines = fix_decimal_splits(display_lines)
                display_lines = fix_quote_splits(display_lines)
                display_lines = fix_dangling_connectors(display_lines)

            derived_tts_lines = derive_tts_lines_from_display_lines(display_lines, narration_tts)

            # TTS 라인 분할 (narration_tts — 실제 음성과 일치)
            # subtitle_lines_tts 필드가 있으면 에이전트 사전 분할 결과 사용
            pre_split_tts = scene.get("subtitle_lines_tts")
            if pre_split_tts and isinstance(pre_split_tts, list) and len(pre_split_tts) > 0:
                candidate_tts_lines = [l.strip() for l in pre_split_tts if l.strip()]
            else:
                candidate_tts_lines = smart_split(narration_tts)
                candidate_tts_lines = fix_decimal_splits(candidate_tts_lines)
                candidate_tts_lines = fix_quote_splits(candidate_tts_lines)
                candidate_tts_lines = fix_dangling_connectors(candidate_tts_lines)

            # narration → narration_tts 전처리 규칙이 만든 변형은 같은 규칙으로 역매칭한다.
            # line count mismatch 시 비례 분배로 떨어지기 전에 display_lines 기반 전처리 매핑을 우선 사용.
            if derived_tts_lines and len(derived_tts_lines) == len(display_lines):
                tts_lines = derived_tts_lines
            else:
                tts_lines = candidate_tts_lines

            # === 1차: ElevenLabs 사이드카 or WhisperX forced alignment ===
            if elevenlabs_words:
                words = elevenlabs_words
                entries = match_lines_to_timestamps(tts_lines, words, duration)
                entries = apply_keyword_delay(entries, words)
                source = "elevenlabs"
            elif WHISPERX_AVAILABLE:
                segments = [{"text": narration_tts, "start": 0.0, "end": duration}]
                result = whisperx.align(segments, model_a, metadata, audio, device, return_char_alignments=False)
                words = []
                for seg in result.get("segments", []):
                    for w in seg.get("words", []):
                        if "start" in w and "end" in w:
                            words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
                entries = match_lines_to_timestamps(tts_lines, words, duration)
                source = "whisperx"
            else:
                words = []
                entries = match_lines_to_timestamps(tts_lines, [], duration)
                source = "proportional"

            # === 2차: 품질 검증 (ElevenLabs는 신뢰 — whisperx만 검증) ===
            if source != "elevenlabs" and not check_alignment_quality(entries, duration):
                # WhisperX 실패 → Gemini fallback
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
            elif source == "whisperx":
                whisperx_ok += 1

            # 디스플레이 텍스트로 교체 (타임스탬프는 유지)
            if len(display_lines) == len(entries):
                for j, entry in enumerate(entries):
                    entry["text"] = display_lines[j]
            else:
                # 라인 수 불일치 → 전체 시간을 디스플레이 라인에 비례 분배
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
    subtitles_to_write = (
        merge_subtitle_scenes(existing_subtitles, all_subtitles)
        if target_scene is not None
        else all_subtitles
    )
    with open(project_dir / "subtitles.json", "w", encoding="utf-8") as f:
        json.dump({"scenes": subtitles_to_write}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"Done: {len(subtitles_to_write)} subtitle files generated")
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
