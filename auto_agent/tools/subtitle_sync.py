"""
자막 동기화 래퍼

auto_kairos의 subtitle_sync.py에서 이관.
Whisper 타임스탬프 + 한국어 문법 규칙 기반 자막 분할.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from statistics import variance, mean

from .whisper import WhisperClient


# 한국어 조사 패턴 (분할 가능 지점)
JOSA_PATTERNS = [
    r'(?:[가-힣]+|[A-Za-z0-9]+)은\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)는\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)이\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)가\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)을\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)를\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)에서\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)에게\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)으로\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)로\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)와\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)과\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)의\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)도\s',
    r'(?:[가-힣]+|[A-Za-z0-9]+)만\s',
]

# 분할 금지 패턴 (수식어+명사, 서술어)
MODIFIER_PATTERNS = [
    r'[가-힣]+적\s[가-힣]+',
    r'[가-힣]+한\s[가-힣]+',
    r'[가-힣]+된\s[가-힣]+',
    r'[가-힣]+의\s[가-힣]+',
    r'[가-힣]+다는\s겁니다',
    r'[가-힣]+다는\s거죠',
    r'[가-힣]+다고\s합니다',
]

PREDICATE_PATTERNS = [
    r'[가-힣]+\s수\s(?:있|없)[가-힣]*',
    r'(?:못|안)\s[가-힣]+',
]

# 2순위: 연결어미 패턴 (절 경계)
CLAUSE_PATTERNS = [
    r'위해서는\s',
    r'기\s위해\s',
    r'지만\s',
    r'는데\s',
    r'면서\s',
    r'하고\s',
    r'하며\s',
]


@dataclass
class SubtitleEntry:
    """자막 항목"""
    index: int
    text: str
    start: float
    end: float

    def to_srt_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def to_srt(self) -> str:
        return f"{self.index}\n{self.to_srt_time(self.start)} --> {self.to_srt_time(self.end)}\n{self.text}\n"


@dataclass
class SubtitleResult:
    """자막 생성 결과"""
    scene_number: int
    original_text: str
    entries: List[SubtitleEntry]
    audio_duration: float
    word_count: int
    raw_words: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        result = {
            "scene_number": self.scene_number,
            "original_text": self.original_text,
            "audio_duration": self.audio_duration,
            "word_count": self.word_count,
            "entries": [
                {"index": e.index, "text": e.text, "start": e.start, "end": e.end}
                for e in self.entries
            ],
        }
        if self.raw_words:
            result["words"] = self.raw_words
        return result

    def to_srt(self) -> str:
        return "\n".join(e.to_srt() for e in self.entries)


class SubtitleSync:
    """자막 동기화 - 끊어읽기 기반 + 한국어 문법 규칙 분할"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        max_chars_per_line: int = 30,
        language: str = "ko",
        pause_threshold: float = 0.25,
        use_pause_detection: bool = True,
    ):
        self.whisper = WhisperClient(api_key=openai_api_key, language=language)
        self.max_chars = max_chars_per_line
        self.language = language
        self.pause_threshold = pause_threshold
        self.use_pause_detection = use_pause_detection

    def detect_natural_pauses(self, words: List[Dict]) -> List[Dict]:
        """단어 간 간격으로 끊어읽기 지점 감지"""
        if len(words) < 2:
            return []

        all_gaps = []
        gap_data = []
        for i in range(len(words) - 1):
            gap = words[i + 1].get("start", 0) - words[i].get("end", 0)
            if gap > 0:
                all_gaps.append(gap)
                gap_data.append((i, gap, words[i].get("end", 0)))

        if not all_gaps:
            return []

        avg_gap = mean(all_gaps)
        std_gap = (variance(all_gaps)) ** 0.5 if len(all_gaps) > 1 else 0
        k = max(0.5, self.pause_threshold * 4)
        threshold = max(avg_gap + (std_gap * k), 0.1)

        return [
            {"after_word_idx": idx, "gap": gap, "timestamp": ts}
            for idx, gap, ts in gap_data
            if gap >= threshold
        ]

    def _find_protected_ranges(self, text: str) -> List[Tuple[int, int]]:
        protected = []
        for pattern in PREDICATE_PATTERNS + MODIFIER_PATTERNS:
            for match in re.finditer(pattern, text):
                protected.append((match.start(), match.end()))
        if not protected:
            return []
        protected.sort()
        merged = [protected[0]]
        for start, end in protected[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def _is_protected(self, pos: int, ranges: List[Tuple[int, int]]) -> bool:
        return any(s < pos < e for s, e in ranges)

    def split_by_periods(self, text: str) -> List[str]:
        normalized = re.sub(r'\n+', ' ', text)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        sentences = []
        current = ""
        i = 0
        in_quote = False
        while i < len(normalized):
            char = normalized[i]
            current += char
            # 따옴표 상태 추적
            if char in '\u201C\u201E':      # 열린 꺾쇠 따옴표 (" „)
                in_quote = True
            elif char in '\u201D\u201F':    # 닫힌 꺾쇠 따옴표 (" ‟)
                in_quote = False
            elif char == '"':               # 직선 따옴표 토글
                in_quote = not in_quote
            if char in '.!?' and not in_quote:
                after = normalized[i + 1:] if i + 1 < len(normalized) else ""
                before = normalized[:i]
                should_break = False
                if char in '!?':
                    should_break = (after == "" or after[0].isspace())
                else:
                    if before and before[-1].isdigit() and after and after[0].isdigit():
                        should_break = False
                    elif after == "" or (after and after[0].isspace()):
                        should_break = True
                if should_break:
                    sentences.append(current.strip())
                    current = ""
                    if after and after[0] == ' ':
                        i += 1
            i += 1
        if current.strip():
            sentences.append(current.strip())
        return sentences

    def find_split_points(self, sentence: str) -> List[Tuple[int, int]]:
        points = []
        protected_ranges = self._find_protected_ranges(sentence)

        # 1순위: 명사 뒤 조사 (priority 1 = 최우선)
        for pattern in JOSA_PATTERNS:
            for match in re.finditer(pattern, sentence):
                end_pos = match.end() - 1
                if not self._is_protected(end_pos, protected_ranges):
                    points.append((end_pos, 1))

        # 2순위: 연결어미 (priority 2)
        for pattern in CLAUSE_PATTERNS:
            for match in re.finditer(pattern, sentence):
                end_pos = match.end() - 1
                points.append((end_pos, 2))

        # 3순위: 쉼표 (priority 3 = 최후순)
        for match in re.finditer(r',\s', sentence):
            points.append((match.end() - 1, 3))

        seen = set()
        unique = []
        for pos, priority in points:
            if pos not in seen:
                seen.add(pos)
                unique.append((pos, priority))
        return sorted(unique, key=lambda x: x[0])

    def split_long_sentence(self, sentence: str, cuts_needed: int) -> List[str]:
        if cuts_needed <= 0:
            return [sentence]
        split_points = self.find_split_points(sentence)
        if not split_points:
            return self._simple_split(sentence)

        total_len = len(sentence)
        targets = [total_len * i // (cuts_needed + 1) for i in range(1, cuts_needed + 1)]

        selected = []
        used = set()
        for target in targets:
            best = None
            best_score = float('inf')
            best_priority = float('inf')
            for pos, priority in split_points:
                if pos in used:
                    continue
                score = abs(pos - target)
                # 거리 우선, 같은 거리면 우선순위로 판단 (v1 방식)
                if score < best_score or (score == best_score and priority < best_priority):
                    best_score = score
                    best_priority = priority
                    best = pos
            if best is not None:
                selected.append(best)
                used.add(best)

        if not selected:
            return self._simple_split(sentence)

        selected.sort()
        parts = []
        start = 0
        for point in selected:
            parts.append(sentence[start:point].strip())
            start = point
            while start < len(sentence) and sentence[start] == ' ':
                start += 1
        if start < len(sentence):
            parts.append(sentence[start:].strip())
        return [p for p in parts if p]

    def _simple_split(self, text: str) -> List[str]:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            combined = (current + " " + word).strip() if current else word
            if len(combined) <= self.max_chars:
                current = combined
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _is_complete_quote(self, text: str) -> bool:
        """완전한 인용구인지 확인 (\u201C...\u201D 또는 "..."로 감싸짐)"""
        s = text.strip()
        return (
            (s.startswith('\u201C') and s.endswith('\u201D')) or
            (s.startswith('"') and s.endswith('"') and len(s) > 2)
        )

    def _fix_decimal_splits(self, lines: List[str]) -> List[str]:
        """소수점에서 잘린 줄을 병합한다.

        '125.' / '8%' 처럼 소수점에서 줄이 나뉜 경우,
        뒤 줄을 앞 줄에 붙여서 하나로 합친다.
        """
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

    def smart_split_text(self, text: str) -> List[str]:
        # 1. 줄바꿈으로 먼저 분할 (작가의 의도적 구분 = 따옴표/문단 경계)
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        final_lines = []
        for para in paragraphs:
            sentences = self.split_by_periods(para)
            for sentence in sentences:
                # 완전한 인용구는 따옴표 2자를 제외하고 길이 계산
                effective_len = len(sentence)
                if self._is_complete_quote(sentence):
                    effective_len = len(sentence) - 2
                ratio = effective_len / self.max_chars
                if ratio <= 1:
                    final_lines.append(sentence)
                else:
                    cuts = max(1, int(ratio))
                    parts = self.split_long_sentence(sentence, cuts)
                    # 재귀 분할: 조각이 여전히 max_chars 초과 시 추가 분할
                    resolved = []
                    for part in parts:
                        if len(part) > self.max_chars:
                            sub_parts = self.split_long_sentence(part, 1)
                            if len(sub_parts) > 1:
                                resolved.extend(sub_parts)
                            else:
                                resolved.extend(self._simple_split(part))
                        else:
                            resolved.append(part)
                    final_lines.extend(resolved)
        # 소수점 분리 후처리 (e.g. "125." + "8%" → "125.8%")
        final_lines = self._fix_decimal_splits(final_lines)
        return final_lines

    def match_to_timestamps(self, lines: List[str], words: List[Dict],
                            audio_duration: float = 0) -> List[SubtitleEntry]:
        if not lines:
            return []
        if not words:
            # 단어 정보 없으면 오디오 길이 기준 균등 분배
            total_chars = sum(len(l) for l in lines) or 1
            current = 0.0
            entries = []
            for i, line in enumerate(lines):
                dur = (len(line) / total_chars) * audio_duration
                entries.append(SubtitleEntry(index=i + 1, text=line, start=current, end=current + dur))
                current += dur
            return entries

        def normalize(t):
            return re.sub(r'[\u201C\u201D\u201E\u201F.,!?;:\'"()\[\]{}\u3000]', '', t.lower()).strip()

        def _edit_distance(a: str, b: str) -> int:
            """간단한 편집거리 (퍼지 매칭용)"""
            if len(a) > len(b):
                a, b = b, a
            dists = list(range(len(a) + 1))
            for j, cb in enumerate(b):
                new_dists = [j + 1]
                for i, ca in enumerate(a):
                    cost = 0 if ca == cb else 1
                    new_dists.append(min(new_dists[i] + 1, dists[i + 1] + 1, dists[i] + cost))
                dists = new_dists
            return dists[-1]

        def _fuzzy_match(target: str, candidate: str) -> bool:
            """부분문자열 매칭 + 편집거리 1 이하 허용"""
            nt, nc = normalize(target), normalize(candidate)
            if not nt or not nc:
                return False
            # 부분문자열 매칭
            if nt in nc or nc in nt:
                return True
            # 편집거리 허용 (짧은 쪽 기준 1글자 이하 차이)
            if _edit_distance(nt, nc) <= max(1, min(len(nt), len(nc)) // 4):
                return True
            return False

        def _find_word_forward(target: str, start_idx: int, max_search: int = 0) -> int:
            """start_idx부터 전진 탐색, 매칭 실패 시 -1 반환"""
            limit = len(words) if max_search <= 0 else min(len(words), start_idx + max_search)
            for j in range(start_idx, limit):
                if _fuzzy_match(target, words[j].get("word", "")):
                    return j
            return -1

        entries = []
        word_index = 0
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            line_words = normalize(line).split()
            if not line_words:
                continue

            # 시작 단어 찾기 — 현재 위치에서 가까운 범위 내에서 검색
            first_match = _find_word_forward(line_words[0], word_index, max_search=15)
            if first_match >= 0:
                word_index = first_match
            # 매칭 실패 시 word_index 유지 (이전 위치 기반 추정)

            start_time = words[word_index]["start"] if word_index < len(words) else 0

            # 마지막 단어 찾기 — 시작 위치 이후, 가까운 첫 매칭만 취함
            end_idx = word_index
            if len(line_words) > 1:
                last_match = _find_word_forward(line_words[-1], word_index, max_search=20)
                if last_match >= 0:
                    end_idx = last_match

            end_time = words[end_idx]["end"] if end_idx < len(words) else start_time
            word_index = end_idx + 1

            entries.append(SubtitleEntry(index=i + 1, text=line, start=start_time, end=end_time))

        if not entries:
            return entries

        # 연속성 보장 — 역전 방지
        for i in range(len(entries) - 1):
            next_start = entries[i + 1].start
            if next_start >= entries[i].start:
                entries[i].end = next_start
            # next_start < current.start → 역전 발생, 보간으로 대체
            else:
                entries[i].end = entries[i].start + (entries[i].end - entries[i].start)

        if audio_duration > 0 and entries[-1].end < audio_duration:
            entries[-1].end = audio_duration

        # 역전된 엔트리 보간 복구 (start=0 이면서 첫 엔트리가 아닌 경우)
        for i in range(1, len(entries)):
            if entries[i].start <= 0 and entries[i - 1].end > 0:
                entries[i].start = entries[i - 1].end
            if entries[i].end <= entries[i].start:
                # 남은 시간을 남은 엔트리에 균등 분배
                remaining = (audio_duration if audio_duration > 0 else entries[i - 1].end + 2.0) - entries[i].start
                remaining_entries = len(entries) - i
                per_entry = max(0.1, remaining / remaining_entries)
                for k in range(i, len(entries)):
                    entries[k].start = entries[i].start + (k - i) * per_entry
                    entries[k].end = entries[k].start + per_entry
                if audio_duration > 0:
                    entries[-1].end = audio_duration
                break

        return entries

    def generate_subtitles(self, original_text: str, audio_source: str = "",
                           scene_number: int = 1) -> SubtitleResult:
        """원본 텍스트 + TTS 오디오로 자막 생성"""
        whisper_result = self.whisper.analyze_audio(audio_source) if audio_source else {}
        audio_duration = whisper_result.get("duration", 0)
        whisper_words = whisper_result.get("words", [])

        subtitle_lines = self.smart_split_text(original_text)
        entries = self.match_to_timestamps(subtitle_lines, whisper_words, audio_duration)

        return SubtitleResult(
            scene_number=scene_number,
            original_text=original_text,
            entries=entries,
            audio_duration=audio_duration,
            word_count=len(whisper_words),
            raw_words=whisper_words,
        )

    def generate_batch(self, scenes: List[Dict], output_dir: Path) -> List[SubtitleResult]:
        """여러 씬 자막 일괄 생성"""
        results = []
        output_dir.mkdir(parents=True, exist_ok=True)

        for scene in scenes:
            try:
                audio_source = scene.get("audio_source") or scene.get("audio_url") or scene.get("audio_path", "")
                result = self.generate_subtitles(
                    original_text=scene.get("original_text", ""),
                    audio_source=audio_source,
                    scene_number=scene.get("scene_number", 1),
                )
                results.append(result)

                srt_path = output_dir / f"scene_{result.scene_number:03d}.srt"
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(result.to_srt())

                # 단어별 타임스탬프 사이드카 JSON 저장
                if result.raw_words:
                    words_path = output_dir / f"scene_{result.scene_number:03d}_words.json"
                    with open(words_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "scene_number": result.scene_number,
                            "audio_duration": result.audio_duration,
                            "words": result.raw_words,
                        }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  씬 {scene.get('scene_number')} 자막 실패: {e}")

        all_results = {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(results),
            "max_chars_per_line": self.max_chars,
            "scenes": [r.to_dict() for r in results],
        }
        json_path = output_dir / "subtitles.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        return results
