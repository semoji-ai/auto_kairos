"""
auto-agent — AI 영상 제작 파이프라인 CLI

사용법:
  auto-agent --version                          # 버전
  auto-agent init <workspace>                   # 워크스페이스 초기화
  auto-agent run --project <slug> [옵션]         # 파이프라인 실행
  auto-agent project list|create|active|info    # 프로젝트 관리
  auto-agent config get|set|set-json|delete     # 프로젝트 설정
  auto-agent studio --project <slug>            # Remotion 스튜디오
  auto-agent style list|add|remove              # 아트스타일 관리
  auto-agent voice list|add|remove              # 음성 프리셋 관리
  auto-agent font list|set|reset               # 폰트 관리
  auto-agent bg start|stop|status|logs|list    # 백그라운드 파이프라인
  auto-agent sync --project <slug>             # 로컬 → Supabase 동기화
  auto-agent pull --project <slug>             # Supabase → 로컬 다운로드
  auto-agent version list|rollback              # 버전 관리
  auto-agent assets [--type audio]              # 에셋 조회
  auto-agent cleanup [--execute]                # 클린업
  auto-agent costs                              # 비용 요약
  auto-agent dashboard [--port 8080]            # 웹 대시보드
  auto-agent update                             # 최신 버전으로 업데이트
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Windows cp949 인코딩 문제 — 모든 모듈 import 전에 UTF-8 강제
if platform.system() == "Windows":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from auto_agent import __version__
from auto_agent.paths import get_package_dir, get_data_dir, get_workspace_dir
from auto_agent.utils.platform import get_npm_cmd, get_npx_cmd, get_env_with_node
from auto_agent.ui import (
    console,
    print_error,
    print_success,
    print_warning,
    print_header,
    is_non_interactive,
    style_table,
    voice_table,
)


def cmd_init(args):
    """워크스페이스 초기화 (신규 또는 v2→v3 업그레이드)."""
    if not args:
        print_error("Usage: auto-kairos init <workspace-path> [--upgrade]")
        console.print("  예시: auto-kairos init ~/my-video-project")
        console.print("  업그레이드: auto-kairos init ~/my-video-project --upgrade")
        sys.exit(1)

    upgrade_mode = "--upgrade" in args
    clean_args = [a for a in args if a != "--upgrade"]
    workspace = Path(clean_args[0]).resolve()
    template_dir = get_package_dir() / "remotion_template"

    print_header(f"Auto Kairos v3 — {'업그레이드' if upgrade_mode else '워크스페이스 초기화'}")
    console.print(f"  경로: [accent]{workspace}[/accent]")
    if upgrade_mode:
        console.print(f"  모드: [yellow]v2→v3 업그레이드 (기존 데이터 보존)[/yellow]\n")
    else:
        console.print("")

    # 1. 디렉토리 생성
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "RESEARCH").mkdir(exist_ok=True)

    # 2. Remotion 템플릿 복사/업데이트
    remotion_dest = workspace / "remotion"
    if upgrade_mode and remotion_dest.exists():
        # 업그레이드: src/만 덮어쓰기 (public/의 사용자 에셋 보존)
        console.print("  [yellow]UPDATE[/yellow] remotion/src/ (v3 컴포넌트 업데이트)")
        src_src = template_dir / "src"
        src_dest = remotion_dest / "src"
        if src_src.exists():
            shutil.copytree(src_src, src_dest, dirs_exist_ok=True)
        # package.json + config도 업데이트
        for fname in ("package.json", "tsconfig.json", "remotion.config.ts", "render_scene.js"):
            src_f = template_dir / fname
            if src_f.exists():
                shutil.copy2(src_f, remotion_dest / fname)
        # public/fonts, public/geojson 동기화
        for subdir in ("fonts", "geojson"):
            src_d = template_dir / "public" / subdir
            if src_d.exists():
                shutil.copytree(src_d, remotion_dest / "public" / subdir, dirs_exist_ok=True)
        console.print("  [yellow]UPDATE[/yellow] package.json, tsconfig.json, remotion.config.ts")
    elif remotion_dest.exists():
        console.print("  [dim]SKIP[/dim] remotion/ (이미 존재, --upgrade로 업데이트 가능)")
    else:
        console.print("  [accent]COPY[/accent] remotion/ 템플릿")
        shutil.copytree(template_dir, remotion_dest, dirs_exist_ok=True)

    # 3. .env.example 생성
    env_example = workspace / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# Auto Agent 환경 변수\n"
            "# 필요한 API 키를 설정하고 .env로 이름 변경하세요.\n\n"
            "# 필수\n"
            "ELEVENLABS_API_KEY=\n"
            "OPENAI_API_KEY=\n\n"
            "# 선택 (Claude Code 구독 대신 API 직접 사용 시)\n"
            "# ANTHROPIC_API_KEY=\n\n"
            "# 선택 (이미지 생성)\n"
            "FAL_API_KEY=\n"
            "SERPER_API_KEY=\n\n"
            "# 선택 (팩트체크)\n"
            "GOOGLE_API_KEY=\n",
            encoding="utf-8",
        )
        console.print("  [accent]CREATE[/accent] .env.example")

    # 4. CLAUDE.md 생성/업데이트 (Claude Code 연동 — 템플릿 복사)
    claude_md = workspace / "CLAUDE.md"
    template = get_data_dir() / "CLAUDE.md.template"
    if upgrade_mode or not claude_md.exists():
        if template.exists():
            if claude_md.exists():
                # 기존 백업
                backup = workspace / "CLAUDE.md.v2.bak"
                shutil.copy2(claude_md, backup)
                console.print(f"  [yellow]BACKUP[/yellow] CLAUDE.md → CLAUDE.md.v2.bak")
            shutil.copy2(template, claude_md)
            console.print(f"  [accent]{'UPDATE' if upgrade_mode else 'CREATE'}[/accent] CLAUDE.md (v3)")
        else:
            claude_md.write_text("# Auto Kairos 워크스페이스\n", encoding="utf-8")
            console.print("  [accent]CREATE[/accent] CLAUDE.md")
    else:
        console.print("  [dim]SKIP[/dim] CLAUDE.md (이미 존재)")

    # 5. Claude Code 권한 설정
    claude_settings_dir = workspace / ".claude"
    claude_settings = claude_settings_dir / "settings.json"
    if not claude_settings.exists():
        claude_settings_dir.mkdir(exist_ok=True)
        claude_settings.write_text(
            json.dumps({
                "permissions": {
                    "allow": [
                        "Bash(auto-kairos *)",
                        "Bash(auto-agent *)",
                        "Bash(python3 *)",
                        "Bash(npm *)",
                        "Bash(npx remotion *)",
                        "Bash(cd *)",
                        "Bash(ls *)",
                        "Bash(cat *)",
                        "Bash(mkdir *)",
                        "Bash(cp *)",
                    ]
                }
            }, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        console.print("  [accent]CREATE[/accent] .claude/settings.json (권한 사전 승인)")
    else:
        console.print("  [dim]SKIP[/dim] .claude/settings.json (이미 존재)")

    # 6. DB 초기화
    db_path = workspace / "auto_agent.db"
    if not db_path.exists():
        import os
        os.environ["AUTO_AGENT_WORKSPACE"] = str(workspace)
        from auto_agent.db.connection import init_db
        init_db()
        console.print("  [accent]CREATE[/accent] auto_agent.db")
    else:
        console.print("  [dim]SKIP[/dim] auto_agent.db (이미 존재)")

    # 7. npm install
    remotion_pkg = remotion_dest / "package.json"
    remotion_nm = remotion_dest / "node_modules"
    if remotion_pkg.exists() and (not remotion_nm.exists() or upgrade_mode):
        console.print("  [accent]NPM[/accent] Remotion 의존성 설치 중...")
        try:
            result = subprocess.run(
                [get_npm_cmd(), "install"],
                cwd=str(remotion_dest),
                capture_output=True,
                text=True, encoding="utf-8",
                env=get_env_with_node(),
            )
            if result.returncode == 0:
                print_success("npm install 완료")
            else:
                print_warning(f"npm install 실패: {result.stderr[:200]}")
                console.print(f"  수동 실행: cd {remotion_dest} && npm install")
        except FileNotFoundError:
            print_warning("npm을 찾을 수 없습니다. Node.js를 먼저 설치하세요.")
            console.print(f"  설치 후: cd {remotion_dest} && npm install")

    console.print(f"\n[accent]워크스페이스 준비 완료![/accent]")
    console.print(f"\n  다음 단계:")
    console.print(f"    1. cp {workspace}/.env.example {workspace}/.env")
    console.print(f"    2. .env 파일에 API 키 입력")
    console.print(f"    3. cd {workspace}")
    console.print(f"    4. [accent]auto-agent project create[/accent]")


def cmd_run(args):
    """파이프라인 실행."""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent run")
    parser.add_argument("--project", required=True, help="프로젝트 slug 또는 uuid")
    parser.add_argument("--from", dest="from_step", help="이 step부터 실행")
    parser.add_argument("--only", dest="only_step", help="이 step만 실행")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 계획만 출력")
    parser.add_argument("--workspace", help="워크스페이스 경로")
    parsed = parser.parse_args(args)

    # uuid/slug 양쪽 허용: DB로 resolve해 slug를 정규화
    project_identifier = parsed.project
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.resolve_project(project_identifier)
            if project:
                project_identifier = project["slug"]
    except Exception:
        pass

    from auto_agent.orchestrator.runner import PipelineRunner
    runner = PipelineRunner(project_identifier)
    runner.run(
        from_step=parsed.from_step,
        only_step=parsed.only_step,
        dry_run=parsed.dry_run,
    )


def cmd_studio(args):
    """Remotion 스튜디오 실행."""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent studio")
    parser.add_argument("--project", help="프로젝트 slug (manifest 자동 로드)")
    parser.add_argument("--workspace", help="워크스페이스 경로")
    parsed = parser.parse_args(args)

    workspace = get_workspace_dir()
    remotion_dir = workspace / "remotion"

    if not remotion_dir.exists():
        print_error(f"Remotion 디렉토리를 찾을 수 없습니다: {remotion_dir}")
        console.print(f"  'auto-agent init {workspace}' 를 먼저 실행하세요.")
        sys.exit(1)

    extra_env = {}
    if parsed.project:
        extra_env["PROJECT_NAME"] = parsed.project

    print_success(f"Remotion Studio 시작: {remotion_dir}")
    subprocess.run(
        [get_npx_cmd(), "remotion", "studio"],
        cwd=str(remotion_dir),
        env={**get_env_with_node(), **extra_env},
    )


def cmd_project(args):
    """프로젝트 관리 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_project as _cmd_project
    _cmd_project(args)


