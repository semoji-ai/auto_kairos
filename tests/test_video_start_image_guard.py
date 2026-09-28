"""비디오 생성에 **첫 프레임이 반드시 붙는지** 지킨다.

씬 이미지가 있는 씬을 첨부 없이 돌리면 모델이 장면을 지어낸다. 크레딧은
그대로 나가고 결과는 씬과 무관한 그림이 되는데, 예전 코드는 경로가 틀려도
`continue` 로 조용히 넘어가 **로그에 아무 말이 없었다.**

    images={"start_image": ["generated/scene_092_v5.png"]}   ← 틀린 경로
    실제                  images/generated/scene_092_v5.png

이 한 글자 차이로 세 편이 첫 프레임 없이 생성됐고 68크레딧을 날렸다.
그 뒤로 `generate()` 는 셋 중 하나라도 걸리면 **돌리기 전에 실패**한다.

    · 파일이 없다
    · 프로젝트 밖을 가리킨다
    · 넘겼는데 하나도 안 붙었다(슬롯 이름 오타)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "adobe")):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture()
def vid(monkeypatch, tmp_path):
    from adobe.backend import video as v
    # CLI 와 모델 스펙은 있다고 치고, 첨부 검사만 본다
    monkeypatch.setattr(v, "cli", lambda: "/bin/echo")
    monkeypatch.setattr(v, "load_specs", lambda: [
        {"job_type": "minimax_h3",
         "image_slots": ["start_image", "end_image", "image_references"],
         "params": [{"name": "duration", "type": "integer"}]}])
    monkeypatch.setattr(v, "_upload_cached", lambda fp, cache, **kw: "uuid-ok")
    return v


PARAMS = {"prompt": "동작 서술", "duration": 6}


def test_없는_경로는_돌리기_전에_실패한다(vid, tmp_path):
    r = vid.generate(tmp_path, "minimax_h3", PARAMS,
                     images={"start_image": ["generated/scene_092_v5.png"]})
    assert r["status"] == "failed"
    assert "찾지 못했습니다" in r["error"]
    # 어디가 틀렸는지 알려 줘야 고칠 수 있다
    assert "images/generated" in r["error"]


def test_프로젝트_밖_경로도_실패한다(vid, tmp_path, monkeypatch):
    outside = tmp_path.parent / "밖.png"
    outside.write_bytes(b"x")
    r = vid.generate(tmp_path, "minimax_h3", PARAMS,
                     images={"start_image": [f"../{outside.name}"]})
    assert r["status"] == "failed"
    assert "프로젝트 밖" in r["error"]


def test_슬롯_이름이_틀리면_빈손_생성을_막는다(vid, tmp_path):
    f = tmp_path / "images" / "generated"
    f.mkdir(parents=True)
    (f / "scene_092_v5.png").write_bytes(b"x")
    r = vid.generate(tmp_path, "minimax_h3", PARAMS,
                     images={"start-image": ["images/generated/scene_092_v5.png"]})
    assert r["status"] == "failed"
    assert "하나도 붙지 않았습니다" in r["error"]


def test_바른_경로는_통과한다(vid, tmp_path, monkeypatch):
    f = tmp_path / "images" / "generated"
    f.mkdir(parents=True)
    (f / "scene_092_v5.png").write_bytes(b"x")
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        class R:
            returncode, stdout, stderr = 0, "{}", ""
        return R()

    monkeypatch.setattr(vid.subprocess, "run", fake_run)
    vid.generate(tmp_path, "minimax_h3", PARAMS,
                 images={"start_image": ["images/generated/scene_092_v5.png"]})
    assert "--start-image" in seen["cmd"], "첫 프레임이 명령에 실려야 한다"
    assert "uuid-ok" in seen["cmd"]
