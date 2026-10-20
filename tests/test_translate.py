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


def test_parse_ignores_trailing_prose_with_braces():
    txt = '{"n001": "A", "n002": "B"}\nNote: I kept {brand} names as-is.'
    assert parse_response(txt, ["n001", "n002"]) == {"n001": "A", "n002": "B"}


def test_non_string_value_counts_as_missing():
    with pytest.raises(MissingIds) as e:
        parse_response('{"n001": "A", "n002": ["x", "y"]}', ["n001", "n002"])
    assert e.value.missing == ["n002"]


def test_broken_json_is_retried_not_fatal():
    calls = []

    def runner(prompt):
        calls.append(1)
        return '{"n001": "He said "never" ok"}' if len(calls) == 1 else '{"n001": "A", "n002": "B"}'

    assert translate_batch(ITEMS, {}, "en", "segments", runner) == {"n001": "A", "n002": "B"}


def test_raster_prompt_allows_skip_and_emphasis_markers():
    p = build_prompt([{"id": "1#0", "ko": "매장 수 및 매출 매년 증가", "max_chars": 40, "two_tone": True,
                       "layer": "2 자막", "context": "매장 수도 늘고"}], {}, "en", "raster")
    assert "__SKIP__" in p and "[[" in p and "max_chars" in p
