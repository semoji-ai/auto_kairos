# 계획 2: 영어 내레이션·화면 텍스트·자막 → 영어 미리보기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코스트코(B209) 마스터를 영어로 번역하고, 세모지 보이스로 영어 TTS를 만들어 길이를 맞춘 뒤, 타임 워프·화면 텍스트 교체·영어 자막을 적용해 영어 내레이션이 얹힌 미리보기 영상(`render/en/B209_EN_preview.mp4`)을 만든다.

**Architecture:** 순수 로직(글자 예산·번역 프롬프트/응답 파싱·TTS 정렬 경계·자막 분할·마스터→파트 시간 역변환·미리보기 오디오 배치)은 `sg/` 모듈로 pytest TDD. 외부 호출(헤드리스 `claude -p` 번역, ElevenLabs TTS, whisper ASR, AE JSX, ffmpeg)은 얇은 CLI(`scripts/`)가 맡는다. 실행 순서: 번역 → TTS(+길이 벗어난 구간 재작성 루프) → 변환표 → 원본 aep에 텍스트 교체 → 타임 워프 → 영어 자막 → 파트 렌더 → 미리보기 조립.

**Tech Stack:** Python 3(numpy), pytest, `claude -p`(구독 CLI, 번역), ElevenLabs HTTP API(세모지 보이스 `W7FnAxJNpD5WGjrF5GLp`, 키는 `~/LocalProjects/auto_kairos/.env`의 `ELEVENLABS_API_KEY`), whisper-cli(ggml-small, 영어 ASR), After Effects 2026 ExtendScript, aerender, ffmpeg.

**Spec:** `docs/superpowers/specs/2026-10-19-semoji-global-localization-design.md` (개정 2) §5·§6·§7.4

## Global Constraints

- 작업 폴더 `~/Projects/semoji_global`(= `~/LocalProjects/semoji_global`). 브랜치 `plan2-english`에서 작업.
- 편 데이터 `episodes/B209/`. 산출물: `l10n/en.json`, `l10n/en_review.md`, `tts/en/<id>.mp3`·`<id>.align.json`·`durs.json`, `build/en/`, `render/en/`. 오디오·영상·build는 git 제외.
- NAS 원본 수정 금지. AE 입력은 `src/B209_main_ko.aep`, 결과는 `build/en/`에 save_as.
- 마스터 시간 = 컷 적용 후(유튜브 시간). nonverbal 구간은 번역·TTS 대상 아님(원래 길이 유지, 미리보기에서 원래 녹음 조각 사용).
- 세모지 보이스 ID `W7FnAxJNpD5WGjrF5GLp`, `language_code: "en"`, `/with-timestamps`, 출력 `mp3_44100_192`. 모델은 `profiles/en.json`의 `tts_model`(Task 4에서 v3/multilingual_v2 비교 후 확정).
- 길이 허용: TTS 길이 / 원래 구간 길이 = r, **0.75 ≤ r ≤ 1.35**면 통과(타임 워프가 흡수). 벗어나면 번역 재작성(최대 2회), 그래도 벗어나면 `review`로 보고하고 진행.
- 번역은 `claude -p`(헤드리스) — API 키 직접 호출 금지(구독 CLI만). 응답은 JSON만.
- JSX 규칙(계획 1과 동일): UTF-8 BOM, `in/out` 키 따옴표, `S()` 직렬화, `var SELF=$.fileName;`, try/catch 후 로그. 실행 `scripts/ae/run.sh`, 렌더 `scripts/ae/render.sh … 29.97 "H.264 - Match Render Settings - 15 Mbps"`.
- AE 작업 중 `caffeinate -d -u -t 21600 &`. 디스크 여유 10GB 미만이면 렌더 중단.
- 사용자 보고는 한글. 화면·자막의 영어는 미국식 표기.

## Review Focus

1. 번역 응답이 일부 id를 빠뜨리거나 JSON 밖에 설명을 붙이는 경우 — 빠진 id는 재요청, 파싱 실패는 조용히 넘어가면 안 됨(Task 2 테스트).
2. TTS 앞뒤 무음·호흡이 길어 실제 말보다 길게 잡히는 경우 — 정렬 정보로 말 경계를 잘라 길이를 재야 함(Task 3 테스트).
3. 영어 문장이 길어 자막 한 줄(42자)을 넘는 경우, 아주 짧은 단어 조각이 0.8초 미만 자막이 되는 경우 — 단어 경계에서 나누고 짧은 조각은 합침(Task 5 테스트).
4. 화면 문자열이 키프레임 소스텍스트를 가진 경우, 번역문이 원래 박스보다 넓은 경우 — 키마다 같은 원문이면 교체, 넓으면 글자 크기 축소(최소 70%) 후 경고(Task 6 AE 검증).
5. 컷·건너뛴 소스에 걸친 구간의 자막 시각 — 마스터→파트 역변환이 클립 경계를 지켜야 함(Task 1 테스트).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `profiles/en.json` | 언어 프로필(초당 글자 수, TTS 모델·설정, 자막 줄 길이, 폰트 매핑) |
| `glossary/en.json` | 시리즈 공통 용어집(고유명사·채널 문구) |
| `sg/budget.py` | 글자 예산, 길이 판정 |
| `sg/translate.py` | 번역 프롬프트 생성·응답 파싱·배치 실행(러너 주입) |
| `sg/tts.py` | ElevenLabs 호출, 정렬에서 말 경계 계산, 트림 |
| `sg/subs.py` | 정렬 기반 자막 큐 분할 |
| `sg/edl.py` (수정) | `master_to_part` 추가 |
| `sg/preview.py` | 미리보기 오디오 배치 계산 |
| `scripts/translate.py` | `l10n/en.json` + `en_review.md` |
| `scripts/tts.py` | 구간 TTS + 길이 판정 + 재작성 루프 + `durs.json` |
| `scripts/asr_check.py` | 영어 TTS 전사 대조 |
| `scripts/ae/patch_text.jsx` | 화면 문자열 교체(comp_id, layer 기준) |
| `scripts/ae/subtitles.jsx` | 파트별 `#자막` 컴프에 영어 자막 레이어 생성 |
| `scripts/subtitles.py` | 자막 큐 → JSX job + `render/en/en.srt` |
| `scripts/preview.py` | 파트 렌더 이어 붙이기 + 영어 내레이션 믹스 |
| `scripts/timewarp.py` (수정) | `--aep` 입력 지정 |
| `tests/test_budget.py` `test_translate.py` `test_tts.py` `test_subs.py` `test_preview.py`, `tests/test_edl.py`(추가) | 단위 테스트 |

---

### Task 1: 프로필·용어집 + 글자 예산 + 마스터→파트 역변환

**Files:**
- Create: `profiles/en.json`, `glossary/en.json`, `sg/budget.py`
- Modify: `sg/edl.py`
- Test: `tests/test_budget.py`, `tests/test_edl.py`

**Interfaces:**
- Produces: `sg.budget.char_budget(dur: float, cps: float) -> int`; `sg.budget.fit_status(orig: float, new: float, lo=0.75, hi=1.35) -> str` (`"ok"|"short"|"long"`); `sg.edl.master_to_part(edl, m: float) -> tuple[str, float] | None`(컷 안·아웃트로면 None).

- [ ] **Step 1: 실패하는 테스트**

`tests/test_budget.py`
```python
from sg.budget import char_budget, fit_status


def test_char_budget_rounds_down():
    assert char_budget(4.0, 14) == 56
    assert char_budget(0.5, 14) == 7


def test_fit_status_bounds_are_inclusive():
    assert fit_status(4.0, 3.0) == "ok"        # 0.75
    assert fit_status(4.0, 5.4) == "ok"        # 1.35
    assert fit_status(4.0, 2.9) == "short"
    assert fit_status(4.0, 5.5) == "long"
```

