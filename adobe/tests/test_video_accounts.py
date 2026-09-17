"""영상 생성의 계정 일관성 — 됐다 안 됐다 하던 원인.

UUID 는 올린 계정에서만 보인다. 예전에는 업로드가 pick(0), 생성이
pick(필요량)으로 계정을 따로 골라, 1번 계정 잔액이 0보다 크고 필요량보다
작은 날은 업로드와 생성이 다른 계정으로 갈려 「UUID 도 파일도 아니다」로
떨어졌다. 잔액은 날마다 바뀌므로 성공과 실패가 오락가락했다.

규칙: **계정은 generate 가 한 번 고르고, 업로드는 그 env 를 그대로 받는다.**
업로드 캐시 열쇠에는 계정 이름이 들어간다 — 계정을 바꿔 재시도할 때
남의 UUID 를 재사용하지 않게.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend import video


def test_upload_cache_key_is_per_account(tmp_path, monkeypatch):
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    uploads = []
    monkeypatch.setattr(video, "upload",
                        lambda p, env=None, **kw: uploads.append(env) or f"uid-{len(uploads)}")
    cache = {}
    u1 = video._upload_cached(img, cache, acct="A", env={"HOME": "/a"})
    u2 = video._upload_cached(img, cache, acct="B", env={"HOME": "/b"})
    u1_again = video._upload_cached(img, cache, acct="A", env={"HOME": "/a"})
    assert u1 != u2                       # 계정이 다르면 따로 올린다
    assert u1_again == u1                 # 같은 계정은 캐시를 쓴다
    assert len(uploads) == 2
    assert all(k.split("|", 1)[0] in ("A", "B") for k in cache)


def test_generate_uploads_with_the_generation_account(tmp_path, monkeypatch):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "s.png").write_bytes(b"x")

    picked_env = {"HOME": "/home/acct1", "MARK": "acct1"}
    monkeypatch.setattr(video, "cli", lambda: "hf")
    monkeypatch.setattr(video, "_account_env", lambda need=None: (picked_env, "acct1"))

    upload_envs = []
    monkeypatch.setattr(video, "upload",
                        lambda p, env=None, **kw: upload_envs.append(env) or "uid-1")

    run_envs = []

    def fake_run(cmd, env=None, **kw):
        run_envs.append(env)
        return SimpleNamespace(returncode=0,
                               stdout='{"result": {"url": "https://x/out.mp4"}}',
                               stderr="")

    monkeypatch.setattr(video.subprocess, "run", fake_run)

    res = video.generate(tmp_path, "minimax_h3", {"prompt": "p", "duration": 5},
                         images={"start_image": ["images/s.png"]})
    assert res["status"] == "completed"
    # 업로드와 생성이 같은 계정 env 를 쓴다 — 이것이 어긋나면 UUID 를 못 찾는다
    assert upload_envs and all(e is picked_env for e in upload_envs)
    assert run_envs and all(e is picked_env for e in run_envs)


def test_upload_default_env_is_plain_environ(monkeypatch, tmp_path):
    """env 를 안 주면 계정을 고르지 않고 현재 환경 그대로 — layer_edit 처럼
    생성도 기본 계정으로 도는 호출부와 어긋나지 않게."""
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    seen = {}

    def fake_run(cmd, env=None, **kw):
        seen["env"] = env
        return SimpleNamespace(returncode=0, stdout='{"id": "u"}', stderr="")

    monkeypatch.setattr(video, "cli", lambda: "hf")
    monkeypatch.setattr(video.subprocess, "run", fake_run)
    # _account_env 가 불리면 실패해야 한다 — 계정 선택은 호출부 몫
    monkeypatch.setattr(video, "_account_env",
                        lambda need=None: pytest.fail("upload 이 계정을 스스로 고르면 안 된다"))
    assert video.upload(img) == "u"
    assert "HOME" in (seen["env"] or {})
