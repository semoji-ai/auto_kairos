from pathlib import Path
from backend import verify_voice

GOOD = """스팸은 1937년 미국에서 태어났습니다.

무려 80년이 넘는 역사를 가진 통조림이죠.

그런데,
한국에서는 명절 선물세트로 팔리고 있습니다.

해외 언론들도 놀라워하며 기사를 쏟아냈다고 합니다.

하지만 서양에서는 싸구려 햄으로 취급받고 있는데요.

이것은 단순한 통조림이 아니었습니다.
전쟁과 함께 세계로 퍼져나간 음식이거든요.
"""

PLAIN = """스팸은 1937년 미국에서 태어났다.
80년이 넘는 역사를 가진 통조림이다.
한국에서는 선물세트로 팔리게 됐다.
해외 언론들도 기사를 쏟아냈다.
전쟁과 함께 세계로 퍼졌다.
"""


def test_good_passes():
    r = verify_voice.check(GOOD)
    assert r["ok"], r["violations"]


def test_plain_endings_fail():
    r = verify_voice.check(PLAIN)
    assert not r["ok"]
    assert any("평서체" in v for v in r["violations"])


def test_hangul_year_fails():
    r = verify_voice.check(GOOD.replace("1937년", "천구백삼십칠년"))
    assert not r["ok"]
    assert any("숫자" in v for v in r["violations"])


def test_uniform_lines_fail():
    txt = "\n".join(["스팸은 미국에서 태어난 음식입니다."] * 30)
    r = verify_voice.check(txt)
    assert not r["ok"]
    assert any("리듬" in v or "균일" in v for v in r["violations"])


def test_meta_lines_excluded():
    txt = GOOD + "\n[B-roll: 공장 전경]\n(연출: 줌인)\n"
    r = verify_voice.check(txt)
    assert r["ok"], r["violations"]


def test_gate_rewrites_once_on_fail(tmp_path, monkeypatch):
    """게이트 실패 → 위반 겨냥 재작성 1회 → 재채점."""
    from backend import pipeline
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("# t\n\n채널: semoji\n분량: 5분\n", encoding="utf-8")
    (proj / "final_manuscript.md").write_text(PLAIN, encoding="utf-8")
    calls = []
    def fake_run_skill(prompt, proj_dir, **kw):
        calls.append(prompt)
        (proj / "final_manuscript.md").write_text(GOOD * 8, encoding="utf-8")   # 분량 밴드 내
        return {"returncode": 0, "session_id": None}
    monkeypatch.setattr(pipeline, "run_skill", fake_run_skill)
    r = pipeline.apply_voice_gate(proj)
    assert r["gate"] == "pass"
    rewrites = [c for c in calls if "평서체" in c]
    assert len(rewrites) == 1          # 심사 2회 + 재작성 1회 중 재작성만 위반 포함


def test_gate_skipped_for_other_channels(tmp_path):
    from backend import pipeline
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("# t\n\n채널: iromism\n", encoding="utf-8")
    assert pipeline.apply_voice_gate(proj)["gate"] == "skipped"


def test_no_colloq_no_report_fails():
    txt = "\n".join(f"메시는 {1987+i}년에 새로운 기록을 세운 최고의 선수였습니다." for i in range(20))
    r = verify_voice.check(txt)
    assert not r["ok"]
    assert any("전달체" in v or "구어체" in v for v in r["violations"])


def test_duration_deviation_fails(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("# t\n\n채널: semoji\n분량: 5분\n", encoding="utf-8")
    (proj / "final_manuscript.md").write_text(GOOD * 20, encoding="utf-8")  # 과대 분량(약 2,600자 > 상한 1,950)
    r = verify_voice.check_project(proj)
    assert any("분량" in v for v in r["violations"])


def test_judge_prompt_targets_comprehension():
    from backend import pipeline
    p = pipeline.build_judge_prompt("원고본문")
    assert "중학생" in p and "JSON" in p and "원고본문" in p


def test_rewrite_prompt_prioritizes_flow():
    from backend import pipeline
    p = pipeline.build_rewrite_prompt("원고", ["평서체 6회"], ["숫자 나열 끊김"])
    assert p.index("자연스러") < p.index("평서체 6회")   # 우선순위: 흐름 > 지표
    assert "에피소드" in p                                # 분량 조절은 문장 쳐내기가 아니라 에피소드 단위
    assert "억지" in p                                    # 지표 스터핑 금지 명시


def test_gate_runs_judge_and_rewrite(tmp_path, monkeypatch):
    """regex PASS여도 심사 FAIL이면 재작성. 재작성 후 심사 재실행."""
    from backend import pipeline
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("# t\n\n채널: semoji\n분량: 5분\n", encoding="utf-8")
    (proj / "final_manuscript.md").write_text(GOOD * 8, encoding="utf-8")
    calls = []
    def fake_run_skill(prompt, proj_dir, output_last=None, **kw):
        calls.append(prompt)
        if "JSON 한 줄" in prompt:      # 심사 프롬프트만
            verdict = ('{"issues": [{"quote": "x", "why": "숫자 나열 끊김", "severity": "major"}]}'
                       if len(calls) == 1 else '{"issues": [{"quote": "y", "why": "취향", "severity": "minor"}]}')
            __import__("pathlib").Path(output_last).write_text(verdict, encoding="utf-8")
        else:
            (proj / "final_manuscript.md").write_text(GOOD * 8, encoding="utf-8")
        return {"returncode": 0, "session_id": None}
    monkeypatch.setattr(pipeline, "run_skill", fake_run_skill)
    r = pipeline.apply_voice_gate(proj)
    assert r["gate"] == "pass"
    assert len(calls) == 3    # 심사 FAIL → 재작성 → 심사 PASS


def test_terminology_rules_present():
    """직역 방지 3단 판단이 팩과 심사 프롬프트에 존재."""
    from pathlib import Path
    from backend import pipeline
    pack = (Path("data/artstyle/semoji-voice.md")).read_text(encoding="utf-8")
    assert "통용어" in pack and "입단 테스트" in pack and "직역" in pack
    assert "직역" in pipeline.build_judge_prompt("x")
