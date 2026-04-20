"""
기존 프로젝트 데이터를 새 DB 시스템으로 마이그레이션.

실행: python -m db.migrate_existing
"""
import json
import re
import shutil
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from auto_agent.db.connection import init_db, db_exists, get_db_path, PROJECT_ROOT
from auto_agent.db.project_manager import ProjectManager


def scan_scene_number(filename: str):
    """파일명에서 씬 번호 추출. scene_003.mp3 → 3"""
    m = re.search(r"scene_(\d+)", filename)
    return int(m.group(1)) if m else None


def migrate_project(pm: ProjectManager, slug: str, name: str) -> int:
    """단일 프로젝트 마이그레이션. project_id 반환."""
    output_dir = PROJECT_ROOT / "output" / slug

    if not output_dir.exists():
        print(f"  [SKIP] {output_dir} does not exist")
        return -1

    # 이미 등록된 프로젝트인지 확인
    existing = pm.get_project(slug=slug)
    if existing:
        print(f"  [SKIP] Project '{slug}' already exists (id={existing['id']})")
        return existing["id"]

    # scene_specs에서 topic 추출
    topic = None
    scene_count = 0

    # 루트 scene_specs가 최신일 수 있으므로 먼저 확인
    root_specs = PROJECT_ROOT / "scene_specs.json"
    output_specs = output_dir / "scene_specs.json"

    # 최신 scene_specs 결정 (루트 > output 디렉토리)
    canonical_specs = None
    if root_specs.exists():
        canonical_specs = root_specs
    elif output_specs.exists():
        canonical_specs = output_specs

    if canonical_specs:
        with open(canonical_specs, "r", encoding="utf-8") as f:
            data = json.load(f)
        topic = data.get("topic", "")
        scene_count = data.get("total_scenes", len(data.get("scenes", [])))

    # 1. 프로젝트 생성
    project_id = pm.create_project(
        name=name, slug=slug, topic=topic, theme="simple"
    )
    pm.update_project(project_id, scene_count=scene_count, status="completed")
    print(f"  [OK] Project created: id={project_id}, slug={slug}")

    # 2. 루트 JSON을 프로젝트 디렉토리로 이동/복사
    versions_dir = output_dir / "versions"
    versions_dir.mkdir(exist_ok=True)

    root_files = {
        "scene_specs": ("scene_specs.json", "scene_specs"),
        "motion_plan": ("motion_plan.json", "motion_plan"),
        "scene_decomposition": ("scene_decomposition.json", "scene_decomposition"),
        "manuscript": ("final_manuscript.md", "manuscript"),
    }

    for key, (filename, file_type) in root_files.items():
        root_path = PROJECT_ROOT / filename
        dest_path = output_dir / filename

        if root_path.exists():
            # 루트 → output 디렉토리로 복사 (최신 버전)
            shutil.copy2(root_path, dest_path)
            print(f"  [COPY] {filename}: root → output/{slug}/")

            # v001으로 버전 등록
            pm.save_version(
                project_id, file_type, dest_path,
                description="Initial migration from root",
                created_by="migration",
            )
            print(f"  [VER] {file_type} v001 registered")
        elif dest_path.exists():
            # output에만 있는 경우 (이미 제자리)
            pm.save_version(
                project_id, file_type, dest_path,
                description="Existing file in output dir",
                created_by="migration",
            )
            print(f"  [VER] {file_type} v001 (from output dir)")

    # 3. 백업 파일들을 versions/로 이동 + 등록
    backup_patterns = [
        (PROJECT_ROOT / "scene_specs.json.bak.1772502558", "scene_specs", "Pre-v4.0 backup"),
        (PROJECT_ROOT / "scene_specs_creative_backup.json", "scene_specs", "Creative direction backup"),
        (PROJECT_ROOT / "scene_specs_v4.0_backup.json", "scene_specs", "v4.0 initial backup"),
        (PROJECT_ROOT / "motion_plan.json.bak.1772502558", "motion_plan", "Pre-v4.0 backup"),
        (output_dir / "scene_specs_v5.json", "scene_specs", "v5 variant"),
        (output_dir / "iran_war_2026_scene_specs.json", "scene_specs", "Iran war specific specs"),
    ]

    for src_path, file_type, description in backup_patterns:
        if src_path.exists():
            pm.save_version(
                project_id, file_type, src_path,
                description=description,
                created_by="migration",
            )
            print(f"  [VER] {file_type} backup: {src_path.name}")

    # 4. 오디오 에셋 등록
    audio_dir = output_dir / "audio"
    if audio_dir.exists():
        audio_count = 0
        for f in sorted(audio_dir.glob("*.mp3")):
            scene_num = scan_scene_number(f.name)
            pm.register_asset(
                project_id, "audio", str(f),
                scene_number=scene_num,
                metadata={"format": "mp3"},
            )
            audio_count += 1
        print(f"  [ASSET] {audio_count} audio files registered")

    # 5. 이미지 에셋 등록
    image_dir = output_dir / "images"
    if image_dir.exists():
        image_count = 0
        for f in sorted(image_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                scene_num = scan_scene_number(f.name)
                pm.register_asset(
                    project_id, "image", str(f),
                    scene_number=scene_num,
                )
                image_count += 1

        # viz_bg 서브디렉토리
        viz_bg_dir = image_dir / "viz_bg"
        if viz_bg_dir.exists():
            for f in sorted(viz_bg_dir.glob("*")):
                if f.is_file():
                    scene_num = scan_scene_number(f.name)
                    pm.register_asset(
                        project_id, "viz_bg", str(f),
                        scene_number=scene_num,
                    )
                    image_count += 1
        print(f"  [ASSET] {image_count} image files registered")

    # 6. 캐릭터 이미지
    char_dir = output_dir / "characters"
    if char_dir.exists():
        char_count = 0
        for f in char_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                pm.register_asset(project_id, "character", str(f))
                char_count += 1
        if char_count:
            print(f"  [ASSET] {char_count} character images registered")

    # 7. 자막 에셋 등록
    subtitle_dir = output_dir / "subtitles"
    if subtitle_dir.exists():
        sub_count = 0
        for f in sorted(subtitle_dir.glob("*.srt")):
            scene_num = scan_scene_number(f.name)
            pm.register_asset(
                project_id, "subtitle", str(f),
                scene_number=scene_num,
            )
            sub_count += 1
        print(f"  [ASSET] {sub_count} subtitle files registered")

    # 8. JSON 메타데이터 에셋 등록
    json_assets = [
        "subtitles.json", "tts_results.json", "tts_mapping.json",
        "image_gen_results.json", "image_licenses.json",
    ]
    for jf in json_assets:
        jp = output_dir / jf
        if jp.exists():
            pm.register_asset(project_id, "json", str(jp))

    # 9. 라이선스 정보 마이그레이션
    license_path = output_dir / "image_licenses.json"
    if license_path.exists():
        with open(license_path, "r", encoding="utf-8") as f:
            licenses = json.load(f)

        if isinstance(licenses, list):
            lic_count = 0
            for lic in licenses:
                scene_str = lic.get("scene", "")
                scene_num = scan_scene_number(scene_str)
                # 대응하는 에셋 찾기
                assets = pm.get_assets(project_id, asset_type="image", scene_number=scene_num)
                if assets:
                    pm.register_license(
                        asset_id=assets[0]["id"],
                        source=lic.get("source", "unknown"),
                        source_url=lic.get("source_url"),
                        license_type=lic.get("license"),
                        title=lic.get("title"),
                    )
                    lic_count += 1
            print(f"  [LICENSE] {lic_count} licenses registered")

    # 10. manifest를 manifests/ 디렉토리에 복사
    manifest_src = PROJECT_ROOT / "remotion" / "public" / "manifest.json"
    manifest_dest = PROJECT_ROOT / "remotion" / "public" / "manifests" / f"{slug}.json"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)

    if manifest_src.exists():
        shutil.copy2(manifest_src, manifest_dest)
        print(f"  [MANIFEST] Copied to manifests/{slug}.json")

    # iran_war 전용 매니페스트도 복사
    iran_manifest = PROJECT_ROOT / "remotion" / "public" / "iran_war_2026_manifest.json"
    if iran_manifest.exists():
        shutil.copy2(iran_manifest, manifest_dest)
        print(f"  [MANIFEST] Iran war manifest → manifests/{slug}.json")

    return project_id


