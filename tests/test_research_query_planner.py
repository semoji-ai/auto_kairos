from backend.research import query_planner


def test_plan_queries_parses(monkeypatch):
    brief = {"real_topic": "유한양행", "core_question": "왜?"}
    raw = '{"queries":[{"query":"유한양행","rationale":"본 entity","lang":"ko"},' \
          '{"query":"유일한 박사","rationale":"창업자","lang":"ko"}]}'
    out = query_planner.plan_queries(brief, invoker=lambda p: raw)
    assert [q["query"] for q in out] == ["유한양행", "유일한 박사"]
    assert out[0]["lang"] == "ko"


def test_plan_queries_drops_overlong(monkeypatch):
    brief = {"real_topic": "x"}
    raw = '{"queries":[{"query":"' + "가" * 90 + '","rationale":"too long","lang":"ko"},' \
          '{"query":"짧은쿼리","rationale":"ok","lang":"ko"}]}'
    out = query_planner.plan_queries(brief, invoker=lambda p: raw)
    assert [q["query"] for q in out] == ["짧은쿼리"]


def test_plan_queries_fallback_on_bad_json(monkeypatch):
    brief = {"real_topic": "유한양행"}
    out = query_planner.plan_queries(brief, invoker=lambda p: "not json")
    assert out and out[0]["query"] == "유한양행"


def test_plan_queries_fallback_uses_slug(monkeypatch):
    brief = {}
    out = query_planner.plan_queries(brief, project_slug="tesla_story",
                                     invoker=lambda p: "boom")
    assert out and out[0]["query"] == "tesla"
