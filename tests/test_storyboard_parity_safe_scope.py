import json
from pathlib import Path

from fastapi.testclient import TestClient

import app as dashboard_app
from auto_agent.dashboard.helpers import enrich_scenes_with_media


def test_enrich_scenes_uses_manifest_layout_when_available(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    manifest_dir = workspace / "remotion" / "public" / "manifests"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "abcd1234_demo.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest": {
                    "scenes": [
                        {"sceneNumber": 1, "layout": "quote_portrait"},
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("auto_agent.paths.get_workspace_dir", lambda: workspace)

    output_dir = tmp_path / "output" / "abcd1234_demo"
    output_dir.mkdir(parents=True)

    scenes = [
        {
            "sceneNumber": 1,
            "chapter": 1,
            "title": "인용문 씬",
            "narration": "본문",
            "visualization": {"creative": {"layout": "headline_only"}},
            "items": ["인용문"],
        }
    ]

    enriched = enrich_scenes_with_media(scenes, "abcd1234_demo", str(output_dir))

    assert enriched[0]["_layout"] == "quote_portrait"
    assert enriched[0]["_layout_explicit"] is True


def test_art_style_post_provisions_and_rebuilds_manifest(tmp_path, monkeypatch):
    output_dir = tmp_path / "output" / "abcd1234_demo"
    output_dir.mkdir(parents=True)
    canonical_dir = tmp_path / "data" / "artstyle" / "styles"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "semoji.json").write_text(
        json.dumps({"name": "세모지", "reference_image": "semoji_base.jpg"}, ensure_ascii=False),
        encoding="utf-8",
    )

    calls = []

    class FakePM:
        def __init__(self):
            self.config = {"art_style": "artstyle/styles/quirky_cartoon.json"}
            self.project = {"id": 7, "slug": "demo", "output_dir": str(output_dir)}

        def get_project(self, slug=None, project_id=None):
            if slug == "demo":
                return self.project
            if project_id == 7:
                return self.project
            return None

        def get_config(self, project_id):
            assert project_id == 7
            return dict(self.config)

        def set_config(self, project_id, config):
            assert project_id == 7
            self.config = dict(config)
            calls.append(("set_config", config["art_style"]))

        def provision_art_style(self, project_id):
            assert project_id == 7
            calls.append(("provision", project_id))
            local_style = output_dir / "art_style.json"
            local_style.write_text(json.dumps({"name": "세모지"}, ensure_ascii=False), encoding="utf-8")
            return str(local_style)

    fake_pm = FakePM()

    monkeypatch.setattr(dashboard_app, "get_pm", lambda: fake_pm)
    monkeypatch.setattr(dashboard_app, "_setup_studio_project", lambda slug: calls.append(("setup", slug)))
    monkeypatch.setattr(dashboard_app, "get_data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr("auto_agent.db.project_manager.resolve_art_style_path", lambda art_style, project_dir=None: canonical_dir / Path(art_style).name)
    monkeypatch.setattr("auto_agent.scripts.build_manifest.build_manifest", lambda project_id, dir_name, project_dir=None: calls.append(("build_manifest", project_id, dir_name, project_dir)))

    client = TestClient(dashboard_app.app)
    response = client.post("/api/p/demo/art-style", json={"art_style": "artstyle/styles/semoji.json"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert fake_pm.config["art_style"] == "artstyle/styles/semoji.json"
    assert ("set_config", "artstyle/styles/semoji.json") in calls
    assert ("provision", 7) in calls
    assert ("setup", "demo") in calls
    assert any(call[0] == "build_manifest" for call in calls)