`tests/test_edl.py` 끝에 추가:
```python


from sg.edl import master_to_part


def test_master_to_part_inverts_part_to_master():
    e = edl()
    assert master_to_part(e, 5.0) == ("a", 5.0)
    assert master_to_part(e, 12.0) == ("b", 2.0)
    assert master_to_part(e, 15.0) == ("b", 7.0)     # pr 15 → 두 번째 b 클립(pr 14, src 6) → src 7
    assert master_to_part(e, 17.0) == ("b", 10.0)    # 컷(pr 16~17) 뒤: 마스터 17 = pr 18 → src 10
    assert master_to_part(e, 20.5) is None           # 마스터 20.5 = pr 21.5 → 아웃트로
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_budget.py tests/test_edl.py`
Expected: FAIL — `No module named 'sg.budget'`, `cannot import name 'master_to_part'`

- [ ] **Step 3: 구현**

`sg/budget.py`
```python
"""번역 길이 예산과 TTS 길이 판정."""
import math


def char_budget(dur, cps):
    return int(math.floor(dur * cps))


def fit_status(orig, new, lo=0.75, hi=1.35):
    r = new / orig
    if r < lo - 1e-9:
        return "short"
    if r > hi + 1e-9:
        return "long"
    return "ok"
```

`sg/edl.py` 끝에 추가
```python


def master_to_part(edl, m):
    """마스터 시각 → (파트 id, 파트 로컬 소스 시각). 아웃트로·범위 밖이면 None."""
    p = master_to_pr(edl, m)
    for c in edl["parts"]:
        if c["pr_in"] <= p < c["pr_in"] + c["dur"]:
            return c["id"], round(c["src_in"] + (p - c["pr_in"]), 6)
    return None
```

`profiles/en.json`
```json
{
  "lang": "en",
  "language_code": "en",
  "cps": 14.0,
  "fit": {"lo": 0.75, "hi": 1.35, "max_rewrites": 2},
  "tts_model": "eleven_v3",
  "tts_voice": "W7FnAxJNpD5WGjrF5GLp",
  "tts_settings": {"stability": 0.5, "similarity_boost": 0.9, "style": 0.6, "use_speaker_boost": true},
  "subs": {"max_chars": 42, "min_dur": 0.8, "gap": 0.04},
  "fonts": {"OTSBAggroM": "OTSBAggroM", "OTSBAggroL": "OTSBAggroL", "OTSBAggroB": "OTSBAggroB",
            "HakgyoansimAllimjangTTF-R": "OTSBAggroM", "GeekbleMalang2": "OTSBAggroB", "BMYEONSUNG": "OTSBAggroM"},
  "min_font_scale": 0.7
}
```

`glossary/en.json`
```json
{
  "코스트코": "Costco", "이마트": "E-Mart", "홈플러스": "Homeplus", "롯데마트": "Lotte Mart",
  "월마트": "Walmart", "K마트": "Kmart", "까르푸": "Carrefour", "페드마트": "FedMart", "프라이스클럽": "Price Club",
  "짐 시네갈": "Jim Sinegal", "솔 프라이스": "Sol Price", "샘 월튼": "Sam Walton", "후고 만": "Hugo Mann",
  "커클랜드": "Kirkland Signature", "양재점": "Yangjae store", "세상의 모든 지식": "All Knowledge",
  "출처": "Source", "챕터": "Chapter", "억": "hundred million (KRW) — convert to USD when natural", "조": "trillion (KRW)"
}
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q`
Expected: 모두 통과(기존 50 + 3 = 53)

- [ ] **Step 5: 커밋**
```bash
git add profiles/en.json glossary/en.json sg/budget.py sg/edl.py tests/test_budget.py tests/test_edl.py
git commit -m "feat: 영어 프로필·용어집, 글자 예산, 마스터→파트 역변환"
```

---

### Task 2: 번역 모듈 + `scripts/translate.py`

**Files:**
- Create: `sg/translate.py`, `scripts/translate.py`
- Test: `tests/test_translate.py`

**Interfaces:**
- Consumes: `char_budget` (Task 1)
- Produces:
  - `sg.translate.build_prompt(items: list[dict], glossary: dict, lang: str, kind: str) -> str` — items 원소 `{"id","ko","budget","prev","next"}`(kind="segments") 또는 `{"id","ko","max_chars"}`(kind="strings")
  - `sg.translate.parse_response(text: str, ids: list[str]) -> dict[str,str]` — 코드펜스·앞뒤 설명을 벗기고 첫 JSON 객체를 파싱. 빠진 id가 있으면 `MissingIds(missing: list)` 예외(ValueError 하위).
  - `sg.translate.translate_batch(items, glossary, lang, kind, runner, retries=2) -> dict` — runner(prompt)->str. 빠진 id만 재요청.
  - `sg.translate.claude_runner(prompt) -> str` — `claude -p --output-format text` 호출.
  - CLI `python3 scripts/translate.py episodes/B209 en [--only n001,n002] [--rewrite durs_report.json]` → `l10n/en.json`, `l10n/en_review.md`

- [ ] **Step 1: 실패하는 테스트**

`tests/test_translate.py`
```python
import pytest
from sg.translate import build_prompt, parse_response, translate_batch, MissingIds

ITEMS = [{"id": "n001", "ko": "코스트코는 회원제 창고형 할인마트입니다.", "budget": 50, "prev": "", "next": "다음 문장"},
         {"id": "n002", "ko": "다음 문장", "budget": 20, "prev": "코스트코는…", "next": ""}]


def test_prompt_carries_budget_glossary_and_neighbors():
    p = build_prompt(ITEMS, {"코스트코": "Costco"}, "en", "segments")
    assert "n001" in p and "50" in p and "Costco" in p and "다음 문장" in p
    assert "JSON" in p


def test_parse_strips_fences_and_prose():
    txt = 'Here you go:\n```json\n{"n001": "Costco is a membership warehouse club.", "n002": "Next."}\n```\nDone.'
    assert parse_response(txt, ["n001", "n002"]) == {"n001": "Costco is a membership warehouse club.", "n002": "Next."}


def test_parse_reports_missing_ids():
    with pytest.raises(MissingIds) as e:
        parse_response('{"n001": "x"}', ["n001", "n002"])
    assert e.value.missing == ["n002"]


def test_batch_rerequests_only_missing_ids():
    calls = []

    def runner(prompt):
        calls.append(prompt)
        return '{"n001": "A"}' if len(calls) == 1 else '{"n002": "B"}'

    out = translate_batch(ITEMS, {}, "en", "segments", runner)
    assert out == {"n001": "A", "n002": "B"}
    assert "n002" in calls[1] and "n001" not in calls[1].split("ITEMS")[-1]


def test_batch_gives_up_after_retries():
    with pytest.raises(MissingIds):
        translate_batch(ITEMS, {}, "en", "segments", lambda p: '{"n001": "A"}', retries=1)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_translate.py`
Expected: FAIL — `No module named 'sg.translate'`

- [ ] **Step 3: 구현**

