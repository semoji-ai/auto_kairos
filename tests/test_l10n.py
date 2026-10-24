import json
from sg.l10n import update_entries


def test_update_keeps_changes_written_by_another_process(tmp_path):
    p = tmp_path / "zh.json"
    p.write_text(json.dumps({"segments": {"n1": {"text": "旧"}}, "raster": {}}))
    # 다른 프로세스(TTS 재번역)가 그 사이 segments를 고침
    d = json.loads(p.read_text()); d["segments"]["n1"]["text"] = "新"; p.write_text(json.dumps(d))
    # 이쪽(그림 문구 번역)은 raster만 갱신
    update_entries(str(p), "raster", {"a#0": {"text": "会费"}})
    d = json.loads(p.read_text())
    assert d["segments"]["n1"]["text"] == "新" and d["raster"]["a#0"]["text"] == "会费"
