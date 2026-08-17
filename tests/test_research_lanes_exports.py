def test_lane_exports_importable():
    from backend.research.lanes import (
        search_wikipedia, search_news, search_crossref, search_openlibrary,
        fetch_wikipedia_article_content,
    )
    for fn in (search_wikipedia, search_news, search_crossref, search_openlibrary):
        assert callable(fn)
