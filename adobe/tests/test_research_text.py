from backend.research.lanes import _text


def test_contains_korean():
    assert _text.contains_korean("한국어")
    assert not _text.contains_korean("english only")


def test_wikipedia_languages_order():
    assert _text.wikipedia_languages_for_query("한국") == ["ko", "en"]
    assert _text.wikipedia_languages_for_query("korea") == ["en", "ko"]


def test_extract_domain_strips_www():
    assert _text.extract_domain("https://www.example.com/path") == "example.com"
    assert _text.extract_domain("https://sub.go.kr") == "sub.go.kr"


def test_clean_html_fragment():
    assert _text.clean_html_fragment("<b>hi</b>  there") == "hi there"


def test_split_google_news_title():
    assert _text.split_google_news_title("Headline - Reuters") == ("Headline", "Reuters")
    assert _text.split_google_news_title("NoPublisher") == ("NoPublisher", "")


def test_title_similar():
    assert _text.title_similar("apple banana cherry", "apple banana cherry date")
    assert not _text.title_similar("apple banana cherry", "x y z w")
