from backend import env


def test_get_key_from_os_env(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "from-os")
    assert env.get_key("SERPER_API_KEY") == "from-os"


def test_get_key_from_file(monkeypatch, tmp_path):
    envf = tmp_path / ".env"
    envf.write_text('# 주석\nSERPER_API_KEY="file-key"\nPIXABAY_API_KEY=pix\n', encoding="utf-8")
    monkeypatch.setenv("AUTO_KAIROS_ENV", str(envf))
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    assert env.get_key("SERPER_API_KEY") == "file-key"   # 따옴표 제거
    assert env.get_key("PIXABAY_API_KEY") == "pix"


def test_get_key_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTO_KAIROS_ENV", str(tmp_path / "nope.env"))
    monkeypatch.delenv("ZZZ", raising=False)
    assert env.get_key("ZZZ") == ""