def cleanup_root_files():
    """마이그레이션 후 루트 파일 정리 (안전하게)."""
    files_to_remove = [
        "scene_specs.json.bak.1772502558",
        "scene_specs_creative_backup.json",
        "scene_specs_v4.0_backup.json",
        "motion_plan.json.bak.1772502558",
    ]

    removed = []
    for filename in files_to_remove:
        fp = PROJECT_ROOT / filename
        if fp.exists():
            fp.unlink()
            removed.append(filename)

    if removed:
        print(f"\n  [CLEANUP] Removed {len(removed)} root backup files:")
        for f in removed:
            print(f"    - {f}")

    # 루트 JSON은 심볼릭 링크로 남겨둘 수도 있지만,
    # 레거시 호환을 위해 일단 유지 (향후 수동 삭제 권장)
    legacy_files = [
        "scene_specs.json", "motion_plan.json",
        "scene_decomposition.json", "final_manuscript.md",
    ]
    print("\n  [INFO] 다음 루트 파일은 레거시 호환을 위해 유지됨 (수동 삭제 가능):")
    for f in legacy_files:
        fp = PROJECT_ROOT / f
        if fp.exists():
            print(f"    - {f} ({fp.stat().st_size:,} bytes)")


def main():
    print("=" * 60)
    print("auto_agent_v2 데이터 마이그레이션")
    print("=" * 60)

    # DB 초기화
    db_path = init_db()
    print(f"\n[DB] Initialized: {db_path}")

    pm = ProjectManager()

    # 기존 프로젝트 마이그레이션
    print(f"\n[MIGRATE] 미국_이란_전쟁_2026")
    project_id = migrate_project(
        pm,
        slug="미국_이란_전쟁_2026",
        name="미국 이란 전쟁 2026",
    )

    if project_id > 0:
        # 루트 백업 파일 정리
        cleanup_root_files()

        # 결과 요약
        print("\n" + "=" * 60)
        print("마이그레이션 완료 요약")
        print("=" * 60)

        project = pm.get_project(project_id=project_id)
        assets = pm.get_asset_counts(project_id)
        versions = {}
        for ft in ["scene_specs", "motion_plan", "scene_decomposition", "manuscript"]:
            v = pm.get_versions(project_id, ft)
            if v:
                versions[ft] = len(v)

        print(f"\n  프로젝트: {project['name']}")
        print(f"  슬러그: {project['slug']}")
        print(f"  토픽: {project['topic']}")
        print(f"  씬 수: {project['scene_count']}")
        print(f"  상태: {project['status']}")
        print(f"\n  에셋:")
        for atype, count in sorted(assets.items()):
            print(f"    {atype}: {count}개")
        print(f"\n  버전:")
        for ft, count in sorted(versions.items()):
            print(f"    {ft}: {count}개 버전")
        print(f"\n  DB 경로: {db_path}")
        print(f"  DB 크기: {db_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
