"""
Preflight Check -- 환경 의존성 검증

pipeline.json phase_0 step_0: API 키, node, ffmpeg, Remotion, Lucide 검증
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from auto_agent.scripts.project_paths import PROJECT_ROOT


def check_env_var(name: str, required: bool = True) -> bool:
    val = os.getenv(name)
    if val:
        print(f"  [OK] {name}")
        return True
    if required:
        print(f"  [FAIL] {name} -- 미설정")
        return False
    print(f"  [SKIP] {name} -- 선택적 (미설정)")
    return True


def check_command(name: str, version_flag: str = "--version") -> bool:
    path = shutil.which(name)
    if not path:
        print(f"  [FAIL] {name} -- 설치되지 않음")
        return False
    try:
        result = subprocess.run(
            [name, version_flag],
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        version = result.stdout.strip().split("\n")[0] or result.stderr.strip().split("\n")[0]
        print(f"  [OK] {name} -- {version}")
        return True
    except Exception as e:
        print(f"  [WARN] {name} -- 경로 확인됨 ({path}), 버전 확인 실패: {e}")
        return True


def check_node_version() -> bool:
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        version = result.stdout.strip()
        major = int(version.lstrip("v").split(".")[0])
        if major >= 18:
            print(f"  [OK] node {version}")
            return True
        print(f"  [FAIL] node {version} -- v18+ 필요")
        return False
    except Exception:
        print("  [FAIL] node -- 설치되지 않음")
        return False


def _ensure_remotion_setup() -> bool:
    """remotion/ 디렉토리에 package.json과 node_modules 검증. 누락 시 자동 복구."""
    remotion_dir = PROJECT_ROOT / "remotion"

    # 1) package.json 누락 → 템플릿에서 복사
    pkg_json = remotion_dir / "package.json"
    if not pkg_json.exists():
        template_dir = Path(__file__).resolve().parent.parent / "remotion_template"
        if template_dir.exists():
            print("  [AUTO] remotion/ 누락 -- 템플릿에서 복사 중...")
            import shutil as _sh
            if remotion_dir.exists():
                _sh.rmtree(remotion_dir)
            _sh.copytree(template_dir, remotion_dir)
            print("  [AUTO] remotion/ 템플릿 복사 완료")
        else:
            print("  [FAIL] remotion/package.json 없음 + 템플릿도 없음")
            return False

    # 2) node_modules 누락 → npm install
    if not (remotion_dir / "node_modules").exists():
        print("  [AUTO] node_modules 누락 -- npm install 실행 중...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(remotion_dir),
                capture_output=True, text=True, encoding="utf-8",
                timeout=120,
            )
            if result.returncode == 0:
                print("  [AUTO] npm install 완료")
            else:
                print(f"  [FAIL] npm install 실패: {result.stderr[:200]}")
                return False
        except Exception as e:
            print(f"  [FAIL] npm install 실행 오류: {e}")
            return False

    return True


def check_preset(project_dir_str: str) -> bool:
    """art style preset validation."""
    from pathlib import Path
    project_dir = Path(project_dir_str)
    art_style_path = project_dir / "art_style.json"
    if not art_style_path.exists():
        print("  [WARN] art_style.json -- not found in project dir (will be provisioned)")
        return True  # provision stage will copy it
    try:
        from auto_agent.data.artstyle.preset_schema import load_preset, validate_preset
        preset = load_preset(art_style_path)
        errors = validate_preset(preset)
        if errors:
            for e in errors:
                print(f"  [FAIL] preset -- {e}")
            return False
        print("  [OK] preset -- validation passed")
        return True
    except Exception as e:
        print(f"  [WARN] preset -- validation error: {e}")
        return True  # legacy format passes


def check_npm_package(name: str) -> bool:
    remotion_dir = PROJECT_ROOT / "remotion"
    node_modules = remotion_dir / "node_modules" / name
    if node_modules.exists():
        print(f"  [OK] {name}")
        return True
    print(f"  [FAIL] {name} -- remotion/node_modules에 없음")
    return False


def main():
    print("Preflight Check")
    print("=" * 40)
    errors = 0

    # 1. API 키
    print("\n[API Keys]")
    check_env_var("ANTHROPIC_API_KEY", required=False)  # Claude Code 구독제 사용 시 불필요
    if not check_env_var("ELEVENLABS_API_KEY"):
        errors += 1
    check_env_var("OPENAI_API_KEY", required=False)
    check_env_var("FAL_API_KEY", required=False)
    check_env_var("SERPER_API_KEY", required=False)
    check_env_var("GOOGLE_API_KEY", required=False)

    # 2. CLI 도구
    print("\n[CLI Tools]")
    if not check_node_version():
        errors += 1
    if not check_command("ffmpeg"):
        errors += 1
    check_command("npx")

    # 3. Remotion 초기화 검증 + NPM 패키지
    print("\n[Remotion Setup]")
    if not _ensure_remotion_setup():
        errors += 1
    print("\n[NPM Packages]")
    check_npm_package("@remotion/cli")
    check_npm_package("lucide-react")

    # 4. Python 패키지
    print("\n[Python Packages]")
    required_packages = ["requests", "fal_client", "dotenv"]
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [WARN] {pkg} -- 미설치")

    # 5. 폰트 파일 검증 (누락 시 FontAgent로 자동 설치 시도)
    print("\n[Fonts]")
    fonts_dir = PROJECT_ROOT / "remotion" / "public" / "fonts"
    required_fonts = [
        ("GyeonggiMillenniumBatang-Regular.ttf", "gongu-13288410", "경기천년바탕_Regular.ttf"),
        ("GyeonggiMillenniumBatang-Bold.ttf", "gongu-13288409", "경기천년바탕_Bold.ttf"),
    ]
    for dst_name, font_id, src_name in required_fonts:
        target = fonts_dir / dst_name
        if target.exists():
            print(f"  [OK] {dst_name}")
            continue
        # FontAgent로 자동 설치 시도
        try:
            import tempfile
            import shutil as _sh
            from fontagent.cli import run_install  # type: ignore
            tmp = Path(tempfile.mkdtemp())
            run_install(font_id, str(tmp))
            src = tmp / src_name
            if src.exists():
                fonts_dir.mkdir(parents=True, exist_ok=True)
                _sh.copy(src, target)
                # remotion_template 동기화
                tmpl = PROJECT_ROOT / "auto_agent" / "remotion_template" / "public" / "fonts" / dst_name
                if not tmpl.exists():
                    _sh.copy(target, tmpl)
                print(f"  [AUTO] {dst_name} -- FontAgent로 설치 완료")
            else:
                raise FileNotFoundError(src)
            _sh.rmtree(tmp, ignore_errors=True)
        except Exception:
            # CLI fallback
            try:
                import tempfile, shutil as _sh
                tmp = Path(tempfile.mkdtemp())
                result = subprocess.run(
                    [sys.executable, "-m", "fontagent.cli", "install", font_id, "--output-dir", str(tmp)],
                    capture_output=True, text=True, timeout=60,
                )
                src = tmp / src_name
                if result.returncode == 0 and src.exists():
                    fonts_dir.mkdir(parents=True, exist_ok=True)
                    _sh.copy(src, target)
                    tmpl = PROJECT_ROOT / "auto_agent" / "remotion_template" / "public" / "fonts" / dst_name
                    if not tmpl.exists():
                        _sh.copy(target, tmpl)
                    print(f"  [AUTO] {dst_name} -- FontAgent CLI로 설치 완료")
                else:
                    print(f"  [WARN] {dst_name} -- 누락됨. 설치: bash scripts/setup_fonts.sh")
                _sh.rmtree(tmp, ignore_errors=True)
            except Exception as e2:
                print(f"  [WARN] {dst_name} -- 누락됨. 설치: bash scripts/setup_fonts.sh ({e2})")

    # 6. Preset validation (if project dir is known)
    print("\n[Preset Validation]")
    project_dir = os.getenv("AUTO_AGENT_PROJECT_DIR", "")
    if project_dir:
        if not check_preset(project_dir):
            errors += 1
    else:
        print("  [SKIP] AUTO_AGENT_PROJECT_DIR not set")

    # 6. Project config 필수값 검증 — 인터뷰에서 설정되어야 할 항목들
    print("\n[Project Config — 사전 인터뷰 결과]")
    project_slug = os.getenv("PROJECT_NAME", "")
    if project_slug:
        try:
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            proj = pm.get_project(slug=project_slug)
            cfg = pm.get_config(proj["id"]) if proj else {}
            required_cfg = {
                "art_style": "아트스타일 (사전 인터뷰 A단계)",
                "writing_style": "문체 (사전 인터뷰 A단계)",
            }
            optional_cfg = {
                "voice_id": "보이스 ID",
                "duration_minutes": "영상 분량",
                "video_theme": "테마(dark/light)",
            }
            for key, label in required_cfg.items():
                if cfg.get(key):
                    print(f"  [OK] {key} = {cfg[key]}")
                else:
                    print(f"  [FAIL] {key} 미설정 — {label}이 누락됐습니다. 사전 인터뷰를 완료하세요.")
                    errors += 1
            for key, label in optional_cfg.items():
                val = cfg.get(key)
                if val:
                    print(f"  [OK] {key} = {val}")
                else:
                    print(f"  [WARN] {key} 미설정 — {label} (선택적)")
            # editorial_brief.json 존재 확인
            if proj and proj.get("output_dir"):
                brief_path = Path(proj["output_dir"]) / "editorial_brief.json"
                if brief_path.exists():
                    print("  [OK] editorial_brief.json — 기획 의도 고정됨")
                else:
                    print("  [WARN] editorial_brief.json 없음 — 사전 인터뷰 B단계(기획 인터뷰)를 완료하세요")
        except Exception as e:
            print(f"  [WARN] config 검증 오류: {e}")
    else:
        print("  [SKIP] PROJECT_NAME not set")

    print(f"\n{'=' * 40}")
    if errors:
        print(f"FAIL: {errors}개 필수 항목 미충족")
        sys.exit(1)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    main()
