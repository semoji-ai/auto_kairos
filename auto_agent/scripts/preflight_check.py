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

    # 3. NPM 패키지
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

    print(f"\n{'=' * 40}")
    if errors:
        print(f"FAIL: {errors}개 필수 항목 미충족")
        sys.exit(1)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    main()