def cmd_config(args):
    """프로젝트 설정 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_config as _cmd_config
    _cmd_config(args)


def cmd_version(args):
    """버전 관리 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_version as _cmd_version
    _cmd_version(args)


def cmd_assets(args):
    """에셋 조회 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_assets as _cmd_assets
    _cmd_assets(args)


def cmd_cleanup(args):
    """클린업 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_cleanup as _cmd_cleanup
    _cmd_cleanup(args)


def cmd_costs(args):
    """비용 요약 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_costs as _cmd_costs
    _cmd_costs(args)


def cmd_dashboard(args):
    """웹 대시보드 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_dashboard as _cmd_dashboard
    _cmd_dashboard(args)


def _get_arg(args: list, flag: str) -> str:
    """CLI 인자에서 --flag <value> 추출."""
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return ""


def _get_active_project():
    """활성 프로젝트 (pm, project, config) 반환. 없으면 (None, None, None)."""
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.get_active_project()
            if project:
                config = pm.get_config(project["id"])
                return pm, project, config
    except Exception:
        pass
    return None, None, None


def _format_elapsed(started_at: str, finished_at: str = None) -> str:
    """started_at/finished_at ISO 문자열로 경과 시간 포매팅."""
    from datetime import datetime
    start = datetime.fromisoformat(started_at)
    end = datetime.fromisoformat(finished_at) if finished_at else datetime.now()
    total_secs = int((end - start).total_seconds())
    mins = total_secs // 60
    if mins < 60:
        secs = total_secs % 60
        return f"{mins}분 {secs}초"
    return f"{mins // 60}시간 {mins % 60}분"


