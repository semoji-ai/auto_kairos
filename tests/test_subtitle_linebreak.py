"""말자막 줄 나누기 — 세모지 통합보고 §2-1 의 ✕/○ 사례.

generate_subtitles.smart_split 과 SubtitleSync.smart_split_text 가 같은 규칙을 쓰는지도 본다.
"""
import pytest

from auto_agent.tools.subtitle_linebreak import break_lines


def _splitters():
    from auto_agent.scripts.generate_subtitles import smart_split
    from auto_agent.tools.subtitle_sync import SubtitleSync
    sync = SubtitleSync.__new__(SubtitleSync)
    sync.max_chars = 30
    return [break_lines, smart_split, sync.smart_split_text]


SPLITTERS = _splitters()


@pytest.mark.parametrize("split", SPLITTERS)
def test_break_at_comma_not_after_next_clause_head(split):
    # ✕ "둘러보시면, 이 회사가 / 만든…"   ○ "둘러보시면," / "이 회사가 만든…"
    lines = split("중국 어느 가정집을 둘러보시면, 이 회사가 만든 가전제품이 꼭 하나쯤 있습니다.")
    assert lines[0].endswith("둘러보시면,")
    assert lines[1].startswith("이 회사가 만든")


@pytest.mark.parametrize("split", SPLITTERS)
def test_never_leave_lone_predicate(split):
    # ✕ "…성장 방식을 / 선택합니다."
    lines = split("마이디어는 경쟁사를 하나씩 사들이며 덩치를 키우는 성장 방식을 선택합니다.")
    assert lines[-1] != "선택합니다."
    assert len(lines[-1].split()) >= 2
    assert not lines[0].endswith("방식을")
    assert not lines[0].endswith("키우는")          # 꾸밈말만 줄 끝에 남기지 않는다


@pytest.mark.parametrize("split", SPLITTERS)
def test_object_goes_with_predicate(split):
    # ✕ "~로 몸집을 / 점점 불려"   ○ "~로 / 몸집을 점점 불려"
    lines = split("마이디어는 공격적인 인수합병으로 몸집을 점점 불려 나갔습니다.")
    assert lines == ["마이디어는 공격적인 인수합병으로", "몸집을 점점 불려 나갔습니다."]


@pytest.mark.parametrize("split", SPLITTERS)
def test_date_split_only_when_direction_shows_year_typo(split):
    # 연출이 연도를 별도 타이포로 보여 줄 때만 "연도," 를 따로 뗀다
    assert split("1975년, 작업장은 마을 공터에 세운 작은 창고였습니다.", split_lead_date=True)[:2] == \
        ["1975년,", "작업장은 마을 공터에 세운 작은 창고였습니다."]
    assert split("1922년 11월 12일, 충남 천안군 북일면 부대리.", split_lead_date=True)[0] == "1922년 11월 12일,"
    # 그렇지 않으면 한 줄에 들어가는 문장은 날짜와 함께
    assert split("1922년 11월 12일, 충남 천안군 북일면 부대리.") == ["1922년 11월 12일, 충남 천안군 북일면 부대리."]
    # 길어서 나눠야 해도 날짜만 따로 남기지 않는다
    lines = split("2026년, 창립 74년 만에 처음으로 재계 서열 5위에 오른 기업이 있습니다.")
    assert lines[0] != "2026년," and lines[0].startswith("2026년,")


def test_scene_marker_for_lead_date_split():
    from auto_agent.tools.subtitle_linebreak import scene_splits_lead_date
    assert scene_splits_lead_date({"subtitle_split_lead_date": True}) is True
    assert scene_splits_lead_date({"techniques": ["year-tag"]}) is True
    assert scene_splits_lead_date({"techniques": ["sage-date-typing-card", "photo-pop"]}) is True
    # 명시 필드가 기법보다 우선
    assert scene_splits_lead_date({"techniques": ["year-tag"], "subtitle_split_lead_date": False}) is False
    assert scene_splits_lead_date({"techniques": ["photo-pop"]}) is False
    assert scene_splits_lead_date({}) is False and scene_splits_lead_date(None) is False


def test_generate_tts_subtitle_contract_uses_scene_marker():
    from auto_agent.scripts import generate_tts as g
    scene = {"narration": "1922년 11월 12일, 충남 천안군 북일면 부대리.", "techniques": ["year-tag"]}
    g._ensure_subtitle_line_contract(scene, scene["narration"], scene["narration"], [])
    assert scene["subtitle_lines"][0] == "1922년 11월 12일,"
    plain = {"narration": "1922년 11월 12일, 충남 천안군 북일면 부대리."}
    g._ensure_subtitle_line_contract(plain, plain["narration"], plain["narration"], [])
    assert plain["subtitle_lines"] == ["1922년 11월 12일, 충남 천안군 북일면 부대리."]


@pytest.mark.parametrize("split", SPLITTERS)
def test_quoted_parenthesized_name_stays_with_particle(split):
    text = "'익스프레스 마스터(EXPRESS MASTER)'는 마이디어가 처음 내놓은 선풍기 브랜드입니다."
    lines = split(text)
    assert any("'익스프레스 마스터(EXPRESS MASTER)'는" in ln for ln in lines)
    assert "".join(lines).replace(" ", "") == text.replace(" ", "")


@pytest.mark.parametrize("split", SPLITTERS)
def test_numbers_kept_as_in_manuscript(split):
    lines = split("당시 직원 수는 3,500여명에 달했고, 공장도 세 곳으로 늘었습니다.")
    assert lines[0].endswith("3,500여명에 달했고,")
    assert all("3,500" not in ln or "3,500여명에" in ln for ln in lines)


def test_short_line_unchanged_and_lines_within_limit():
    assert break_lines("짧은 문장입니다.") == ["짧은 문장입니다."]
    long = ("하지만 이 가난한 마을에 유일한 자랑거리가 있었으니 그당시 흔치않게 학교가 있었죠. "
            "어린 종희도 교육을 통해 새로운 세상에 점차 눈을 뜨고 있었는데요.")
    lines = break_lines(long)
    assert all(len(ln) <= 33 for ln in lines)
    assert "".join(lines).replace(" ", "") == long.replace(" ", "")
    assert all(len(ln.split()) >= 2 for ln in lines[-1:])


def test_one_breath_quoted_phrase_kept_but_long_quote_can_break():
    lines = break_lines("이른바 '드라이버만 있으면 되는 조립' 방식이 마이디어의 출발점이었습니다.")
    assert any("'드라이버만 있으면 되는 조립'" in ln for ln in lines)
    long_quote = ('"김 사장, 경부고속도로를 곧 착공하면, 공사하다가 화약이 떨어져서 '
                  '공사를 중단한다는 소리 안 나오게 할 자신 있어요?"')
    assert all(len(ln) <= 33 for ln in break_lines(long_quote))