`sg/translate.py`
```python
"""헤드리스 claude로 현지화 번역. 프롬프트·응답 파싱은 순수 함수."""
import json
import re
import subprocess

LANG_NAMES = {"en": "English (US)", "ja": "Japanese", "zh": "Simplified Chinese"}


class MissingIds(ValueError):
    def __init__(self, missing):
        super().__init__(f"missing ids: {missing}")
        self.missing = missing


def build_prompt(items, glossary, lang, kind):
    target = LANG_NAMES.get(lang, lang)
    gl = "\n".join(f"- {k} → {v}" for k, v in glossary.items())
    if kind == "segments":
        rules = (f"You localize Korean YouTube documentary narration (channel: brand history explainers) into {target}.\n"
                 "Keep the meaning, order and tone (friendly, curious, explanatory). Add only the minimal context a global viewer needs "
                 "(e.g. explain a Korean institution in a few words). Convert Korean-specific expressions naturally.\n"
                 "Each item has a character budget for the spoken line (spaces included). Stay within ±15% of the budget.\n"
                 "Each item is spoken separately, so it must read naturally on its own while flowing from 'prev' to 'next'.\n")
    else:
        rules = (f"You localize short on-screen texts (titles, labels, captions, source credits) of a Korean video into {target}.\n"
                 "Keep them short and punchy. Never exceed max_chars. Keep numbers, years and brand names. 'Source: ...' for 출처.\n")
    body = json.dumps(items, ensure_ascii=False, indent=0)
    return (rules + f"Glossary (use exactly):\n{gl}\n\n"
            "Return ONLY a JSON object mapping each id to its translation. No commentary, no code fences.\n\nITEMS\n" + body)


def parse_response(text, ids):
    t = re.sub(r"```(?:json)?", "", text)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    obj = json.loads(t[i:j + 1])
    out = {k: str(obj[k]).strip() for k in ids if k in obj and str(obj[k]).strip()}
    missing = [k for k in ids if k not in out]
    if missing:
        e = MissingIds(missing)
        e.partial = out
        raise e
    return out


def translate_batch(items, glossary, lang, kind, runner, retries=2):
    todo, done = list(items), {}
    for attempt in range(retries + 1):
        ids = [x["id"] for x in todo]
        try:
            done.update(parse_response(runner(build_prompt(todo, glossary, lang, kind)), ids))
            return done
        except MissingIds as e:
            done.update(getattr(e, "partial", {}))
            todo = [x for x in todo if x["id"] in e.missing]
            if attempt == retries:
                raise MissingIds(e.missing)
    return done


def claude_runner(prompt):
    r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return r.stdout
```

`scripts/translate.py`
```python
"""번역.  usage: translate.py <EP> <lang> [--only id,id] [--rewrite rewrite.json]
rewrite.json: {id: {"target_chars": int, "why": "long|short"}} — 해당 구간만 길이를 맞춰 다시 번역."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.budget import char_budget
from sg.translate import translate_batch, claude_runner

ep, lang = sys.argv[1], sys.argv[2]
a = sys.argv[3:]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
gloss = json.load(open(os.path.join(root, "glossary", f"{lang}.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
out_p = os.path.join(ep, "l10n", f"{lang}.json")
os.makedirs(os.path.dirname(out_p), exist_ok=True)
L = json.load(open(out_p)) if os.path.exists(out_p) else {"lang": lang, "segments": {}, "strings": {}}

segs = [g for g in src["segments"] if not g.get("nonverbal")]
only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
rew = json.load(open(a[a.index("--rewrite") + 1])) if "--rewrite" in a else None

items = []
for i, g in enumerate(segs):
    if only and g["id"] not in only:
        continue
    if rew is not None and g["id"] not in rew:
        continue
    if rew is None and not only and g["id"] in L["segments"]:
        continue
    budget = rew[g["id"]]["target_chars"] if rew else char_budget(g["out"] - g["in"], prof["cps"])
    it = {"id": g["id"], "ko": g["ko"], "budget": budget,
          "prev": segs[i - 1]["ko"] if i else "", "next": segs[i + 1]["ko"] if i + 1 < len(segs) else ""}
    if rew:
        it["previous_translation"] = L["segments"][g["id"]]["text"]
        it["note"] = f"previous translation was too {rew[g['id']]['why']} when spoken; rewrite to about {budget} characters"
    items.append(it)
for k in range(0, len(items), 25):
    res = translate_batch(items[k:k + 25], gloss, lang, "segments", claude_runner)
    for i, t in res.items():
        L["segments"].setdefault(i, {})["text"] = t
    json.dump(L, open(out_p, "w"), ensure_ascii=False, indent=1)
    print(f"segments {min(k + 25, len(items))}/{len(items)}", flush=True)

if rew is None and not only:
    sitems = [{"id": s["id"], "ko": s["ko"].replace("\r", " / "), "max_chars": max(8, int(len(s["ko"]) * 2.2))}
              for s in src["strings"] if s["id"] not in L["strings"]]
    for k in range(0, len(sitems), 40):
        res = translate_batch(sitems[k:k + 40], gloss, lang, "strings", claude_runner)
        for i, t in res.items():
            L["strings"][i] = {"text": t.replace(" / ", "\r")}
        json.dump(L, open(out_p, "w"), ensure_ascii=False, indent=1)

with open(os.path.join(ep, "l10n", f"{lang}_review.md"), "w") as f:
    f.write(f"# {lang} 번역 대조표\n\n| id | 길이(초) | 예산 | 한국어 | 번역 |\n|---|---|---|---|---|\n")
    for g in segs:
        t = L["segments"].get(g["id"], {}).get("text", "")
        f.write(f"| {g['id']} | {g['out'] - g['in']:.1f} | {char_budget(g['out'] - g['in'], prof['cps'])} | {g['ko']} | {t} |\n")
    f.write("\n## 화면 문자열\n\n| id | 한국어 | 번역 |\n|---|---|---|\n")
    for s in src["strings"]:
        f.write(f"| {s['id']} | {s['ko'].replace(chr(13), ' / ')} | {L['strings'].get(s['id'], {}).get('text', '').replace(chr(13), ' / ')} |\n")
print("done", len(L["segments"]), "segments", len(L["strings"]), "strings")
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_translate.py`
Expected: `5 passed`

- [ ] **Step 5: B209 실제 번역**

Run: `python3 scripts/translate.py episodes/B209 en`
Expected: `done 172 segments 42 strings`(구간 수 = 177 - nonverbal 5). `l10n/en_review.md`를 열어 무작위 10줄을 읽고, 고유명사가 용어집대로인지, 한국 맥락(식약처 등) 보충이 짧은지 확인한다. 어색한 줄은 `--only id`로 재번역.

- [ ] **Step 6: 커밋**
```bash
git add sg/translate.py scripts/translate.py tests/test_translate.py
git add -f episodes/B209/l10n/en.json episodes/B209/l10n/en_review.md
git commit -m "feat: 헤드리스 claude 번역 — B209 영어 번역본"
```

---

### Task 3: TTS 모듈(정렬 기반 말 경계) + `scripts/tts.py`

**Files:**
- Create: `sg/tts.py`, `scripts/tts.py`
- Test: `tests/test_tts.py`

**Interfaces:**
- Consumes: `fit_status` (Task 1), `l10n/en.json` (Task 2)
- Produces:
  - `sg.tts.speech_bounds(alignment: dict) -> tuple[float,float]` — `characters`, `character_start_times_seconds`, `character_end_times_seconds`에서 공백·문장부호가 아닌 첫 글자 시작과 마지막 글자 끝.
  - `sg.tts.synthesize(text, voice, model, lang_code, settings, key) -> tuple[bytes, dict]`
  - `sg.tts.trim(mp3_in, mp3_out, t0, t1, pad=0.03)`
  - CLI `python3 scripts/tts.py episodes/B209 en [--only id,…] [--model eleven_v3] [--out-dir tts/en]` → 구간당 `tts/en/<id>.mp3`(트림본), `<id>.align.json`(트림 기준으로 시각 이동), `tts/en/durs.json`({id: 초}), `tts/en/fit.json`({id: {"orig","new","status"}})
  - CLI 옵션 `--rewrite-loop`: fit이 short/long인 구간을 `translate.py --rewrite`로 재작성 후 그 구간만 다시 TTS, 최대 `profiles.fit.max_rewrites`회.

- [ ] **Step 1: 실패하는 테스트**

`tests/test_tts.py`
```python
from sg.tts import speech_bounds


def test_bounds_skip_leading_and_trailing_space_and_punct():
    al = {"characters": [" ", "H", "i", ".", " "],
          "character_start_times_seconds": [0.0, 0.30, 0.42, 0.55, 0.60],
          "character_end_times_seconds": [0.30, 0.42, 0.55, 0.60, 1.40]}
    assert speech_bounds(al) == (0.30, 0.55)


def test_bounds_on_plain_text():
    al = {"characters": list("ok"), "character_start_times_seconds": [0.1, 0.2],
          "character_end_times_seconds": [0.2, 0.35]}
    assert speech_bounds(al) == (0.1, 0.35)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_tts.py`
Expected: FAIL — `No module named 'sg.tts'`

- [ ] **Step 3: 구현**

`sg/tts.py`
```python
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
```

`scripts/tts.py`
```python
"""구간 TTS.  usage: tts.py <EP> <lang> [--only id,…] [--model m] [--out-dir tts/<lang>] [--rewrite-loop]"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.budget import fit_status, char_budget
from sg.tts import speech_bounds, synthesize, trim, load_key

