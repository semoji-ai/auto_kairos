from backend import sessions


def test_roundtrip(tmp_path):
    assert sessions.load_session(tmp_path) is None
    sessions.save_session(tmp_path, "sess-abc")
    assert sessions.load_session(tmp_path) == "sess-abc"


def test_overwrite(tmp_path):
    sessions.save_session(tmp_path, "s1")
    sessions.save_session(tmp_path, "s2")
    assert sessions.load_session(tmp_path) == "s2"
