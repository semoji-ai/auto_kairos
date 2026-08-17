from backend.research.lanes.wikipedia import search_wikipedia
from backend.research.lanes.crossref import search_crossref
from backend.research.lanes.openlibrary import search_openlibrary


def test_wikipedia_normalizes(monkeypatch):
    def fake_json(url, **k):
        return {"query": {"search": [{"title": "유한양행", "snippet": "<b>제약</b> 회사"}]}}
    out = search_wikipedia("유한양행", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "유한양행"
    assert out[0]["lane"] == "wikipedia"
    assert out[0]["tier_hint"] == "A"
    assert "<b>" not in out[0]["snippet"]
    assert out[0]["url"].startswith("https://ko.wikipedia.org/wiki/")


def test_wikipedia_lane_error_entry():
    def boom(url, **k):
        raise RuntimeError("net")
    out = search_wikipedia("x", fetch_json_impl=boom)
    assert any(r.get("error") for r in out)


def test_crossref_normalizes():
    def fake_json(url, **k):
        return {"message": {"items": [{
            "title": ["A Study"], "URL": "https://doi.org/10.1/x", "DOI": "10.1/x",
            "author": [{"given": "Jane", "family": "Doe"}],
            "publisher": "Elsevier", "created": {"date-parts": [[2020, 5, 1]]},
            "abstract": "<p>abs</p>"}]}}
    out = search_crossref("study", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "A Study"
    assert out[0]["lane"] == "crossref"
    assert out[0]["kind"] == "paper"
    assert out[0]["doi"] == "10.1/x"
    assert "Jane Doe" in out[0]["author"]


def test_openlibrary_normalizes():
    def fake_json(url, **k):
        return {"docs": [{"title": "Book", "key": "/works/OL1W",
                          "author_name": ["Kim"], "publisher": ["Munhak"],
                          "first_publish_year": 1999}]}
    out = search_openlibrary("book", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "Book"
    assert out[0]["lane"] == "openlibrary"
    assert out[0]["kind"] == "book"
    assert out[0]["url"] == "https://openlibrary.org/works/OL1W"
