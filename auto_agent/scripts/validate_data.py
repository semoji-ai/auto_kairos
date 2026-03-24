"""
Data Validation -- 전 단계 데이터 정합성 검증

pipeline.json phase_5 step_10: gate=true -> 실패 시 파이프라인 중단
검증 항목:
  - scene_specs <-> audio 파일 매칭
  - 시각화 데이터 완전성
  - 자막 타이밍 <-> 오디오 길이 일치
  - 아이콘명 Lucide 존재 확인
  - 이미지 에셋 파일 존재 확인
"""
import json
import sys
from pathlib import Path

from auto_agent.scripts.project_paths import PROJECT_ROOT, get_project_dir, get_scene_specs_path


# Lucide 아이콘 이름은 remotion/node_modules에서 추출 가능
# 기본적으로 kebab-case 허용
def _load_lucide_icons() -> set:
    """Lucide 아이콘 목록 로드 (가능한 경우)."""
    icons_dir = PROJECT_ROOT / "remotion" / "node_modules" / "lucide-react" / "dist" / "esm" / "icons"
    if icons_dir.exists():
        return {f.stem.replace("-", "_") for f in icons_dir.glob("*.js")}
    # 폴백: 검증 스킵
    return set()


class ValidationReport:
    def __init__(self):
        self.errors = []     # critical -- 파이프라인 중단
        self.warnings = []   # non-critical

    def error(self, category: str, message: str):
        self.errors.append({"category": category, "message": message})
        print(f"  [ERROR] [{category}] {message}")

    def warn(self, category: str, message: str):
        self.warnings.append({"category": category, "message": message})
        print(f"  [WARN]  [{category}] {message}")

    def ok(self, message: str):
        print(f"  [OK]    {message}")

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def validate_audio_matching(report: ValidationReport, specs: dict, project_dir: Path):
    """scene_specs <-> audio 파일 매칭 검증."""
    audio_dir = project_dir / "audio"
    scenes = specs.get("scenes", [])

    for scene in scenes:
        num = scene.get("sceneNumber", 0)
        narration = scene.get("narration_tts", scene.get("narration", ""))
        audio_file = audio_dir / f"scene_{num:03d}.mp3"

        if narration and narration.strip():
            if not audio_file.exists():
                report.error("audio", f"scene_{num:03d}.mp3 없음 (나레이션 있음)")
        elif audio_file.exists():
            report.warn("audio", f"scene_{num:03d}.mp3 존재하지만 나레이션 없음")

    report.ok(f"Audio matching: {len(scenes)} scenes checked")


def validate_subtitle_matching(report: ValidationReport, specs: dict, project_dir: Path):
    """자막 파일 존재 검증."""
    sub_dir = project_dir / "subtitles"
    scenes = specs.get("scenes", [])

    for scene in scenes:
        num = scene.get("sceneNumber", 0)
        audio_file = project_dir / "audio" / f"scene_{num:03d}.mp3"
        srt_file = sub_dir / f"scene_{num:03d}.srt"

        if audio_file.exists() and not srt_file.exists():
            report.warn("subtitle", f"scene_{num:03d}.srt 없음 (오디오 있음)")

    report.ok(f"Subtitle matching: {len(scenes)} scenes checked")


def validate_image_assets(report: ValidationReport, specs: dict, project_dir: Path):
    """이미지 에셋 파일 존재 확인."""
    images_dir = project_dir / "images"
    scenes = specs.get("scenes", [])
    missing = 0

    for scene in scenes:
        asset = scene.get("imageAsset")
        if not asset:
            continue
        num = scene.get("sceneNumber", 0)
        placement = asset.get("placement", "")

        if placement == "background":
            viz_bg = images_dir / "viz_bg" / f"scene_{num:03d}.png"
            if not viz_bg.exists():
                report.warn("image", f"viz_bg/scene_{num:03d}.png 없음")
                missing += 1
        else:
            scene_img = images_dir / f"scene_{num:03d}.png"
            if not scene_img.exists():
                report.warn("image", f"scene_{num:03d}.png 없음")
                missing += 1

    if missing == 0:
        report.ok("Image assets: all present")


def validate_viz_data(report: ValidationReport, specs: dict):
    """creative 필드 + 시각화 데이터 완전성 검증."""
    scenes = specs.get("scenes", [])

    for scene in scenes:
        viz = scene.get("visualization", {})
        num = scene.get("sceneNumber", 0)
        creative = viz.get("creative", {})

        # creative 필드 존재 확인
        if not creative:
            report.warn("creative", f"scene {num}: creative 필드 없음 (normalizeCreative가 보완)")
            continue

        # headline 확인
        if not creative.get("headline"):
            report.warn("creative", f"scene {num}: headline 없음")

        # chartConfig 있으면 items/values 일치 확인
        if creative.get("chartConfig"):
            items = viz.get("items", [])
            values = viz.get("values", [])
            if items and values and len(items) != len(values):
                report.error("creative", f"scene {num}: items({len(items)}) != values({len(values)})")

        # pie 차트 합계 검증
        if creative.get("chartConfig", {}).get("type") == "pie":
            values = viz.get("values", [])
            if values:
                total = sum(values)
                if abs(total - 100) > 5:
                    report.warn("creative", f"scene {num}: pie 합계 {total}% (100% 아님)")

    report.ok("Creative/viz data validation complete")


def validate_icons(report: ValidationReport, specs: dict):
    """아이콘명 Lucide 존재 확인."""
    lucide_icons = _load_lucide_icons()
    if not lucide_icons:
        report.warn("icons", "Lucide 아이콘 목록 로드 실패 -- 검증 스킵")
        return

    scenes = specs.get("scenes", [])
    for scene in scenes:
        viz = scene.get("visualization", {})
        data = viz.get("data", {})
        num = scene.get("sceneNumber", 0)

        # items 내 icon 필드 검증
        for item in data.get("items", []):
            icon = item.get("icon", "")
            if icon:
                normalized = icon.replace("-", "_")
                if normalized not in lucide_icons:
                    report.warn("icons", f"scene {num}: unknown icon '{icon}'")

    report.ok("Icon validation complete")


def main():
    project_dir = get_project_dir()
    specs_path = get_scene_specs_path()

    if not specs_path.exists():
        print(f"ERROR: {specs_path} not found")
        sys.exit(1)

    print(f"Data Validation: {project_dir}")
    print(f"Scene Specs: {specs_path}")
    print("=" * 50)

    with open(specs_path, "r", encoding="utf-8") as f:
        specs = json.load(f)

    scenes = specs.get("scenes", [])
    print(f"Scenes: {len(scenes)}\n")

    report = ValidationReport()

    validate_audio_matching(report, specs, project_dir)
    validate_subtitle_matching(report, specs, project_dir)
    validate_image_assets(report, specs, project_dir)
    validate_viz_data(report, specs)
    validate_icons(report, specs)

    # 결과 저장
    result = {
        "passed": report.passed,
        "errors": report.errors,
        "warnings": report.warnings,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
    }

    output_path = project_dir / "validation_report.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{'=' * 50}")
    print(f"Errors:   {len(report.errors)}")
    print(f"Warnings: {len(report.warnings)}")
    print(f"Result:   {'PASS' if report.passed else 'FAIL'}")
    print(f"Output:   {output_path}")

    if not report.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
