"""헤드리스 claude로 현지화 번역. 프롬프트·응답 파싱은 순수 함수."""
import json
import re
import subprocess

LANG_NAMES = {"en": "English (US)", "ja": "Japanese", "zh": "Simplified Chinese"}
# 그림 속 문구의 글자 규칙(폰트에 있는 글자만 쓰게) — 언어별
SCRIPT_RULES = {
    "en": "Use only plain ASCII characters (no ₩, no curly quotes); write Korean won as KRW. ",
    "zh": "使用简体中文（不要繁体字），数字用阿拉伯数字，韩元写作“韩元”，不要表情符号或生僻字。"
          "Count max_chars as Chinese characters. ",
}


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
    elif kind == "raster":
        rules = (f"You localize Korean text drawn inside illustrations of a Korean explainer video into {target}.\n"
                 "Each item is text recognized by OCR inside one illustration layer ('layer' is the designer's layer name, "
                 "'context' is the narration playing while it is on screen). OCR sometimes misreads drawings, logos or "
                 "patterns as text: if the item is not real meaningful Korean text, return exactly \"__SKIP__\".\n"
                 "Otherwise translate it short and punchy, never longer than max_chars. Keep numbers and years. "
                 + SCRIPT_RULES.get(lang, SCRIPT_RULES["en"]) +
                 "If two_tone is true, the original emphasized part of the phrase in a second color: wrap the "
                 "corresponding emphasized English words in [[ ]] (exactly one [[...]] span).\n")
    else:
        rules = (f"You localize short on-screen texts (titles, labels, captions, source credits) of a Korean video into {target}.\n"
                 "Keep them short and punchy. Never exceed max_chars. Keep numbers, years and brand names. "
                 + {"en": "'Source: ...' for 출처.\n", "zh": "出处写作“来源：…”。只用简体中文。\n"}.get(lang, "\n"))
    body = json.dumps(items, ensure_ascii=False, indent=0)
    return (rules + f"Glossary (use exactly):\n{gl}\n\n"
            "Return ONLY a JSON object mapping each id to its translation. No commentary, no code fences.\n\nITEMS\n" + body)


def parse_response(text, ids):
    t = re.sub(r"```(?:json)?", "", text)
    i = t.find("{")
    if i < 0:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    obj, _ = json.JSONDecoder().raw_decode(t, i)   # 첫 객체만 읽음(뒤에 붙은 설명의 중괄호 무시)
    out = {k: obj[k].strip() for k in ids if isinstance(obj.get(k), str) and obj[k].strip()}
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
        except ValueError:   # JSON 깨짐(이스케이프 안 된 따옴표 등) → 같은 묶음 재요청
            if attempt == retries:
                raise
    return done


def claude_runner(prompt):
    r = subprocess.run(["claude", "-p", "--output-format", "text"], input=prompt, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return r.stdout
