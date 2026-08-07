"""
Korean TTS Preprocessing Module
Handles number-to-text conversion, English abbreviation pronunciation,
punctuation normalization, and special character handling for Korean text.
"""

import re
import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ProcessingResult:
    """Result of processing a single scene."""
    scene_id: str
    original: str
    processed: str
    changes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class KoreanNumberConverter:
    """Converts Arabic numerals to Korean text with special rules."""

    # Korean number names - using 한글/Native Korean numbering system
    NATIVE_ONES = ['', '한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉']
    NATIVE_TENS = ['', '열', '스물', '서른', '마흔', '쉰', '예순', '일흔', '여든', '아흔']

    # Sino-Korean numbering system (for formal/modern use)
    SINO_ONES = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구']
    SINO_TENS = ['', '십', '이십', '삼십', '사십', '오십', '육십', '칠십', '팔십', '구십']
    SINO_HUNDREDS = ['', '백', '이백', '삼백', '사백', '오백', '육백', '칠백', '팔백', '구백']

    @staticmethod
    def number_to_korean(num: int, context: str = '', use_sino: bool = True) -> str:
        """
        Convert a number to Korean text.

        Uses Sino-Korean numbering (일, 이, 삼...) for years, units
        Uses Native Korean (한, 두, 세...) for counting

        Args:
            num: The number to convert
            context: The context (e.g., '만', '배', '센트') for special rules
            use_sino: Whether to use Sino-Korean (True) or Native (False)

        Returns:
            Korean text representation of the number
        """
        if num == 0:
            return '영' if use_sino else '영'

        if num < 0:
            return '마이너스 ' + KoreanNumberConverter.number_to_korean(-num, context, use_sino)

        # Use Sino-Korean for most contexts
        return KoreanNumberConverter._number_to_sino_korean(num)

    @staticmethod
    def _number_to_sino_korean(num: int) -> str:
        """Convert using Sino-Korean numbering system."""
        if num == 0:
            return '영'
        if num < 0:
            return '마이너스 ' + KoreanNumberConverter._number_to_sino_korean(-num)

        # Handle numbers up to 999,999,999
        if num < 10:
            return KoreanNumberConverter.SINO_ONES[num]
        elif num < 100:
            tens = num // 10
            ones = num % 10
            result = '십' if tens == 1 else KoreanNumberConverter.SINO_ONES[tens] + '십'
            if ones > 0:
                result += KoreanNumberConverter.SINO_ONES[ones]
            return result
        elif num < 1000:
            hundreds = num // 100
            remainder = num % 100
            result = '백' if hundreds == 1 else KoreanNumberConverter.SINO_ONES[hundreds] + '백'
            if remainder > 0:
                result += KoreanNumberConverter._number_to_sino_korean(remainder)
            return result
        elif num < 10000:
            thousands = num // 1000
            remainder = num % 1000
            result = '천' if thousands == 1 else KoreanNumberConverter.SINO_ONES[thousands] + '천'
            if remainder > 0:
                result += KoreanNumberConverter._number_to_sino_korean(remainder)
            return result
        else:
            # For larger numbers
            man = num // 10000
            remainder = num % 10000
            result = '만' if man == 1 else KoreanNumberConverter._number_to_sino_korean(man) + '만'
            if remainder > 0:
                result += KoreanNumberConverter._number_to_sino_korean(remainder)
            return result


