from backend.research.lanes import _trust


def test_classify_tier_encyclopedia_is_A():
    assert _trust.classify_tier("https://en.wikipedia.org/wiki/X") == "A"


def test_classify_tier_wildcard_go_kr_is_A():
    assert _trust.classify_tier("https://kostat.go.kr/portal") == "A"


def test_classify_tier_unknown_domain():
    assert _trust.classify_tier("https://some-random-blog.example/post") == "unknown"


def test_classify_tier_empty_url():
    assert _trust.classify_tier("") == "unknown"


def test_is_evidence_eligible():
    assert _trust.is_evidence_eligible("https://en.wikipedia.org/wiki/X")
    assert not _trust.is_evidence_eligible("https://some-random-blog.example/post")