# ── 아트스타일 관리 ─────────────────────────────

def cmd_style(args):
    """아트스타일 관리: list, add, remove."""
    from auto_agent.ui.prompts import _scan_art_styles

    if not args or args[0] == "list":
        styles = _scan_art_styles()
        if not styles:
            print_warning("등록된 아트스타일이 없습니다.")
            return
        console.print(style_table(styles))

    elif args[0] == "add":
        # 비인터랙티브: style add --name <이름> --image <이미지경로> [--description <설명>]
        if "--name" in args:
            name = _get_arg(args, "--name")
            image = _get_arg(args, "--image") or ""
            description = _get_arg(args, "--description") or ""
            style_desc = _get_arg(args, "--style-desc") or ""
            if not name:
                print_error("--name 은 필수입니다.")
                return
            data = {
                "name": name,
                "description": description,
                "art_style": style_desc,
                "color_palette": "",
                "mood_and_tone": "",
            }
            ref_image_path = image
        else:
            # 인터랙티브
            try:
                from auto_agent.ui.prompts import prompt_style_add
                data = prompt_style_add()
            except KeyboardInterrupt:
                console.print("\n[dim]취소됨[/dim]")
                return
            ref_image_path = ""

        # 워크스페이스에 JSON 저장
        styles_dir = get_workspace_dir() / "artstyle" / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)

        filename = data["name"].replace(" ", "_").lower() + ".json"
        filepath = styles_dir / filename

        # reference_image: 이미지 파일을 스타일 디렉토리에 복사
        saved_ref_image = ""
        if ref_image_path and Path(ref_image_path).exists():
            src = Path(ref_image_path)
            dest = styles_dir / f"{Path(filename).stem}_base{src.suffix}"
            shutil.copy2(src, dest)
            saved_ref_image = f"artstyle/styles/{dest.name}"
            console.print(f"  [accent]COPY[/accent] 기준 이미지 → {dest}")

        style_json = {
            "name": data["name"],
            "description": data["description"],
            "reference_image": saved_ref_image,
            "scene_style_description": data.get("art_style", ""),
            "style": {
                "art_style": data.get("art_style", ""),
                "color_palette": data.get("color_palette", ""),
                "mood_and_tone": data.get("mood_and_tone", ""),
            },
            "technical": {
                "no_text": True,
                "resolution": "1024x1024",
            },
        }

        filepath.write_text(
            json.dumps(style_json, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print_success(f"아트스타일 추가됨: [accent]{data['name']}[/accent] → {filepath}")
        if saved_ref_image:
            print_success(f"  기준 이미지: {saved_ref_image}")

    elif args[0] == "remove":
        if len(args) < 2:
            print_error("Usage: style remove <파일명 또는 스타일명>")
            return

        target = args[1]
        styles = _scan_art_styles()
        matched = None
        for s in styles:
            if s["filename"] == target or s["name"] == target or s["filename"] == target + ".json":
                matched = s
                break

        if not matched:
            print_error(f"스타일 '{target}' 을 찾을 수 없습니다.")
            return

        # 워크스페이스 스타일만 삭제 가능
        ws_styles = str(get_workspace_dir() / "artstyle" / "styles")
        if not matched["path"].startswith(ws_styles):
            print_error("기본 내장 스타일은 삭제할 수 없습니다. 워크스페이스에 추가한 스타일만 삭제 가능합니다.")
            return

        Path(matched["path"]).unlink()
        print_success(f"스타일 삭제됨: {matched['name']}")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, add, remove <이름>")


# ── 음성 프리셋 관리 ────────────────────────────

def cmd_voice(args):
    """음성 프리셋 관리: list, add, remove."""
    from auto_agent.voice_manager import VoiceManager
    vm = VoiceManager()

    if not args or args[0] == "list":
        voices = vm.list_voices()
        if not voices:
            print_warning("등록된 음성 프리셋이 없습니다.")
            return
        console.print(voice_table(voices))

    elif args[0] == "add":
        # 비인터랙티브: voice add --name <이름> --voice-id <ID> [--description <설명>]
        if "--name" in args and "--voice-id" in args:
            name = _get_arg(args, "--name")
            voice_id = _get_arg(args, "--voice-id")
            description = _get_arg(args, "--description") or ""
            if not name or not voice_id:
                print_error("--name 과 --voice-id 는 필수입니다.")
                return
            data = {"name": name, "voice_id": voice_id, "description": description}
        else:
            # 인터랙티브
            try:
                from auto_agent.ui.prompts import prompt_voice_add
                data = prompt_voice_add()
            except KeyboardInterrupt:
                console.print("\n[dim]취소됨[/dim]")
                return

        vm.add_voice(
            name=data["name"],
            voice_id=data["voice_id"],
            description=data["description"],
        )
        print_success(f"음성 프리셋 추가됨: [accent]{data['name']}[/accent] (voice_id: {data['voice_id']})")

    elif args[0] == "remove":
        if len(args) < 2:
            print_error("Usage: voice remove <이름>")
            return
        name = args[1]
        if vm.remove_voice(name):
            print_success(f"음성 프리셋 삭제됨: {name}")
        else:
            print_error(f"프리셋 '{name}' 을 찾을 수 없습니다.")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, add, remove <이름>")


def cmd_font(args):
    """폰트 관리: list, set, reset."""
    from auto_agent.font_manager import FontManager, DEFAULT_FONT

    fm = FontManager()

    if not args or args[0] == "list":
        # 폰트 목록 출력
        fonts = fm.list_fonts()
        if not fonts:
            print_warning("시스템 폰트를 찾을 수 없습니다.")
            return

        # 현재 프로젝트 설정 폰트 확인
        current_font = DEFAULT_FONT
        _, _, config = _get_active_project()
        if config:
            current_font = config.get("font_family", DEFAULT_FONT)

        from rich.table import Table
        table = Table(title="사용 가능한 폰트", border_style="dim")
        table.add_column("폰트", style="white")
        table.add_column("소스", style="dim")
        table.add_column("", style="accent")

        bundled = [f for f in fonts if f["source"] == "bundled"]
        system = [f for f in fonts if f["source"] == "system"]

        for f in bundled:
            marker = " <-- 현재" if f["family"] == current_font else ""
            table.add_row(f["family"], "번들", marker)

        for f in system:
            marker = " <-- 현재" if f["family"] == current_font else ""
            table.add_row(f["family"], "시스템", marker)

        console.print(table)
        console.print(f"\n  총 [accent]{len(fonts)}[/accent]개 ({len(bundled)} 번들 + {len(system)} 시스템)")
        console.print(f"  현재: [accent]{current_font}[/accent]")

    elif args[0] == "set":
        # 폰트 설정
        pm, project, _ = _get_active_project()
        if not project:
            print_warning("활성 프로젝트가 없습니다. (DB 미초기화 또는 프로젝트 없음)")
            return

        if len(args) >= 2:
            # 비인터랙티브: font set <폰트명>
            font_name = " ".join(args[1:])
        else:
            # 인터랙티브: 퍼지 검색 선택
            try:
                from auto_agent.ui.prompts import prompt_font
                font_name = prompt_font()
            except KeyboardInterrupt:
                console.print("\n[dim]취소됨[/dim]")
                return

        # 유효성 검사
        if not fm.is_available(font_name):
            print_warning(f"'{font_name}' 폰트가 시스템에 설치되지 않았습니다.")
            from auto_agent.ui.prompts import prompt_confirm
            if not prompt_confirm(f"그래도 설정하시겠습니까? (렌더링 머신에 설치되어 있을 수 있음)"):
                return

        pm.update_config(project["id"], font_family=font_name)
        is_bundled = fm.is_bundled(font_name)
        source = "번들" if is_bundled else "시스템"
        print_success(f"폰트 설정: [accent]{font_name}[/accent] ({source})  —  프로젝트: {project['name']}")
        if not is_bundled:
            console.print("  [dim]렌더링 머신에도 이 폰트가 설치되어 있어야 합니다.[/dim]")

    elif args[0] == "reset":
        # 기본 폰트로 리셋
        pm, project, _ = _get_active_project()
        if not project:
            print_warning("활성 프로젝트가 없습니다. (DB 미초기화 또는 프로젝트 없음)")
            return

        pm.update_config(project["id"], font_family=DEFAULT_FONT)
        print_success(f"폰트 초기화: [accent]{DEFAULT_FONT}[/accent]  —  프로젝트: {project['name']}")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, set [폰트명], reset")


def cmd_bg(args):
    """백그라운드 파이프라인 세션 관리: start, stop, status, logs, list."""
    from auto_agent.session_manager import SessionManager

    sm = SessionManager()

    if not args:
        # 인자 없으면 list 출력
        args = ["list"]

    sub = args[0]

    if sub == "start":
        # bg start --project <slug|uuid> [--from step_N] [--only step_N]
        project_slug = _get_arg(args[1:], "--project")
        from_step = _get_arg(args[1:], "--from") or None
        only_step = _get_arg(args[1:], "--only") or None

        if not project_slug:
            # 활성 프로젝트 사용
            _, project, _ = _get_active_project()
            if project:
                project_slug = project["slug"]

        if not project_slug:
            print_error("프로젝트를 지정하세요: bg start --project <slug>")
            return

        # uuid/slug 양쪽 허용: DB로 resolve해 slug를 정규화
        try:
            from auto_agent.db.connection import db_exists
            if db_exists():
                from auto_agent.db.project_manager import ProjectManager
                pm = ProjectManager()
                project = pm.resolve_project(project_slug)
                if project:
                    project_slug = project["slug"]
        except Exception:
            pass

        try:
            session = sm.start(project_slug, from_step=from_step, only_step=only_step)
            print_success(f"백그라운드 파이프라인 시작: [accent]{project_slug}[/accent]")
            console.print(f"  PID: {session['pid']}")
            console.print(f"  로그: {session['log_file']}")
            if from_step:
                console.print(f"  시작 스텝: {from_step}")
            console.print(f"\n  상태 확인: [accent]auto-agent bg status --project {project_slug}[/accent]")
            console.print(f"  로그 보기: [accent]auto-agent bg logs --project {project_slug}[/accent]")
        except RuntimeError as e:
            print_error(str(e))

    elif sub == "stop":
        project_slug = _get_arg(args[1:], "--project") or (args[1] if len(args) > 1 and not args[1].startswith("-") else None)
        if not project_slug:
            print_error("프로젝트를 지정하세요: bg stop --project <slug>")
            return

        session = sm.stop(project_slug)
        if session:
            if session["status"] == "stopped":
                print_success(f"파이프라인 중지됨: [accent]{project_slug}[/accent]")
            else:
                print_warning(f"이미 종료된 세션: {session['status']}")
        else:
            print_warning(f"'{project_slug}' 세션을 찾을 수 없습니다.")

    elif sub == "status":
        project_slug = _get_arg(args[1:], "--project") or (args[1] if len(args) > 1 and not args[1].startswith("-") else None)
        if project_slug:
            session = sm.get_session(project_slug)
            if session:
                _print_session_detail(session)
            else:
                print_warning(f"'{project_slug}' 세션을 찾을 수 없습니다.")
        else:
            # 모든 세션 상태
            sessions = sm.list_sessions()
            if not sessions:
                print_warning("실행 중인 세션이 없습니다.")
                return
            _print_session_table(sessions)

    elif sub == "logs":
        project_slug = _get_arg(args[1:], "--project") or (args[1] if len(args) > 1 and not args[1].startswith("-") else None)
        if not project_slug:
            print_error("프로젝트를 지정하세요: bg logs --project <slug>")
            return

        follow = "--follow" in args or "-f" in args
        lines = 50
        for i, a in enumerate(args):
            if a in ("--lines", "-n") and i + 1 < len(args):
                try:
                    lines = int(args[i + 1])
                except ValueError:
                    pass

        if follow:
            console.print(f"[dim]로그 실시간 추적: {project_slug} (Ctrl+C로 종료)[/dim]\n")
            try:
                for line in sm.follow_log(project_slug):
                    console.print(line, highlight=False)
            except KeyboardInterrupt:
                console.print("\n[dim]추적 종료[/dim]")
        else:
            log_text = sm.get_log_tail(project_slug, lines=lines)
            if log_text:
                console.print(f"[dim]--- {project_slug} 로그 (최근 {lines}줄) ---[/dim]\n")
                console.print(log_text, highlight=False)
            else:
                print_warning("로그가 비어있거나 세션을 찾을 수 없습니다.")

    elif sub == "list":
        sessions = sm.list_sessions()
        if not sessions:
            print_warning("세션 기록이 없습니다.")
            console.print("  [dim]시작: auto-agent bg start --project <slug>[/dim]")
            return
        _print_session_table(sessions)

    elif sub == "clean":
        days = 7
        for i, a in enumerate(args):
            if a == "--days" and i + 1 < len(args):
                try:
                    days = int(args[i + 1])
                except ValueError:
                    pass
        cleaned = sm.cleanup_finished(keep_days=days)
        print_success(f"세션 정리 완료: {cleaned}개 (기준: {days}일 이전)")

    else:
        print_error(f"알 수 없는 서브커맨드: {sub}")
        console.print("  사용 가능: start, stop, status, logs, list, clean")


def _print_session_detail(session: dict):
    """단일 세션 상세 출력."""
    from rich.panel import Panel
    from rich.text import Text

    status = session["status"]
    status_colors = {
        "running": "green",
        "completed": "blue",
        "failed": "red",
        "stopped": "yellow",
    }
    color = status_colors.get(status, "white")

    lines = [
        f"[white]프로젝트:[/white]  [accent]{session['project_slug']}[/accent]",
        f"[white]상태:[/white]     [{color}]{status.upper()}[/{color}]",
        f"[white]PID:[/white]      {session['pid']}",
        f"[white]시작:[/white]     {session['started_at'][:19]}",
    ]
    if session.get("finished_at"):
        lines.append(f"[white]종료:[/white]     {session['finished_at'][:19]}")
    if session.get("from_step"):
        lines.append(f"[white]시작스텝:[/white]  {session['from_step']}")
    if session.get("only_step"):
        lines.append(f"[white]단일스텝:[/white]  {session['only_step']}")
    lines.append(f"[white]로그:[/white]     [dim]{session.get('log_file', 'N/A')}[/dim]")

    # 실행 시간 계산
    if session.get("started_at"):
        lines.append(f"[white]경과:[/white]     {_format_elapsed(session['started_at'], session.get('finished_at'))}")

    console.print(Panel(
        "\n".join(lines),
        title=f"세션: {session['project_slug']}",
        border_style=color,
    ))


def _print_session_table(sessions: list[dict]):
    """세션 목록 테이블 출력."""
    from rich.table import Table

    table = Table(title="백그라운드 세션", border_style="dim")
    table.add_column("프로젝트", style="accent")
    table.add_column("상태", justify="center")
    table.add_column("PID", style="dim", justify="right")
    table.add_column("시작", style="dim")
    table.add_column("경과", justify="right")

    status_styles = {
        "running": "[green]RUNNING[/green]",
        "completed": "[blue]DONE[/blue]",
        "failed": "[red]FAILED[/red]",
        "stopped": "[yellow]STOPPED[/yellow]",
    }

    for s in sessions:
        status_text = status_styles.get(s["status"], s["status"])
        started = s.get("started_at", "")[:16].replace("T", " ")
        elapsed = _format_elapsed(s["started_at"], s.get("finished_at")) if s.get("started_at") else ""

        table.add_row(
            s["project_slug"],
            status_text,
            str(s["pid"]),
            started,
            elapsed,
        )

    console.print(table)


def cmd_update(args):
    """최신 버전으로 업데이트."""
    import importlib.metadata

    print_header("auto-agent — 업데이트")

    # 패키지 설치 위치에서 Git repo 경로 탐색
    pkg_dir = get_package_dir()
    repo_dir = pkg_dir.parent  # auto_agent/ → repo root

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        # pip install git+... 로 설치한 경우 (site-packages에 위치)
        console.print("  [dim]Git 저장소가 아닌 환경에서 설치되었습니다.[/dim]\n")
        console.print("  업데이트 방법:")
        console.print("  [accent]pip install --upgrade git+ssh://git@github.com/jleavens01/kairos-agent.git[/accent]")
        return

    current = __version__

    # 1. git pull
    console.print(f"  현재 버전: [accent]v{current}[/accent]")
    console.print("  [accent]git pull[/accent] 실행 중...")

    result = subprocess.run(
        ["git", "pull"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True, encoding="utf-8",
    )

    if result.returncode != 0:
        print_error(f"git pull 실패: {result.stderr.strip()}")
        return

    if "Already up to date" in result.stdout:
        print_success("이미 최신 버전입니다.")
        return

    console.print(f"  {result.stdout.strip()}")

    # 2. pip install -e . (editable) 또는 pip install . 재설치
    console.print("  [accent]pip install[/accent] 재설치 중...")

    # editable 설치 여부 확인
    try:
        dist = importlib.metadata.distribution("auto-agent")
        direct_url = dist.read_text("direct_url.json")
        is_editable = direct_url and '"editable": true' in direct_url
    except Exception:
        is_editable = False

    pip_cmd = [sys.executable, "-m", "pip", "install", "-q"]
    if is_editable:
        pip_cmd += ["-e", str(repo_dir)]
    else:
        pip_cmd += [str(repo_dir)]

    result = subprocess.run(pip_cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode != 0:
        print_error(f"pip install 실패: {result.stderr.strip()[:300]}")
        return

    # 3. 업데이트 후 버전 확인
    result = subprocess.run(
        [sys.executable, "-c", "from auto_agent import __version__; print(__version__)"],
        capture_output=True,
        text=True, encoding="utf-8",
    )
    new_version = result.stdout.strip() if result.returncode == 0 else "?"

    if new_version != current:
        print_success(f"업데이트 완료! v{current} → [accent]v{new_version}[/accent]")
    else:
        print_success(f"재설치 완료 (v{new_version})")


def cmd_sync(args):
    """로컬 → Supabase 동기화 (push) — Supabase 미설정 시 비활성."""
    print_warning("Supabase 동기화가 비활성화되어 있습니다. .env에서 SUPABASE_URL/KEY를 설정하세요.")


def cmd_pull(args):
    """Supabase → 로컬 다운로드 (pull) — Supabase 미설정 시 비활성."""
    print_warning("Supabase 동기화가 비활성화되어 있습니다. .env에서 SUPABASE_URL/KEY를 설정하세요.")


def cmd_collect(args):
    """데이터 수집 (YouTube, 트렌드, 소셜)."""
    from auto_agent.modules.data_collector.collector import DataCollector

    print_header("Auto Agent — 데이터 수집")
    collector = DataCollector()

    if not args or "--all" in args:
        collector.collect_all()
        print_success("전체 수집 완료")
    elif "--youtube" in args:
        collector.collect_youtube()
        print_success("YouTube 수집 완료")
    else:
        print_error("Usage: auto-agent collect [--all|--youtube|--trends|--social]")


def cmd_link(args):
    """프로젝트에 YouTube 영상 ID 연결."""
    project_slug = None
    video_id = None

    for i, arg in enumerate(args):
        if arg == "--project" and i + 1 < len(args):
            project_slug = args[i + 1]
        elif arg == "--video-id" and i + 1 < len(args):
            video_id = args[i + 1]

    if not project_slug or not video_id:
        print_error("Usage: auto-agent link --project <slug> --video-id <id>")
        sys.exit(1)

    from auto_agent.db.project_manager import link_video, get_project_by_slug
    from auto_agent.modules.data_collector.collector import DataCollector

    link_video(project_slug, video_id)

    project = get_project_by_slug(project_slug)
    channel = project.get("channel", "이로미즘") if project else "이로미즘"

    collector = DataCollector()
    collector.register_video_tracking(video_id, project_slug, channel)

    print_success(f"영상 연결 완료: {project_slug} ← {video_id}")
    print_success("성과 추적 등록: +1d, +3d, +7d, +28d")


def cmd_watchlist(args):
    """경쟁 채널 워치리스트 관리."""
    from auto_agent.paths import get_vault_dir
    from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser

    vault = get_vault_dir()
    parser = WatchlistParser(vault)

    if not args:
        watchlist_path = vault / "channels" / "_watchlist.md"
        if watchlist_path.exists():
            console.print(watchlist_path.read_text(encoding="utf-8"))
        else:
            print_warning("워치리스트가 없습니다. channels/_watchlist.md를 생성하세요.")
        return

    subcmd = args[0]
    if subcmd == "approve" and len(args) > 1:
        channel_name = args[1]
        try:
            parser.approve(channel_name)
            print_success(f"채널 승격 완료: {channel_name} (trial → active)")
        except ValueError as e:
            print_error(str(e))
    elif subcmd == "remove" and len(args) > 1:
        channel_name = args[1]
        try:
            parser.remove(channel_name)
            print_success(f"채널 제거 완료: {channel_name} → archived")
        except ValueError as e:
            print_error(str(e))
    else:
        print_error("Usage: auto-agent watchlist [approve|remove] <채널명>")


def cmd_vault(args):
    """볼트 관리: sync / index / stats / search."""
    from auto_agent.orchestrator.vault_rag import VAULT_DIR, VaultRAG

    sub = args[0] if args else "stats"

    if sub == "sync":
        vault = VaultRAG()
        result = vault.sync_local_to_vault()
        if result.get("error"):
            print_error(result["error"])
        elif result.get("synced", 0) > 0:
            print_success(f"로컬 → NAS 동기화 완료: {result['synced']}개 파일")
            cleaned = vault.cleanup_local_vault()
            if cleaned > 0:
                print_success(f"로컬 폴백 정리: {cleaned}개 파일 삭제")
        else:
            print_success("동기화할 파일 없음 (로컬 폴백 비어있음)")
        return

    elif sub == "index":
        force = "--force" in args
        try:
            from auto_agent.orchestrator.vault_indexer import VaultIndexer
        except ImportError:
            print_error("RAG 의존성 미설치. 설치: pip install -e '.[rag]'")
            sys.exit(1)

        if not VAULT_DIR.exists():
            print_error(f"볼트를 찾을 수 없음: {VAULT_DIR}")
            sys.exit(1)

        console.print(f"[bold]볼트 인덱싱 시작[/bold]: {VAULT_DIR}")
        if force:
            console.print("[yellow]--force: 전체 재인덱싱[/yellow]")
        indexer = VaultIndexer()
        result = indexer.index_all(VAULT_DIR, force=force)
        console.print(
            f"[green]완료[/green] — 인덱싱: {result['indexed']}, "
            f"스킵: {result['skipped']}, 오류: {result['errors']}, "
            f"총 청크: {result['total_chunks']}"
        )

    elif sub == "stats":
        try:
            from auto_agent.orchestrator.vault_indexer import VaultIndexer
            stats = VaultIndexer().get_stats()
            console.print(f"파일 수: {stats['file_count']}")
            console.print(f"청크 수: {stats['chunk_count']}")
            console.print(f"마지막 인덱싱: {stats['last_indexed_at'] or '없음'}")
            console.print(f"Chroma 경로: {stats['chroma_dir']}")
            console.print(f"볼트 경로: {VAULT_DIR}")
        except ImportError:
            print_error("RAG 의존성 미설치. 설치: pip install -e '.[rag]'")

    elif sub == "search":
        query = " ".join(a for a in args[1:] if not a.startswith("-"))
        if not query:
            print_error("사용법: auto-agent vault search <쿼리>")
            sys.exit(1)
        from auto_agent.orchestrator.vault_rag import VaultRAG
        rag = VaultRAG()
        results = rag.semantic_search(query, top_k=5)
        if not results:
            console.print("[yellow]결과 없음[/yellow]")
            return
        for r in results:
            console.print(f"\n[bold]{r['file']}[/bold] (유사도: {r['score']})")
            console.print(f"  {r['snippet'][:150]}...")
    else:
        console.print("사용법: auto-agent vault [index|stats|search] [--force]")


def _parse_project_flag(args):
    """args에서 --project <slug> 값 추출."""
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            return args[idx + 1]
    return None


COMMANDS = {
    "init": cmd_init,
    "run": cmd_run,
    "studio": cmd_studio,
    "project": cmd_project,
    "config": cmd_config,
    "version": cmd_version,
    "assets": cmd_assets,
    "cleanup": cmd_cleanup,
    "costs": cmd_costs,
    "dashboard": cmd_dashboard,
    "style": cmd_style,
    "voice": cmd_voice,
    "font": cmd_font,
    "bg": cmd_bg,
    "vault": cmd_vault,
    "collect": cmd_collect,
    "link": cmd_link,
    "watchlist": cmd_watchlist,
    "sync": cmd_sync,
    "pull": cmd_pull,
    "update": cmd_update,
    "skill-path": lambda args: print(get_data_dir()),
}


def _print_banner():
    """브랜드 배너 + 사용법 출력."""
    print_header(f"auto-agent v{__version__}")
    console.print()
    cmds = [
        ("init <workspace>", "워크스페이스 초기화"),
        ("project create", "새 프로젝트 (인터랙티브)"),
        ("project list", "프로젝트 목록"),
        ("run --project <slug>", "파이프라인 실행"),
        ("studio --project <slug>", "Remotion 스튜디오"),
        ("config get|set", "프로젝트 설정"),
        ("style list|add|remove", "아트스타일 관리"),
        ("voice list|add|remove", "음성 프리셋 관리"),
        ("font list|set|reset", "폰트 관리"),
        ("bg start|stop|status|logs", "백그라운드 파이프라인"),
        ("version list|rollback", "버전 관리"),
        ("assets", "에셋 조회"),
        ("costs", "비용 요약"),
        ("sync --project <slug>", "로컬 → Supabase 동기화"),
        ("pull --project <slug>", "Supabase → 로컬 다운로드"),
        ("dashboard", "웹 대시보드"),
        ("update", "최신 버전으로 업데이트"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [accent]auto-agent {cmd:<28}[/accent] {desc}")


def main():
    # 워크스페이스 .env 로드 (API 키 등)
    try:
        from dotenv import load_dotenv
        load_dotenv(get_workspace_dir() / ".env")
    except ImportError:
        pass

    args = sys.argv[1:]

    # --version 플래그
    if not args or "--version" in args:
        if "--version" in args:
            console.print(f"[accent]auto-agent[/accent] v{__version__}")
            return
        _print_banner()
        return

    if args[0] in ("-h", "--help", "help"):
        _print_banner()
        return

    cmd = args[0]
    if cmd not in COMMANDS:
        print_error(f"알 수 없는 명령어: {cmd}")
        console.print(f"  사용 가능: [accent]{', '.join(COMMANDS.keys())}[/accent]")
        sys.exit(1)

    COMMANDS[cmd](args[1:])


if __name__ == "__main__":
    main()