class KoreanTTSPreprocessor:
    """Main preprocessor for Korean TTS text."""

    # Units and their Korean representations
    UNITS = {
        '년': '년', '월': '월', '일': '일',
        '시': '시', '분': '분', '초': '초',
        '갤런': '갤런', '온스': '온스',
        '센트': '센트', '달러': '달러', '파운드': '파운드',
        '배': '배', '만': '만',
        '퍼센트': '퍼센트', '%': '퍼센트',
        '세': '세',
    }

    # 영문 단위 → 한글 (TTS가 km, kg 등을 영문 그대로 읽지 못함)
    # 매칭 시 공백 허용, 단위 뒤 알파벳 금지(부분 매칭 방지)
    ENGLISH_UNIT_MAP = [
        # 길이/거리 (긴 것부터)
        ('km', '킬로미터'),
        ('cm', '센티미터'),
        ('mm', '밀리미터'),
        ('nm', '나노미터'),
        # 무게
        ('kg', '킬로그램'),
        ('mg', '밀리그램'),
        # 부피
        ('ml', '밀리리터'),
        # 단일 문자 단위 (마지막에)
        ('m',  '미터'),
        ('g',  '그램'),
        ('L',  '리터'),
        ('l',  '리터'),
    ]

    # 한글 카운터 단위 (한자어 수사로 읽음)
    # "13척" → "십삼척", "5채" → "오채"
    KOREAN_COUNTER_UNITS = ['척', '채', '권', '편', '쪽', '호', '회', '차', '층', '동', '호선',
                             '점', '발', '명', '인', '대', '병', '잔', '그릇', '마리',
                             '가마', '섬', '되', '말', '근', '필', '자', '푼', '냥']

    # English abbreviations → Korean pronunciation
    ENGLISH_ABBR = {
        # Finance/Investment
        'SPIVA': '스피바',
        'S&P': '에스앤피',
        'ETF': '이티에프',
        'IRP': '아이알피',
        'ISA': '아이에스에이',
        'VOO': '브이오오',
        'IVV': '아이브이브이',
        'SPY': '에스피와이',
        'TIGER': '타이거',
        'KODEX': '코덱스',
        'TR': '티알',
        'FOMO': '포모',
        'JPM': '제이피모건',
        'JPMorgan': '제이피모건',
        # Tech
        'AI': '에이아이',
        'API': '에이피아이',
        'GPU': '지피유',
        'CEO': '씨이오',
        'LLM': '엘엘엠',
        'GPT': '지피티',
        'IT': '아이티',
    }

    # English words that TTS often mispronounces
    ENGLISH_WORDS = {
        'Anthropic': '앤쓰로픽',
        'OpenAI': '오픈에이아이',
        'Perplexity': '퍼플렉시티',
        'Gemini': '제미나이',
        'Claude': '클로드',
    }

    def __init__(self):
        """Initialize the preprocessor."""
        self.changes: List[str] = []

    def _basic_cleanup(self, text: str) -> str:
        """legacy direct TTS 경로와 동일한 기본 정리 규칙."""
        original = text
        text = text.strip()
        text = re.sub(r'^#\d+\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^(장소|시간|배경|상황):\s*.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'\{[^}]*\}', '', text)
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF\U00002600-\U000026FF\U00002700-\U000027BF]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub('', text)
        text = re.sub(r"['\"][^'\"]+['\"]\.", lambda m: m.group(0)[1:-2] + ',', text)
        text = re.sub(r'[""""\'\'\'\'「」『』《》〈〉`´]', '', text)
        text = re.sub(r'[<>♪♫♬♭♮♯★☆♥♡※▶◀■□▲△▼▽○●◎◇◆]', '', text)
        text = re.sub(r'[!?]{2,}', lambda m: m.group(0)[0], text)
        text = re.sub(r'\.{3,}', '...', text)
        text = re.sub(r'^([^:]+):\s*', r'\1. ', text, flags=re.MULTILINE)
        text = re.sub(r'\s+', ' ', text).strip()
        if text != original:
            self.changes.append("기본 정리 적용")
        return text

    def _strip_markdown_markers(self, text: str) -> str:
        """마크다운 강조 마커(**볼드**, *이탤릭*, `code`, [[wiki]], [text](url))를 제거.
        원고에서 **볼드**는 영상 연출 힌트이므로 TTS/자막에서는 제거한다."""
        original = text
        # [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
        # [[wikilink]] → wikilink
        text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
        # `code` → code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # **볼드** → 볼드
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        # *이탤릭* → 이탤릭 (단, ** 처리 후 남은 단일 * 만)
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
        if text != original:
            self.changes.append("마크다운 강조 마커 제거")
        return text

    def _convert_english_units(self, text: str) -> str:
        """영문 단위(km, kg, %, m 등)를 한글로 변환.
        숫자가 앞에 있는 경우만 매치 — '5km' → '5킬로미터'.
        단위 뒤가 알파벳이면 매치 안 함 (부분 매칭 방지)."""
        for eng_unit, kor_unit in self.ENGLISH_UNIT_MAP:
            # 숫자(쉼표/소수점 포함) 직후 + 단위 + (뒤에 영문자 없음)
            pattern = re.compile(
                r'(\d[\d,]*(?:\.\d+)?)\s*' + re.escape(eng_unit) + r'(?![A-Za-z])'
            )
            def _repl(m, _eu=eng_unit, _ku=kor_unit):
                num_str = m.group(1).replace(',', '')
                # 숫자도 한자어로 변환 (소수점 지원)
                try:
                    if '.' in num_str:
                        int_part, dec_part = num_str.split('.')
                        korean_int = (
                            KoreanNumberConverter.number_to_korean(int(int_part))
                            if int_part != '0' else '영'
                        )
                        korean_dec = ''.join(
                            KoreanNumberConverter.SINO_ONES[int(d)] if int(d) > 0 else '영'
                            for d in dec_part
                        )
                        korean = f"{korean_int}쩜{korean_dec}"
                    else:
                        korean = KoreanNumberConverter.number_to_korean(int(num_str))
                except Exception:
                    korean = m.group(1)
                self.changes.append(f"{m.group(0)} → {korean}{_ku}")
                return f"{korean}{_ku}"
            text = pattern.sub(_repl, text)
        return text

    def _convert_counter_units(self, text: str) -> str:
        """한글 카운터 단위(척, 채, 권 등)에 붙은 숫자를 한자어 수사로 변환.
        예: '13척' → '십삼척', '133척' → '백삼십삼척'."""
        units_alt = '|'.join(re.escape(u) for u in self.KOREAN_COUNTER_UNITS)
        pattern = re.compile(r'(\d+)(' + units_alt + r')')
        def _repl(m):
            try:
                num = int(m.group(1))
                unit = m.group(2)
                korean = KoreanNumberConverter.number_to_korean(num)
                self.changes.append(f"{m.group(0)} → {korean}{unit}")
                return f"{korean}{unit}"
            except Exception:
                return m.group(0)
        return pattern.sub(_repl, text)

    def process_text(self, text: str) -> tuple[str, List[str]]:
        """
        Process a single text string.

        Args:
            text: The text to process

        Returns:
            Tuple of (processed_text, list_of_changes)
        """
        self.changes = []
        result = text

        # Step -1: legacy direct TTS 경로와 동일한 기본 정리
        result = self._basic_cleanup(result)

        # Step 0: 마크다운 강조 마커 제거 (TTS/자막에 포함되면 안 됨)
        result = self._strip_markdown_markers(result)

        # Process in order: English → punctuation → ranges → English units → numbers → counters → KR units → special cases
        result = self._convert_english(result)
        result = self._normalize_punctuation(result)
        result = self._convert_ranges(result)
        # 영문 단위(km/kg/%) → 한글 (숫자 변환 전에 수행 — 변환 후 단어 단위로 처리)
        result = self._convert_english_units(result)
        result = self._convert_numbers(result)
        # 한글 카운터(척/채/권/...)에 남은 숫자를 한자어로
        result = self._convert_counter_units(result)
        result = self._handle_units(result)
        result = self._prevent_palatalization(result)
        result = self._prevent_rendaku(result)
        result = self._handle_prices_and_measurements(result)
        result = self._apply_legacy_pronunciation_guards(result)

        return result, self.changes

    # Korean particles (조사) to separate from English/abbreviations
    KOREAN_PARTICLES = re.compile(
        r'(?<=[\uAC00-\uD7A3a-zA-Z0-9])(은|는|이|가|을|를|에서|에게|에|으로|로|와|과|의|도|만|까지|부터|보다|마저|조차|밖에|처럼|같이)(?=\s|[.,!?\"\']|$)'
    )

    def _convert_english(self, text: str) -> str:
        """Convert English abbreviations and words to Korean pronunciation."""
        # Handle S&P500+조사 first: "S&P500이" → "에스앤피오백 이"
        pattern_sp500_josa = r'S&P\s*500(은|는|이|가|을|를|에서|에게|에|으로|로|와|과|의|도|만|까지|부터)'
        match = re.search(pattern_sp500_josa, text)
        if match:
            josa = match.group(1)
            self.changes.append(f'S&P500{josa} → 에스앤피오백 {josa}')
            text = re.sub(pattern_sp500_josa, f'에스앤피오백 \\1', text)
        else:
            # Handle S&P500 without 조사
            pattern_sp500 = r'S&P\s*500'
            if re.search(pattern_sp500, text):
                self.changes.append('S&P500 → 에스앤피오백')
                text = re.sub(pattern_sp500, '에스앤피오백', text)

        # Handle abbreviations (longest first)
        for eng, kor in sorted(self.ENGLISH_ABBR.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(r'(?<![A-Za-z&])' + re.escape(eng) + r'(?![A-Za-z])')
            if pattern.search(text):
                self.changes.append(f'{eng} → {kor}')
                text = pattern.sub(kor, text)

        # Handle specific English words
        for eng, kor in self.ENGLISH_WORDS.items():
            if eng in text:
                self.changes.append(f'{eng} → {kor}')
                text = text.replace(eng, kor)

        return text

    def _normalize_punctuation(self, text: str) -> str:
        """Normalize punctuation for TTS."""
        # Em dash → comma with pause
        if '—' in text:
            self.changes.append('— → ,')
            text = text.replace('—', ',')
        # Ellipsis → period
        if '...' in text:
            self.changes.append('... → .')
            text = text.replace('...', '.')
        # Semicolon → comma
        if ';' in text:
            self.changes.append('; → ,')
            text = text.replace(';', ',')
        return text

    def _convert_ranges(self, text: str) -> str:
        """숫자 범위 표기 `~`를 `에서`로 정규화."""
        pattern = r'(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)'

        def replace_range(match):
            left = match.group(1)
            right = match.group(2)
            replaced = f'{left}에서{right}'
            self.changes.append(f'{match.group(0)} → {replaced}')
            return replaced

        return re.sub(pattern, replace_range, text)

    # ── 날짜 연음 규칙 (korean-tts-rules.md §4) ──
    # 연도: 1/6/7/8로 끝나면 "년" → "련"
    YEAR_LIAISON_DIGITS = {1, 6, 7, 8}

    # 월 특수 발음 (구어/낭독 표준)
    MONTH_LIAISON = {
        1: '이뤌', 2: '이월', 3: '삼월', 4: '사월', 5: '오월',
        6: '유월', 7: '칠뤌', 8: '파뤌', 9: '구월',
        10: '시월', 11: '시비뤌', 12: '시비월',
    }

    # 일 특수 발음 (1~31)
    # 21~31은 "이십-이릴" 같이 십의 자리 + 하이픈 + 일의 자리 발음 패턴
    DAY_LIAISON = {
        1: '이릴', 2: '이일', 3: '삼일', 4: '사일', 5: '오일',
        6: '유길', 7: '칠일', 8: '파릴', 9: '구일',
        10: '시빌', 11: '시비릴', 12: '시비일', 13: '십삼일', 14: '십사일',
        15: '시보일', 16: '십육일', 17: '십칠일', 18: '십팔일', 19: '십구일',
        20: '이십일',
        21: '이십-이릴', 22: '이십-이일', 23: '이십-삼일', 24: '이십-사일',
        25: '이십-오일', 26: '이십-유길', 27: '이십-칠일', 28: '이십-파릴',
        29: '이십-구일', 30: '삼십일',
        31: '삼십-이릴',
    }

    @classmethod
    def _hyphenate_year(cls, year: int) -> str:
        """연도를 음절 단위로 하이픈 분할 + 1/6/7/8 끝이면 '련' 발음.

        3자리(100~999) + 4자리(1000~9999) 지원.
        예:
            845  → 팔백-사십-오년
            1955 → 천-구백-오십-오년
            1956 → 천-구백-오십-륙련
            1597 → 천-오백-구십-칠련
            2024 → 이천-이십-사년
            2001 → 이천-일련
            1876 → 천-팔백-칠십-륙련
            1990 → 천-구백-구십년
        """
        if year < 100 or year > 9999:
            # 범위 밖은 fallback
            return KoreanNumberConverter.number_to_korean(year) + '년'

        thousands = year // 1000
        hundreds = (year % 1000) // 100
        tens = (year % 100) // 10
        ones = year % 10

        parts: list[str] = []
        # 천 (4자리만)
        if thousands > 0:
            parts.append('천' if thousands == 1 else KoreanNumberConverter.SINO_ONES[thousands] + '천')
        # 백
        if hundreds > 0:
            parts.append('백' if hundreds == 1 else KoreanNumberConverter.SINO_ONES[hundreds] + '백')
        # 십
        if tens > 0:
            parts.append('십' if tens == 1 else KoreanNumberConverter.SINO_ONES[tens] + '십')

        # 일의 자리 — 6은 "륙"으로 변환 (련 규칙과 함께)
        if ones > 0:
            ones_char = KoreanNumberConverter.SINO_ONES[ones]
            if ones == 6:
                ones_char = '륙'  # 천구백오십육 → 천-구백-오십-륙
            parts.append(ones_char + ('련' if ones in cls.YEAR_LIAISON_DIGITS else '년'))
        else:
            # 일의 자리가 0이면 십의 자리 끝에 년 붙임 (예: 1990 → 천-구백-구십년)
            parts[-1] = parts[-1] + '년'

        return '-'.join(parts)

    def _convert_numbers(self, text: str) -> str:
        """Convert all numeric formats to Korean text."""
        original = text

        # Pattern 1a: 쉼표 있는 연도 (예: 4,600년 전) — 쉼표 제거 후 처리
        pattern_year_comma = r'(\d{1,2}),(\d{3})년'
        def replace_year_comma(match):
            year = int(match.group(1) + match.group(2))
            if 100 <= year <= 9999:
                korean = self._hyphenate_year(year)
            else:
                korean = KoreanNumberConverter.number_to_korean(year) + '년'
            change = f"{match.group(0)} → {korean}"
            self.changes.append(change)
            return korean

        text = re.sub(pattern_year_comma, replace_year_comma, text)

        # Pattern 1b: Year format (예: 845년, 1955년) — 3~4 자리 연도 + 하이픈 + 연음
        pattern_year = r'(\d{3,4})년'
        def replace_year(match):
            year = int(match.group(1))
            korean = self._hyphenate_year(year)
            change = f"{match.group(0)} → {korean}"
            self.changes.append(change)
            return korean

        text = re.sub(pattern_year, replace_year, text)

        # Pattern 2: Date format (예: 5월 31일) — 월/일 특수 발음 적용
        pattern_date = r'(\d{1,2})월\s*(\d{1,2})일'
        def replace_date(match):
            month = int(match.group(1))
            day = int(match.group(2))
            korean_month = self.MONTH_LIAISON.get(month) or (
                KoreanNumberConverter.number_to_korean(month) + '월'
            )
            korean_day = self.DAY_LIAISON.get(day) or (
                KoreanNumberConverter.number_to_korean(day) + '일'
            )
            change = f"{match.group(0)} → {korean_month}-{korean_day}"
            self.changes.append(change)
            return f"{korean_month}-{korean_day}"

        text = re.sub(pattern_date, replace_date, text)

        # Pattern 2b: 단독 월 (날짜 패턴 안 잡힌 것)
        pattern_month_only = r'(\d{1,2})월(?!\s*\d)'
        def replace_month(match):
            month = int(match.group(1))
            korean_month = self.MONTH_LIAISON.get(month) or (
                KoreanNumberConverter.number_to_korean(month) + '월'
            )
            change = f"{match.group(0)} → {korean_month}"
            self.changes.append(change)
            return korean_month

        text = re.sub(pattern_month_only, replace_month, text)

        # Pattern 2c: 단독 일 (날짜 패턴 안 잡힌 것)
        pattern_day_only = r'(?<![\d-])(\d{1,2})일(?![\dㄱ-힣])'
        def replace_day(match):
            day = int(match.group(1))
            if day < 1 or day > 31:
                return match.group(0)
            korean_day = self.DAY_LIAISON.get(day) or (
                KoreanNumberConverter.number_to_korean(day) + '일'
            )
            change = f"{match.group(0)} → {korean_day}"
            self.changes.append(change)
            return korean_day

        text = re.sub(pattern_day_only, replace_day, text)

        # Pattern 3: Gallons, ounces (예: 7,968갤런)
        pattern_units = r'([\d,]+)([갤온센달파])'
        def replace_units(match):
            num_str = match.group(1).replace(',', '')
            try:
                num = int(num_str)
                unit = match.group(2)
                korean_num = KoreanNumberConverter.number_to_korean(num)
                change = f"{match.group(0)} → {korean_num}{unit}"
                self.changes.append(change)
                return korean_num + unit
            except:
                return match.group(0)

        text = re.sub(pattern_units, replace_units, text)

        # Pattern 4: Percentage (예: 68%, 125.8%, 0.5%)
        pattern_percent = r'(\d+(?:\.\d+)?)%'
        def replace_percent(match):
            num_str = match.group(1)
            if '.' in num_str:
                int_part, dec_part = num_str.split('.')
                korean_int = KoreanNumberConverter.number_to_korean(int(int_part)) if int_part != '0' else '영'
                korean_dec = ''.join(
                    KoreanNumberConverter.SINO_ONES[int(d)] if int(d) > 0 else '영'
                    for d in dec_part
                )
                korean = f"{korean_int}쩜{korean_dec}"
            else:
                korean = KoreanNumberConverter.number_to_korean(int(num_str))
            change = f"{match.group(0)} → {korean}퍼센트"
            self.changes.append(change)
            return korean + '퍼센트'

        text = re.sub(pattern_percent, replace_percent, text)

        # Pattern 5: Age format (예: 13세에서 24세)
        pattern_age = r'(\d+)세'
        def replace_age(match):
            num = int(match.group(1))
            korean = KoreanNumberConverter.number_to_korean(num)
            change = f"{match.group(0)} → {korean}세"
            self.changes.append(change)
            return korean + '세'

        text = re.sub(pattern_age, replace_age, text)

        # Pattern 6: Number + Korean unit (만/억/조/개/곳/명/배/원/위/단계 등)
        pattern_num_unit = r'([\d,]+(?:\.\d+)?)\s*(만|억|조|개|곳|명|배|원|위|단계|가지|번|달러|조 달러|억 달러|만 달러|만 원)'
        def replace_num_unit(match):
            num_str = match.group(1).replace(',', '')
            unit = match.group(2)
            try:
                if '.' in num_str:
                    int_part, dec_part = num_str.split('.')
                    korean_int = KoreanNumberConverter.number_to_korean(int(int_part)) if int_part != '0' else '영'
                    korean_dec = ''.join(
                        KoreanNumberConverter.SINO_ONES[int(d)] if int(d) > 0 else '영'
                        for d in dec_part
                    )
                    korean = f"{korean_int}쩜{korean_dec}"
                else:
                    num = int(num_str)
                    korean = KoreanNumberConverter.number_to_korean(num)
                change = f"{match.group(0)} → {korean}{unit}"
                self.changes.append(change)
                return korean + unit
            except:
                return match.group(0)

        text = re.sub(pattern_num_unit, replace_num_unit, text)

        # Pattern 7: N년 (any digit count, not already 4-digit year)
        pattern_n_year = r'(\d{1,3})년'
        def replace_n_year(match):
            num = int(match.group(1))
            korean = KoreanNumberConverter.number_to_korean(num)
            change = f"{match.group(0)} → {korean}년"
            self.changes.append(change)
            return korean + '년'

        text = re.sub(pattern_n_year, replace_n_year, text)

        return text

    def _handle_units(self, text: str) -> str:
        """Handle unit conversions (센트, 파운드, 갤런, 온스)."""
        # Pattern: number + unit (e.g., "5센트", "20센트")
        pattern = r'(\d+)\s*(센트|파운드|갤런|온스|달러)'

        def replace_unit(match):
            num_str = match.group(1)
            unit = match.group(2)

            try:
                num = int(num_str)
                korean_num = KoreanNumberConverter.number_to_korean(num)
                change = f"{match.group(0)} → {korean_num}{unit}"
                self.changes.append(change)
                return korean_num + unit
            except:
                return match.group(0)

        return re.sub(pattern, replace_unit, text)

    def _prevent_palatalization(self, text: str) -> str:
        """
        Prevent 된소리화 (palatalization - merger of consonants).
        Examples:
        - '삼배' → '삼 배' (not merged to 쌤배)
        - '사배' → '사 배' (not merged to 싸배)

        This is important for TTS to maintain proper pronunciation boundaries.
        """
        # Insert space before problematic suffixes to prevent sound merging
        palatalization_patterns = [
            # Before 배 (times/multiplier)
            (r'(?<=[삼])배', ' 배'),  # 삼배 → 삼 배
            (r'(?<=[사])배', ' 배'),  # 사배 → 사 배
            # Could add more patterns as needed
        ]

        for pattern, replacement in palatalization_patterns:
            if re.search(pattern, text):
                change = f"Prevented 된소리화: {pattern}"
                # Only log if not already logged
                if change not in self.changes:
                    self.changes.append(change)
                text = re.sub(pattern, replacement, text)

        return text

    def _prevent_rendaku(self, text: str) -> str:
        """
        Prevent 연음 (rendaku/연음).
        Rules:
        - '억원' → '어-권'
        - '한 모금' → '한 / 모금'
        """
        # Handle 억원 → 어-권
        pattern_rendaku = r'억원'
        if pattern_rendaku in text:
            change = "억원 → 어-권 (연음 차단)"
            self.changes.append(change)
            text = text.replace('억원', '어-권')

        # Handle specific rendaku cases
        rendaku_cases = [
            ('한 모금', '한 / 모금'),
            ('십 명', '십 / 명'),
        ]

        for original_form, processed_form in rendaku_cases:
            if original_form in text:
                change = f"{original_form} → {processed_form} (연음 차단)"
                self.changes.append(change)
                text = text.replace(original_form, processed_form)

        return text

    def _handle_prices_and_measurements(self, text: str) -> str:
        """
        Handle special price and measurement formats.
        Rules:
        - "파운드당 5센트" → "파운드당 오센트"
        - "6온스" → "육온스"
        """
        # 가격 단위 처리 (가 vs 조사 가 구분)
        # This is more complex and requires context analysis

        return text

    def _apply_legacy_pronunciation_guards(self, text: str) -> str:
        """legacy direct TTS 경로에서 쓰던 발음 가드 유지."""
        replacements = [
            ('장난감', '장난깜'),
            ('신기록', '신끼록'),
            ('최고지도자', '최-고-지도자'),
        ]
        for original, replaced in replacements:
            if original in text:
                self.changes.append(f'{original} → {replaced}')
                text = text.replace(original, replaced)

        # '삼천'이 '산천'으로 읽히는 것을 막는 분절 가드.
        # 뒤에 수사·단위·조사·문장부호가 올 때만 건다 — 그래야 고유명사가 깨지지 않는다.
        # 좁히지 않으면 '삼천리자전거'가 "'삼'천리자전거"가 된다.
        _NUM_TAIL = (
            r"(?=[일이사오육칠팔구십백천만억조]"          # 이어지는 수사
            r"|[원년월일개명인대번차속톤장권편척채호회층동점발병잔]"  # 단위·조수사
            r"|[가되말근필자푼냥섬]"                      # 옛 도량형 (가마·되·말·근·필…)
            r"|\s|$|[.,!?)\]\"'])"
        )
        guards = [
            (rf"(?<!')삼만{_NUM_TAIL}", "'삼'만"),
            (rf"(?<!')삼천{_NUM_TAIL}", "'삼'천"),
            (rf"(?<!')삼백{_NUM_TAIL}", "'삼'백"),
        ]
        for pattern, replaced in guards:
            if re.search(pattern, text):
                self.changes.append(f'{pattern} → {replaced}')
                text = re.sub(pattern, replaced, text)

        return text

    def process_scene(self, scene_id: str, original_text: str) -> ProcessingResult:
        """
        Process a complete scene.

        Args:
            scene_id: The scene identifier (e.g., "scene_001")
            original_text: The original script text

        Returns:
            ProcessingResult object
        """
        processed_text, changes = self.process_text(original_text)

        return ProcessingResult(
            scene_id=scene_id,
            original=original_text,
            processed=processed_text,
            changes=changes
        )

    def process_scenes_from_storyboard(self, storyboard_data: Dict[str, Any]) -> List[ProcessingResult]:
        """
        Process all scenes from a storyboard analysis JSON.

        Args:
            storyboard_data: The storyboard analysis dictionary

        Returns:
            List of ProcessingResult objects
        """
        results = []
        scenes = storyboard_data.get('scenes', [])

        for scene in scenes:
            scene_id = scene.get('scene_id', '')
            original_text = scene.get('original_script_text', '')

            if scene_id and original_text:
                result = self.process_scene(scene_id, original_text)
                results.append(result)

        return results


def preprocess_pepsi_storyboard(
    storyboard_path: str,
    limit: int = 10,
    output_json: bool = True
) -> List[Dict[str, Any]]:
    """
    Main function to preprocess Pepsi history storyboard scenes.

    Args:
        storyboard_path: Path to the storyboard_analysis.json file
        limit: Number of scenes to process (None for all)
        output_json: Whether to output as JSON-serializable format

    Returns:
        List of processing results as dictionaries
    """
    import json

    # Load storyboard data
    with open(storyboard_path, 'r', encoding='utf-8') as f:
        storyboard_data = json.load(f)

    # Create preprocessor
    preprocessor = KoreanTTSPreprocessor()

    # Process scenes
    results = preprocessor.process_scenes_from_storyboard(storyboard_data)

    # Limit results if specified
    if limit:
        results = results[:limit]

    # Convert to dictionaries if requested
    if output_json:
        return [result.to_dict() for result in results]

    return results


if __name__ == '__main__':
    import sys

    # Example usage
    if len(sys.argv) > 1:
        storyboard_path = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

        results = preprocess_pepsi_storyboard(storyboard_path, limit=limit)

        # Print as formatted JSON
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # Test with example data
        preprocessor = KoreanTTSPreprocessor()

        test_cases = [
            ("scene_001", "1893년, 미국 노스캐롤라이나주..."),
            ("scene_007", "첫 해에만 시럽 7,968갤런을 판매했으니"),
            ("scene_009", "파운드당 5센트 하던 설탕이 20센트를 넘겼어요"),
            ("scene_031", "흰 컵 두 개"),
            ("scene_046", "13세에서 24세... 68%"),
        ]

        results = []
        for scene_id, text in test_cases:
            result = preprocessor.process_scene(scene_id, text)
            results.append(result.to_dict())

        print(json.dumps(results, ensure_ascii=False, indent=2))
