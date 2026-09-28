import json

from auto_agent.scripts import build_manifest as manifest_module


def test_selected_image_in_nested_folder_reaches_remotion_manifest(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    project = workspace / "output" / "midea"
    image = project / "images" / "production_v11" / "no_people" / "S151_np_v2.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    (project / "images" / "image_assets.json").write_text(
        json.dumps(
            {
                "scenes": [
                    {
                        "sceneNumber": 151,
                        "images": [
                            {"file": "production_v11/no_people/S151_np_v2.png", "selected": True}
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    scene = {
        "sceneNumber": 151,
        "sceneId": "scene-151",
        "narration": "도시바가 무엇을 만들지 줬다면",
        "layout": "cinematic",
        "motion": "fade_rise",
        "visual_kind": "generate_image",
        "imageAsset": {
            "source": "generate",
            "placement": "fullscreen",
            "localPath": "images/production_v11/no_people/S151_np_v2.png",
        },
    }
    monkeypatch.setattr(manifest_module, "get_workspace_dir", lambda: workspace)
    monkeypatch.setattr(manifest_module, "load_scene_specs", lambda _: {"scenes": [scene]})
    monkeypatch.setattr(manifest_module, "_load_project_config", lambda *_: {})

    path = manifest_module.build_manifest("midea", "midea", project_dir=str(project))
    result = json.loads(path.read_text(encoding="utf-8"))

    assert result["manifest"]["scenes"][0]["imagePath"] == (
        "project/images/production_v11/no_people/S151_np_v2.png"
    )