ep, lang = sys.argv[1], sys.argv[2]
a = sys.argv[3:]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
model = a[a.index("--model") + 1] if "--model" in a else prof["tts_model"]
out_dir = os.path.join(ep, a[a.index("--out-dir") + 1] if "--out-dir" in a else f"tts/{lang}")
os.makedirs(out_dir, exist_ok=True)
key = load_key(os.path.expanduser("~/LocalProjects/auto_kairos/.env"))
src = {g["id"]: g for g in json.load(open(os.path.join(ep, "master/source.json")))["segments"]}
lp = os.path.join(ep, "l10n", f"{lang}.json")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def run(ids):
    L = json.load(open(lp))
    fit = json.load(open(os.path.join(out_dir, "fit.json"))) if os.path.exists(os.path.join(out_dir, "fit.json")) else {}
    for i in ids:
        text = L["segments"][i].get("tts") or L["segments"][i]["text"]
        audio, al = synthesize(text, prof["tts_voice"], model, prof["language_code"], prof["tts_settings"], key)
        raw = os.path.join(out_dir, f"{i}.raw.mp3")
        open(raw, "wb").write(audio)
        t0, t1 = speech_bounds(al) if al else (0.0, dur(raw))
        start = trim(raw, os.path.join(out_dir, f"{i}.mp3"), t0, t1)
        os.remove(raw)
        if al:
            al = {"characters": al["characters"],
                  "character_start_times_seconds": [x - start for x in al["character_start_times_seconds"]],
                  "character_end_times_seconds": [x - start for x in al["character_end_times_seconds"]]}
        json.dump(al, open(os.path.join(out_dir, f"{i}.align.json"), "w"), ensure_ascii=False)
        g = src[i]
        d = dur(os.path.join(out_dir, f"{i}.mp3"))
        fit[i] = {"orig": round(g["out"] - g["in"], 3), "new": round(d, 3),
                  "status": fit_status(g["out"] - g["in"], d, prof["fit"]["lo"], prof["fit"]["hi"])}
        print(i, fit[i], flush=True)
        json.dump(fit, open(os.path.join(out_dir, "fit.json"), "w"), indent=1)
    json.dump({k: v["new"] for k, v in fit.items()}, open(os.path.join(out_dir, "durs.json"), "w"), indent=1)
    return fit


L0 = json.load(open(lp))
ids = a[a.index("--only") + 1].split(",") if "--only" in a else [i for i in L0["segments"] if not src[i].get("nonverbal")]
fit = run(ids)
if "--rewrite-loop" in a:
    for rnd in range(prof["fit"]["max_rewrites"]):
        bad = {k: v for k, v in fit.items() if v["status"] != "ok"}
        if not bad:
            break
        rew = {}
        for k, v in bad.items():
            cur = len(json.load(open(lp))["segments"][k]["text"])
            target = int(cur * (v["orig"] * 1.0) / v["new"])    # 원래 길이에 맞추는 글자 수
            rew[k] = {"target_chars": max(4, target), "why": "long" if v["status"] == "long" else "short"}
        rp = os.path.join(out_dir, f"rewrite_{rnd + 1}.json")
        json.dump(rew, open(rp, "w"), indent=1)
        subprocess.run([sys.executable, os.path.join(root, "scripts/translate.py"), ep, lang, "--rewrite", rp], check=True)
        fit = run(list(bad))
    bad = [k for k, v in fit.items() if v["status"] != "ok"]
    print("still out of range:", bad)
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q tests/test_tts.py`
Expected: `2 passed`

- [ ] **Step 5: 커밋**
```bash
git add sg/tts.py scripts/tts.py tests/test_tts.py
git commit -m "feat: 세모지 보이스 구간 TTS(정렬 트림·길이 판정·재작성 루프)"
```

---

### Task 4: TTS 모델 확정 + 전체 TTS + ASR 대조

**Files:**
- Create: `scripts/asr_check.py`
- Modify: `profiles/en.json`(모델 확정, cps 보정)

- [ ] **Step 1: 모델 비교 샘플**

```bash
cd ~/Projects/semoji_global
python3 scripts/tts.py episodes/B209 en --only n001,n006,n020,n050 --model eleven_v3 --out-dir tts/cmp_v3
python3 scripts/tts.py episodes/B209 en --only n001,n006,n020,n050 --model eleven_multilingual_v2 --out-dir tts/cmp_v2
for m in v3 v2; do ffmpeg -v error -y -i "concat:$(ls episodes/B209/tts/cmp_$m/n0*.mp3 | tr '\n' '|' | sed 's/|$//')" -c copy episodes/B209/tts/cmp_$m.mp3; done
```
Expected: 각 4개 mp3 생성. 두 파일(`tts/cmp_v3.mp3`, `tts/cmp_v2.mp3`)을 사용자에게 들려주고(파일 경로 전달) 어느 쪽이 세모지 보이스 느낌에 가까운지 선택받는다. 선택 결과를 `profiles/en.json`의 `tts_model`에 기록한다.

- [ ] **Step 2: 초당 글자 수 보정**

```bash
python3 -c "
import json,glob,os
L=json.load(open('episodes/B209/l10n/en.json'))
f=json.load(open('episodes/B209/tts/cmp_<선택>/fit.json'))
print(sum(len(L['segments'][k]['text']) for k in f)/sum(v['new'] for v in f.values()))"
```
Expected: 영어 세모지 보이스 초당 글자 수(대략 12~17). `profiles/en.json`의 `cps`를 이 값(소수 1자리)으로 고친다. 값이 기존 14와 15% 이상 다르면 `python3 scripts/translate.py episodes/B209 en` 결과를 지우고(`l10n/en.json` 삭제) 새 예산으로 다시 번역한다.

- [ ] **Step 3: 전체 TTS + 재작성 루프**

Run: `python3 scripts/tts.py episodes/B209 en --rewrite-loop`
Expected: 172구간 생성, 마지막 줄 `still out of range: [...]`가 비었거나 10개 이하. 남은 구간은 `en_review.md` 하단에 메모.

- [ ] **Step 4: `scripts/asr_check.py` 작성·실행**

```python
"""영어 TTS 전사 대조.  usage: asr_check.py <EP> <lang>  → tts/<lang>/asr.json, 유사도 0.85 미만 목록"""
import difflib, json, os, re, subprocess, sys, tempfile
ep, lang = sys.argv[1], sys.argv[2]
M = os.path.expanduser("~/LocalProjects/auto_kairos/artifacts/benchmarks/lg_ep01_tts_audit_20260916/ggml-small.bin")
L = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
d = os.path.join(ep, "tts", lang)
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).split()
res, bad = {}, []
for i, v in sorted(L["segments"].items()):
    mp3 = os.path.join(d, f"{i}.mp3")
    if not os.path.exists(mp3):
        continue
    with tempfile.NamedTemporaryFile(suffix=".wav") as w:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "16000", w.name], check=True)
        heard = subprocess.run(["whisper-cli", "-m", M, "-l", lang, "-nt", "-f", w.name], capture_output=True, text=True).stdout.strip()
    sim = difflib.SequenceMatcher(None, norm(v.get("tts") or v["text"]), norm(heard)).ratio()
    res[i] = {"sim": round(sim, 3), "heard": heard}
    if sim < 0.85:
        bad.append(i)
