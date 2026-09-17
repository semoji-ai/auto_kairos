"""산출물이 커밋에 섞여 들어가지 않게 막는다.

## 왜 필요한가

`adobe/projects/_archive` 2.9GB(1,802 파일)가 통째로 커밋돼 있었다. 원인은
`adobe/.gitignore` 의 패턴이 **깊이 하나만** 맞기 때문이다.

    projects/*/images/          → projects/7184ea44/images/        잡힘
                                → projects/_archive/<편>/images/   **안 잡힘**

무시 규칙만 고치면 다음에 또 다른 깊이가 생겼을 때 같은 일이 난다. 그래서
관문을 하나 더 둔다 — 커밋에 들어온 것 중 산출물처럼 보이는 게 있으면 막는다.
"""
from __future__ import annotations

import subprocess

import pytest

from auto_agent.scripts.check_no_artifacts import (
    ARTIFACT_SUFFIXES,
    find_artifacts,
)


class TestIgnoreCoversAnyDepth:
    """무시 규칙이 깊이에 상관없이 잡아야 한다."""

    @pytest.mark.parametrize("path", [
        "adobe/projects/7184ea44/images/x.png",
        "adobe/projects/_archive/3a016021/images/x.png",
        "adobe/projects/_archive/깊게/더깊게/storyboard/x.png",
        "adobe/projects/7184ea44/audio/x.mp3",
        "adobe/projects/_archive/3a016021/audio/x.mp3",
        "adobe/projects/_archive/3a016021/layers/x.svg",
    ])
    def test_project_artifacts_are_ignored(self, path):
        r = subprocess.run(["git", "check-ignore", "-q", path],
                           capture_output=True, cwd=".")
        assert r.returncode == 0, f"무시되지 않는다: {path}"

    @pytest.mark.parametrize("path", [
        "adobe/projects/7184ea44/plan.md",
        "adobe/projects/tesla/final_manuscript.md",
        "adobe/projects/7184ea44/ARCHIVED.json",
    ])
    def test_small_text_records_stay_tracked(self, path):
        """원고·기획·표석은 계속 추적한다 — 이건 산출물이 아니라 기록이다."""
        r = subprocess.run(["git", "check-ignore", "-q", path],
                           capture_output=True, cwd=".")
        assert r.returncode != 0, f"기록인데 무시된다: {path}"


class TestGuardFindsArtifacts:
    def test_flags_binary_under_project_dir(self):
        staged = [
            "adobe/projects/_archive/3a016021/images/a.png",
            "output/f772e15c_x/audio/b.mp3",
            "auto_agent/orchestrator/runner.py",
        ]
        found = find_artifacts(staged)
        assert set(found) == {
            "adobe/projects/_archive/3a016021/images/a.png",
            "output/f772e15c_x/audio/b.mp3",
        }

    def test_allows_repo_assets_outside_project_dirs(self):
        """저장소 자산은 산출물이 아니다 — 아트스타일 기준 시트, 폰트, 테스트 케이스."""
        staged = [
            "auto_agent/data/artstyle/styles/semoji_character_sheet.png",
            "remotion/public/fonts/BMYeonsung.ttf",
            "chartagent_dashboard/cases/x.png",
            "app/src-tauri/icons/icon.png",
        ]
        assert find_artifacts(staged) == []

    def test_allows_text_under_project_dir(self):
        staged = [
            "adobe/projects/tesla/plan.md",
            "adobe/projects/7184ea44/ARCHIVED.json",
        ]
        assert find_artifacts(staged) == []

    def test_suffix_list_covers_the_usual_outputs(self):
        for s in (".png", ".jpg", ".mp3", ".wav", ".mp4", ".mov", ".svg"):
            assert s in ARTIFACT_SUFFIXES


class TestKoreanPathsAreNotSkipped:
    """git 은 비ASCII 경로를 따옴표 + 8진 이스케이프로 내놓는다.

        "adobe/projects/\\354\\213\\234\\355\\227\\230\\355\\216\\270/images/x.png"

    이걸 그대로 받으면 `"` 로 시작해 접두 검사가 전부 빗나간다. **이 저장소의
    프로젝트는 전부 한글 이름**이라(f772e15c_디아지오_…) 그러면 관문이 아무것도
    막지 못한다. 스테이징 목록은 -z 로 받아 따옴표를 아예 만들지 않는다.
    """

    def test_staged_list_has_no_quoted_paths(self, tmp_path):
        import subprocess
        from auto_agent.scripts.check_no_artifacts import _staged

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        d = tmp_path / "adobe" / "projects" / "한글편" / "images"
        d.mkdir(parents=True)
        (d / "x.png").write_bytes(b"\x89PNG" + b"a" * 100)
        subprocess.run(["git", "add", "-Af"], cwd=tmp_path, check=True)

        staged = _staged(tmp_path)
        assert staged, "스테이징 목록이 비었다"
        for p in staged:
            assert not p.startswith('"'), f"따옴표가 벗겨지지 않았다: {p}"
        assert "adobe/projects/한글편/images/x.png" in staged

    def test_korean_project_artifact_is_flagged(self):
        from auto_agent.scripts.check_no_artifacts import find_artifacts
        p = "output/f772e15c_디아지오_싱글몰트_브랜드백과사전/images/scene_1.png"
        assert find_artifacts([p]) == [p]