json.dump(res, open(os.path.join(d, "asr.json"), "w"), ensure_ascii=False, indent=1)
print("checked", len(res), "low", len(bad), bad)
```
Run: `python3 scripts/asr_check.py episodes/B209 en`
Expected: `low` 목록이 0~10개. 각 low 구간은 `asr.json`의 heard와 원문을 비교해, 발음 문제(숫자·약어·브랜드)면 `l10n/en.json`의 해당 구간에 `"tts": "<발음용 표기>"`를 넣고 `python3 scripts/tts.py episodes/B209 en --only <id>`로 재생성, whisper 오인식이면 그대로 둔다.

- [ ] **Step 5: 커밋**
```bash
git add scripts/asr_check.py profiles/en.json
git add -f episodes/B209/l10n/en.json episodes/B209/l10n/en_review.md episodes/B209/tts/en/fit.json episodes/B209/tts/en/durs.json episodes/B209/tts/en/asr.json
git commit -m "feat: B209 영어 TTS 전체 생성·길이 맞춤·ASR 대조"
```

---

### Task 5: 자막 큐 분할 (`sg/subs.py`) + 미리보기 오디오 배치 (`sg/preview.py`)

**Files:**
- Create: `sg/subs.py`, `sg/preview.py`
- Test: `tests/test_subs.py`, `tests/test_preview.py`

**Interfaces:**
- Consumes: `PiecewiseMap`, `master_to_part`, `edl`
- Produces:
  - `sg.subs.split_cues(chars: list[str], starts: list[float], ends: list[float], max_chars=42, min_dur=0.8) -> list[dict]` — `{"t0","t1","text"}`(구간 오디오 기준 초). 단어 경계에서만 자르고, 문장부호(. , ? ! ;) 뒤를 우선, 한 큐 ≤ max_chars, min_dur 미만 큐는 앞 큐에 합침(합쳐서 max_chars를 넘으면 뒤 큐에 합침).
  - `sg.preview.plan_audio(segments: list[dict], warp: PiecewiseMap, tts_dir: str) -> list[dict]` — 말 구간: `{"file": "<tts_dir>/<id>.mp3", "t": warp(seg.in)}`, nonverbal: `{"src_in": seg.in, "src_out": seg.out, "t": warp(seg.in), "kind": "nonverbal"}`.

- [ ] **Step 1: 실패하는 테스트**

`tests/test_subs.py`
```python
from sg.subs import split_cues


def even(text, cps=15.0):
    ch = list(text)
    st = [i / cps for i in range(len(ch))]
    en = [(i + 1) / cps for i in range(len(ch))]
    return ch, st, en


def test_short_line_is_one_cue():
    cues = split_cues(*even("Costco opened in Korea in 1998."))
    assert len(cues) == 1 and cues[0]["text"] == "Costco opened in Korea in 1998."


def test_long_line_splits_at_word_boundaries_within_max_chars():
    t = ("Costco has sold its hot dog combo for one dollar and fifty cents for forty years, "
         "and it still makes money thanks to its membership model.")
    cues = split_cues(*even(t))
    assert all(len(c["text"]) <= 42 for c in cues)
    assert " ".join(c["text"] for c in cues) == t
    assert cues[0]["text"].endswith(",") or len(cues[0]["text"]) > 30   # 쉼표 뒤 우선 분할
    assert all(c["t1"] > c["t0"] for c in cues)


def test_tiny_tail_cue_is_merged():
    cues = split_cues(*even("This line is exactly long enough to split here. Yes."), max_chars=48)
    assert all(c["t1"] - c["t0"] >= 0.8 for c in cues)
```

`tests/test_preview.py`
```python
from sg.preview import plan_audio
from sg.timemap import PiecewiseMap


def test_plan_places_tts_and_nonverbal_at_warped_starts():
    segs = [{"id": "n001", "in": 1.0, "out": 3.0}, {"id": "n002", "in": 4.0, "out": 4.5, "nonverbal": True},
            {"id": "n003", "in": 5.0, "out": 7.0}]
    w = PiecewiseMap([(0, 0), (3, 4), (20, 21)])
    p = plan_audio(segs, w, "/t")
    assert p[0] == {"file": "/t/n001.mp3", "t": w(1.0), "id": "n001"}
    assert p[1]["kind"] == "nonverbal" and p[1]["src_in"] == 4.0 and p[1]["t"] == w(4.0)
    assert p[2]["t"] == w(5.0)
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest -q tests/test_subs.py tests/test_preview.py`
Expected: FAIL — `No module named 'sg.subs'`

- [ ] **Step 3: 구현**

`sg/subs.py`
```python
"""정렬(글자 시각) 기반 자막 큐 분할."""
_PUNCT = ".,?!;:"


def _words(chars):
    """(시작 글자 idx, 끝 글자 idx(포함), 단어 문자열) 목록."""
    out, i, n = [], 0, len(chars)
    while i < n:
        while i < n and chars[i].isspace():
            i += 1
        j = i
        while j < n and not chars[j].isspace():
            j += 1
        if j > i:
            out.append((i, j - 1, "".join(chars[i:j])))
        i = j
    return out


def split_cues(chars, starts, ends, max_chars=42, min_dur=0.8):
    words = _words(chars)
    groups, cur = [], []
    for w in words:
        trial = " ".join(x[2] for x in cur + [w])
        if cur and len(trial) > max_chars:
            # 쉼표 등 뒤에서 끊을 수 있으면 그 지점까지만 현재 그룹으로
            cut = max((k for k in range(len(cur)) if cur[k][2][-1] in _PUNCT), default=None)
            if cut is not None and cut < len(cur) - 1 and len(" ".join(x[2] for x in cur[:cut + 1])) >= max_chars * 0.5:
                groups.append(cur[:cut + 1]); cur = cur[cut + 1:] + [w]
            else:
                groups.append(cur); cur = [w]
        else:
            cur.append(w)
            if w[2][-1] in ".?!" and len(" ".join(x[2] for x in cur)) >= max_chars * 0.6:
                groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    cues = [{"t0": starts[g[0][0]], "t1": ends[g[-1][1]], "text": " ".join(x[2] for x in g)} for g in groups]
    i = 0
    while i < len(cues):
        c = cues[i]
        if c["t1"] - c["t0"] < min_dur and len(cues) > 1:
            if i > 0 and len(cues[i - 1]["text"]) + 1 + len(c["text"]) <= max_chars:
                cues[i - 1] = {"t0": cues[i - 1]["t0"], "t1": c["t1"], "text": cues[i - 1]["text"] + " " + c["text"]}
                cues.pop(i); continue
            if i + 1 < len(cues):
                cues[i + 1] = {"t0": c["t0"], "t1": cues[i + 1]["t1"], "text": c["text"] + " " + cues[i + 1]["text"]}
                cues.pop(i); continue
        i += 1
    return cues
```

`sg/preview.py`
```python
"""미리보기 오디오 배치: 번역 TTS와 nonverbal 원래 녹음 조각을 변환된 시각에."""
import os


def plan_audio(segments, warp, tts_dir):
    out = []
    for g in segments:
        if g.get("nonverbal"):
            out.append({"src_in": g["in"], "src_out": g["out"], "t": warp(g["in"]), "kind": "nonverbal", "id": g["id"]})
        else:
            out.append({"file": os.path.join(tts_dir, f"{g['id']}.mp3"), "t": warp(g["in"]), "id": g["id"]})
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest -q`
Expected: 모두 통과. `test_tiny_tail_cue_is_merged`가 실패하면 `split_cues`의 합치기 순서를 고치되 테스트 기대값은 바꾸지 않는다.

- [ ] **Step 5: 커밋**
```bash
git add sg/subs.py sg/preview.py tests/test_subs.py tests/test_preview.py
git commit -m "feat: 정렬 기반 자막 큐 분할, 미리보기 오디오 배치"
```

---

### Task 6: 화면 문자열 교체 JSX + 영어 변환표·타임 워프

**Files:**
- Create: `scripts/ae/patch_text.jsx`, `scripts/patch_text.py`
- Modify: `scripts/timewarp.py` (`--aep` 입력 경로)

**Interfaces:**
- Consumes: `l10n/en.json` strings, `master/source.json` strings(comp_id, layer, ko), `profiles/en.json` fonts·min_font_scale, `tts/en/durs.json`
- Produces:
  - `scripts/patch_text.py <EP> <lang>` → `scripts/ae/patch_text_job.json` `{"aep","save_as":"build/<lang>/<EP>_<lang>_text.aep","out","items":[{"comp_id","layer","ko","text"}],"font_map","min_scale"}`
  - `patch_text.jsx` 로그 `{"replaced","keys_replaced","shrunk":[{"id","scale"}],"not_found":[...],"mismatch":[...],"errors":[]}`
  - `timewarp.py … --aep <path>`: job의 입력 aep를 지정(없으면 기존대로 `src/<EP>_main_ko.aep`)

- [ ] **Step 1: `scripts/patch_text.py`**

```python
"""화면 문자열 교체 job 생성.  usage: patch_text.py <EP> <lang>"""
import json, os, sys
ep, lang = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
L = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
abs_ep = os.path.abspath(ep); name = os.path.basename(abs_ep)
items = [{"comp_id": s["comp_id"], "layer": s["layer"], "ko": s["ko"], "text": L["strings"][s["id"]]["text"], "id": s["id"]}
         for s in src["strings"] if s["id"] in L["strings"]]
os.makedirs(os.path.join(abs_ep, "build", lang), exist_ok=True)
json.dump({"aep": os.path.join(abs_ep, "src", f"{name}_main_ko.aep"),
           "save_as": os.path.join(abs_ep, "build", lang, f"{name}_{lang}_text.aep"),
           "out": os.path.join(abs_ep, "build", lang, "patch_text_log.json"),
           "items": items, "font_map": prof["fonts"], "min_scale": prof["min_font_scale"]},
          open(os.path.join(root, "scripts/ae/patch_text_job.json"), "w"), ensure_ascii=False, indent=1)
print("items", len(items))
```

- [ ] **Step 2: `scripts/ae/patch_text.jsx`** (저장 후 BOM 추가)

```javascript
// 화면 문자열 교체. comp_id+layer로 찾아 원문(ko)과 같은 소스텍스트(키프레임 포함)를 번역으로 바꾸고,
// 폰트 매핑, 원래보다 넓어지면 글자 크기를 줄여(최소 min_scale) 원래 폭에 맞춘다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={replaced:0, keys_replaced:0, shrunk:[], not_found:[], mismatch:[], errors:[]};
function norm(s){ return String(s).replace(/\r\n|\n/g,"\r"); }
function width(L,t){ try{ var r=L.sourceRectAtTime(t,false); return r.width; }catch(e){ return 0; } }
function apply(td,txt){ td.text=txt; if(C.font_map[td.font]) td.font=C.font_map[td.font]; return td; }
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem) byId[it.id]=it; }
  for(var k=0;k<C.items.length;k++){
    var e=C.items[k], comp=byId[e.comp_id];
    if(!comp || e.layer>comp.numLayers || !(comp.layer(e.layer) instanceof TextLayer)){ LOG.not_found.push(e.id); continue; }
    var L=comp.layer(e.layer), wasLocked=L.locked; L.locked=false;
    var sp=L.property("ADBE Text Properties").property("ADBE Text Document");
    var t=L.inPoint+0.01, w0=width(L,t);
    try{
      if(sp.numKeys>0){
        for(var q=1;q<=sp.numKeys;q++){ var td=sp.keyValue(q);
          if(norm(td.text)===norm(e.ko)){ sp.setValueAtKey(q, apply(td,e.text)); LOG.keys_replaced++; } }
      } else {
        var td=sp.value;
        if(norm(td.text)!==norm(e.ko)){ LOG.mismatch.push(e.id); }
        else { sp.setValue(apply(td,e.text)); LOG.replaced++; }
      }
      var w1=width(L,t);
      if(w0>0 && w1>w0*1.05 && sp.numKeys===0){
        var s=Math.max(C.min_scale, w0/w1), td2=sp.value; td2.fontSize=td2.fontSize*s; sp.setValue(td2);
        LOG.shrunk.push({id:e.id, scale:Math.round(s*100)/100});
      }
    }catch(err){ LOG.errors.push(e.id+": "+String(err)); }
    L.locked=wasLocked;
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
```

- [ ] **Step 3: `scripts/timewarp.py`에 `--aep` 추가**

`json.dump({"aep": os.path.join(abs_ep, "src", f"{name}_main_ko.aep"),` 줄을 다음으로 바꾼다:
```python
json.dump({"aep": os.path.abspath(args[args.index("--aep") + 1]) if "--aep" in args else os.path.join(abs_ep, "src", f"{name}_main_ko.aep"),
```

테스트(`tests/test_timewarp_cli.py` 끝에 추가):
```python


def test_aep_option_overrides_input(tmp_path):
    ep = make_ep(tmp_path)
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/timewarp.py"), str(ep), "t4", "--test-pattern",
                    "--aep", str(tmp_path / "x.aep"), "--job", str(tmp_path / "job.json")], check=True)
    assert json.load(open(tmp_path / "job.json"))["aep"] == str(tmp_path / "x.aep")
```
Run: `python3 -m pytest -q tests/test_timewarp_cli.py` — 먼저 FAIL(KeyError 또는 다른 경로) 확인 후 위 수정 → PASS.

- [ ] **Step 4: 텍스트 교체 실행**

```bash
pgrep -x caffeinate >/dev/null || (nohup caffeinate -d -u -t 21600 >/dev/null 2>&1 &)
python3 scripts/patch_text.py episodes/B209 en
printf '\xef\xbb\xbf' | cat - scripts/ae/patch_text.jsx > t && mv t scripts/ae/patch_text.jsx
scripts/ae/run.sh "$PWD/scripts/ae/patch_text.jsx"
cat episodes/B209/build/en/patch_text_log.json
```
Expected: `errors: []`, `not_found: []`, `replaced + keys_replaced ≥ 40`(문자열 42개). `mismatch`가 있으면 해당 id의 인벤토리 텍스트와 실제 값을 비교해 원인 기록(같은 레이어를 다른 문자열이 키프레임으로 쓰는 경우 등).

- [ ] **Step 5: 영어 변환표 + 타임 워프**

```bash
python3 scripts/timewarp.py episodes/B209 en --durs episodes/B209/tts/en/durs.json --keep-subs --aep episodes/B209/build/en/B209_en_text.aep
scripts/ae/run.sh "$PWD/scripts/ae/localize.jsx"
python3 -c "import json; d=json.load(open('episodes/B209/build/en/localize_log.json')); print(d['parts'], len(d['warnings']), d['errors'])"
```
Expected: 길이 변화 출력(예: `length 979.35 -> 9xx`), 로그 `errors []`, warnings 0(있으면 내용 기록). `--keep-subs`인 이유: `#자막` 컴프는 다음 Task에서 영어 자막으로 다시 채운다.

- [ ] **Step 6: 커밋**
```bash
git add scripts/patch_text.py scripts/ae/patch_text.jsx scripts/timewarp.py tests/test_timewarp_cli.py
git commit -m "feat: 화면 문자열 영어 교체 JSX, 변환표 입력 aep 지정 — B209 영어 워프"
```

---

### Task 7: 영어 자막 (`scripts/subtitles.py` + `subtitles.jsx`)

**Files:**
- Create: `scripts/subtitles.py`, `scripts/ae/subtitles.jsx`

**Interfaces:**
- Consumes: `split_cues`(Task 5), `master_to_part`(Task 1), `build/en/warp.json`, `tts/en/*.align.json`, `graph_nas.json`(파트 컴프 아래 `#자막` 컴프 id)
- Produces:
  - `scripts/subtitles.py <EP> <lang>` → `scripts/ae/subtitles_job.json` `{"aep":"build/<lang>/<EP>_<lang>.aep","save_as":"build/<lang>/<EP>_<lang>_subs.aep","out","parts":[{"comp":"MAIN_KO","sub_comp_id":15600,"cues":[{"in","out","text"}]}]}`(cue 시각 = `#자막` 컴프 로컬 시간 = 변환 후 파트 시간 − 그 `#자막` 레이어 startTime 변환값) + `render/<lang>/<lang>.srt`(변환 후 마스터 시간)
  - `subtitles.jsx`: 각 `#자막` 컴프에서 텍스트 레이어 중 하나를 스타일 견본으로 복제해 큐마다 레이어 생성, 원래 한국어 텍스트 레이어는 삭제(오디오 레이어는 유지). 로그 `{"parts":[{"comp","created","deleted"}],"errors":[]}`

- [ ] **Step 1: `scripts/subtitles.py`**

```python
"""영어 자막 큐 → AE job + SRT.  usage: subtitles.py <EP> <lang>"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.subs import split_cues
from sg.timemap import PiecewiseMap
from sg.edl import master_to_part

ep, lang = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), "..")
prof = json.load(open(os.path.join(root, "profiles", f"{lang}.json")))
cfg = json.load(open(os.path.join(ep, "master_config.json")))
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
W = json.load(open(os.path.join(ep, "build", lang, "warp.json")))
warp = PiecewiseMap(W["master"])
pmap = {pid: PiecewiseMap(v["anchors"]) for pid, v in W["parts"].items()}
G = json.load(open(os.path.join(ep, cfg["graph"])))

# 파트 컴프 바로 아래 '#자막' 레이어: (sub_comp_id, startTime[원래 파트 시간])
subcomp = {}
for pid, P in cfg["parts"].items():
    Ls = [L for L in G["comps"][P["comp_id"]]["layers"]
          if L["src"] is not None and G["comps"].get(str(L["src"]), {}).get("name", "").startswith(cfg["subtitle_comp_prefix"])]
    if len(Ls) != 1:
        raise ValueError(f"{pid}: subtitle comp layers {len(Ls)}")
    subcomp[pid] = (Ls[0]["src"], Ls[0]["st"])

parts = {pid: [] for pid in cfg["parts"]}
srt = []
for g in src["segments"]:
    if g.get("nonverbal"):
        continue
    al = json.load(open(os.path.join(ep, "tts", lang, f"{g['id']}.align.json")))
    loc = master_to_part(edl, g["in"])
    if loc is None:
        continue
    pid, u = loc
    base_part = pmap[pid](u)                       # 변환 후 파트 시간에서 이 구간 시작
    base_master = warp(g["in"])
    sc_id, sc_st = subcomp[pid]
    sc_st_new = pmap[pid](sc_st)                   # localize.jsx는 프리컴프 startTime을 map(ost)로 옮김
    for c in split_cues(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"],
                        prof["subs"]["max_chars"], prof["subs"]["min_dur"]):
        parts[pid].append({"in": round(base_part + c["t0"] - sc_st_new, 3),
                           "out": round(base_part + c["t1"] - sc_st_new - prof["subs"]["gap"], 3), "text": c["text"]})
        srt.append((base_master + c["t0"], base_master + c["t1"], c["text"]))

abs_ep = os.path.abspath(ep); name = os.path.basename(abs_ep)
json.dump({"aep": os.path.join(abs_ep, "build", lang, f"{name}_{lang}.aep"),
           "save_as": os.path.join(abs_ep, "build", lang, f"{name}_{lang}_subs.aep"),
           "out": os.path.join(abs_ep, "build", lang, "subtitles_log.json"),
           "parts": [{"comp": cfg["parts"][pid]["comp"], "sub_comp_id": subcomp[pid][0], "cues": cues} for pid, cues in parts.items()]},
          open(os.path.join(root, "scripts/ae/subtitles_job.json"), "w"), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(ep, "render", lang), exist_ok=True)
fmt = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t % 1) * 1000)) % 1000:03d}"
with open(os.path.join(ep, "render", lang, f"{lang}.srt"), "w") as f:
    for n, (a, b, t) in enumerate(sorted(srt), 1):
        f.write(f"{n}\n{fmt(a)} --> {fmt(b)}\n{t}\n\n")
print({pid: len(c) for pid, c in parts.items()}, "srt", len(srt))
```

주의: `localize.jsx`는 여러 번 쓰이는 프리컴프를 복제하므로 워프 후 `#자막` 컴프 id가 바뀔 수 있다. `subtitles.jsx`는 id가 아니라 **파트 컴프 바로 아래에서 이름이 `#자막`으로 시작하는 레이어의 소스**로 찾는다(job의 `sub_comp_id`는 참고용).

- [ ] **Step 2: `scripts/ae/subtitles.jsx`** (저장 후 BOM 추가)

```javascript
// 파트 컴프 바로 아래 '#자막' 프리컴프를 영어 자막으로 다시 채운다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={parts:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep);
  for(var k=0;k<C.parts.length;k++){
    var part=C.parts[k], main=null, sub=null;
    for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===part.comp) main=it; }
    for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j); if(L.source instanceof CompItem && L.source.name.indexOf("#자막")===0){ sub=L.source; L.enabled=true; } }
    if(!sub){ LOG.errors.push("no #자막 under "+part.comp); continue; }
    var tmpl=null, olds=[];
    for(var j=1;j<=sub.numLayers;j++){ var L=sub.layer(j); if(L instanceof TextLayer){ olds.push(L); if(!tmpl) tmpl=L; } }
    if(!tmpl){ LOG.errors.push("no text template in "+sub.name); continue; }
    for(var j=0;j<olds.length;j++) olds[j].locked=false;
    var made=0;
    for(var c=0;c<part.cues.length;c++){
      var q=part.cues[c], N=tmpl.duplicate();
      var sp=N.property("ADBE Text Properties").property("ADBE Text Document");
      while(sp.numKeys>0) sp.removeKey(1);
      var td=sp.value; td.text=q.text; sp.setValue(td);
      N.startTime=0; N.inPoint=q["in"]; N.outPoint=q["out"]; if(Math.abs(N.inPoint-q["in"])>1e-3) N.inPoint=q["in"];
      N.name="EN "+(c+1); N.enabled=true; made++;
    }
    for(var j=0;j<olds.length;j++) olds[j].remove();
    LOG.parts.push({comp:part.comp, sub:sub.name, created:made, deleted:olds.length});
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
```

- [ ] **Step 3: 실행·확인**

```bash
python3 scripts/subtitles.py episodes/B209 en
printf '\xef\xbb\xbf' | cat - scripts/ae/subtitles.jsx > t && mv t scripts/ae/subtitles.jsx
scripts/ae/run.sh "$PWD/scripts/ae/subtitles.jsx"
cat episodes/B209/build/en/subtitles_log.json
python3 -c "import json; w=json.load(open('episodes/B209/build/en/warp.json')); print({k: round(v['dur_new'],2) for k,v in w['parts'].items()})"
scripts/ae/render.sh "$PWD/episodes/B209/build/en/B209_en_subs.aep" MAIN_KO 0 60 "$PWD/episodes/B209/build/en/check_0_60.mp4" 29.97 "H.264 - Match Render Settings - 15 Mbps"
ffmpeg -v error -y -i episodes/B209/build/en/check_0_60.mp4 -vf "fps=1/3,scale=480:-1,tile=4x5" -frames:v 1 episodes/B209/build/en/check_sheet.png
```
Expected: 로그 errors 없음, 파트별 created > 0, deleted = 원래 한국어 자막 레이어 수. `check_sheet.png`에서 하단 자막이 영어이고 자막바 안에 들어가며(넘침 없음), 화면 타이틀이 영어로 바뀌었는지 눈으로 확인. 자막이 자막바를 넘치면 `profiles/en.json`의 `subs.max_chars`를 38로 낮추고 Step 3을 다시 실행.

- [ ] **Step 4: 커밋**
```bash
git add scripts/subtitles.py scripts/ae/subtitles.jsx
git add -f episodes/B209/render/en/en.srt
git commit -m "feat: 영어 자막 레이어 생성 + SRT — B209"
```

---

### Task 8: 파트 렌더 + 영어 미리보기 조립 (`scripts/preview.py`)

**Files:**
- Create: `scripts/preview.py`
- Modify: `docs/RUNBOOK.md`

**Interfaces:**
- Consumes: `plan_audio`(Task 5), `build/en/warp.json`, `build/en/B209_en_subs.aep`, `master/edl.json`, 원래 내레이션 wav(nonverbal 조각용)
- Produces: `render/en/part_<pid>.mp4`, `render/en/B209_EN_preview.mp4`(영상: 파트 순서 + 한국어 아웃트로 임시, 오디오: 영어 TTS + nonverbal 원래 조각)

- [ ] **Step 1: 파트 렌더**

```bash
cd ~/Projects/semoji_global
for pid in mina gayoung gaeul; do
  read COMP DUR < <(python3 -c "import json; v=json.load(open('episodes/B209/build/en/warp.json'))['parts']['$pid']; print(v['comp'], round(v['dur_new'],3))")
  scripts/ae/render.sh "$PWD/episodes/B209/build/en/B209_en_subs.aep" $COMP 0 $DUR "$PWD/episodes/B209/render/en/part_$pid.mp4" 29.97 "H.264 - Match Render Settings - 15 Mbps"
done
```
Expected: 세 파일, 길이가 dur_new와 ±0.05초.

- [ ] **Step 2: `scripts/preview.py`**

```python
"""영어 미리보기 조립.  usage: preview.py <EP> <lang>"""
import json, os, subprocess, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.preview import plan_audio
from sg.timemap import PiecewiseMap
from sg.edl import master_to_part

ep, lang = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(ep, "master_config.json")))
edl = json.load(open(os.path.join(ep, "master/edl.json")))
src = json.load(open(os.path.join(ep, "master/source.json")))
W = json.load(open(os.path.join(ep, "build", lang, "warp.json")))
warp = PiecewiseMap(W["master"])
out_dir = os.path.join(ep, "render", lang)
order = []
for c in edl["parts"]:
    if c["id"] not in order:
        order.append(c["id"])
vids = [os.path.join(out_dir, f"part_{p}.mp4") for p in order] + [os.path.join(ep, "assets", "outro.mov")]
filt = "".join(f"[{i}:v]scale=1920:1080,fps=30000/1001,format=yuv420p,setsar=1[v{i}];" for i in range(len(vids)))
filt += "".join(f"[v{i}]" for i in range(len(vids))) + f"concat=n={len(vids)}:v=1:a=0[v]"
video = os.path.join(out_dir, "video_only.mp4")
args = ["ffmpeg", "-v", "error", "-y"]
for v in vids:
    args += ["-i", v]
subprocess.run(args + ["-filter_complex", filt, "-map", "[v]", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", video], check=True)

# 오디오: TTS + nonverbal 원래 녹음 조각
G = json.load(open(os.path.join(ep, cfg["graph"])))
nar_file = {}
for pid, P in cfg["parts"].items():
    for it in G["items"].values():
        if it["name"] == P["narration"]:
            rel = os.path.relpath(unicodedata.normalize("NFC", it["file"]), unicodedata.normalize("NFC", cfg["nas_ep"]))
            nar_file[pid] = os.path.join(ep, "src", rel)
plan = plan_audio(src["segments"], warp, os.path.join(ep, "tts", lang))
ins, flt = [], []
for k, p in enumerate(plan):
    if p.get("kind") == "nonverbal":
        pid, u = master_to_part(edl, p["src_in"])
        ins += ["-ss", f"{u:.3f}", "-t", f"{p['src_out'] - p['src_in']:.3f}", "-i", nar_file[pid]]
    else:
        ins += ["-i", p["file"]]
    flt.append(f"[{k}:a]aresample=48000,adelay={int(p['t'] * 1000)}|{int(p['t'] * 1000)}[a{k}]")
mix = ";".join(flt) + ";" + "".join(f"[a{k}]" for k in range(len(plan))) + f"amix=inputs={len(plan)}:normalize=0[a]"
audio = os.path.join(out_dir, "narration.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", mix, "-map", "[a]", "-ac", "2", audio], check=True)
final = os.path.join(out_dir, f"{os.path.basename(os.path.abspath(ep))}_{lang.upper()}_preview.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", final], check=True)
print(final)
```

- [ ] **Step 3: 실행·확인**

```bash
python3 scripts/preview.py episodes/B209 en
ffprobe -v error -show_entries format=duration -of csv=p=0 episodes/B209/render/en/B209_EN_preview.mp4
ffmpeg -v error -y -i episodes/B209/render/en/B209_EN_preview.mp4 -vf "fps=1/10,scale=320:-1,tile=8x13" -frames:v 1 episodes/B209/render/en/sheet.png
```
Expected: 길이 ≈ `warp.json length_new` + 아웃트로 10.28초(±0.5초). `sheet.png` 확인(영어 타이틀·자막, 빈 화면 없음). 임의 3지점(처음 30초, 챕터 2 전환 309초 근처의 변환 시각, 가을 파트 유튜브 컷 근처)을 `ffmpeg -ss <t> -t 15`로 잘라 사용자에게 전달해 내레이션과 화면이 맞는지 확인받는다.

- [ ] **Step 4: 런북 갱신 + 커밋**

`docs/RUNBOOK.md`에 "## 4. 영어판(계획 2)" 섹션 추가: translate.py → tts.py --rewrite-loop → asr_check.py → patch_text.py+jsx → timewarp.py --durs --keep-subs --aep → localize.jsx → subtitles.py+jsx → 파트 렌더 → preview.py, 각 단계 Expected 한 줄씩.
```bash
git add scripts/preview.py docs/RUNBOOK.md
git commit -m "feat: 영어 미리보기 조립 — B209_EN_preview"
```
