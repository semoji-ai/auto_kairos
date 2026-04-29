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
  auto-agent auto-kairos                        # 원클릭 영상 제작
  auto-agent multi-contents --project <slug>    # 멀티포맷 콘텐츠 생성
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
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


def _register_lane_mcp_global(workspace: Path) -> None:
    """lane MCP 서버를 ~/.claude.json 전역 설정에 등록.

    이미 등록돼 있으면 python 경로만 현재 venv로 갱신한다.
    """
    import sys as _sys
    claude_json = Path.home() / ".claude.json"

    # 현재 venv의 python 경로 (없으면 sys.executable)
    venv_python = str(Path(workspace) / ".venv" / "bin" / "python")
    if not Path(venv_python).exists():
        venv_python = _sys.executable

    entry = {
        "command": venv_python,
        "args": ["-m", "auto_agent.tools.mcp_lane_server"],
    }

    try:
        cfg = json.loads(claude_json.read_text(encoding="utf-8")) if claude_json.exists() else {}
    except Exception:
        cfg = {}

    cfg.setdefault("mcpServers", {})
    existing = cfg["mcpServers"].get("lane", {})

    if existing == entry:
        console.print("  [dim]SKIP[/dim] lane MCP 전역 등록 (이미 최신)")
        return

    cfg["mcpServers"]["lane"] = entry
    claude_json.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    action = "UPDATE" if existing else "CREATE"
    console.print(f"  [accent]{action}[/accent] ~/.claude.json — lane MCP 전역 등록 ({venv_python})")


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

    # 6. Lane MCP 전역 등록 (~/.claude.json)
    _register_lane_mcp_global(workspace)

    # 7. DB 초기화
    db_path = workspace / "auto_agent.db"
    if not db_path.exists():
        import os
        os.environ["AUTO_AGENT_WORKSPACE"] = str(workspace)
        from auto_agent.db.connection import init_db
        init_db()
        console.print("  [accent]CREATE[/accent] auto_agent.db")
    else:
        console.print("  [dim]SKIP[/dim] auto_agent.db (이미 존재)")

    # 8. npm install
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
    parser.add_argument("--until", dest="until_step", help="이 step까지만 실행 (예: --until step_2b)")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 계획만 출력")
    parser.add_argument("--force", action="store_true", help="출력 파일이 이미 있어도 강제 재실행")
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
        stop_after_step=getattr(parsed, "until_step", None),
        dry_run=parsed.dry_run,
        force=parsed.force,
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


def _create_from_plan(plan_path_str: str):
    """기획안 마크다운에서 프로젝트 자동 생성."""
    from auto_agent.paths import get_vault_dir

    vault = get_vault_dir()
    plan_path = vault / plan_path_str if not Path(plan_path_str).is_absolute() else Path(plan_path_str)

    if not plan_path.exists():
        print_error(f"기획안을 찾을 수 없습니다: {plan_path}")
        sys.exit(1)

    content = plan_path.read_text(encoding="utf-8")

    # frontmatter 파싱
    channel = "이로미즘"
    topic = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.split("\n"):
                if line.startswith("channel:"):
                    channel = line.split(":", 1)[1].strip()

    # 주제 추출 (## 주제: 라인)
    for line in content.split("\n"):
        if line.startswith("## 주제:"):
            topic = line.replace("## 주제:", "").strip()
            break

    if not topic:
        print_error("기획안에서 주제를 찾을 수 없습니다 (## 주제: 형식 필요)")
        sys.exit(1)

    # 프로젝트 생성 (기존 create 로직 재사용)
    slug = topic.replace(" ", "_").replace("/", "_")[:50]
    console.print(f"  주제: [accent]{topic}[/accent]")
    console.print(f"  채널: [accent]{channel}[/accent]")
    console.print(f"  슬러그: [accent]{slug}[/accent]")

    # 기획안 status 업데이트
    updated = content.replace("status: proposed", "status: approved")
    plan_path.write_text(updated, encoding="utf-8")
    print_success(f"기획안 승인됨: {plan_path.name}")

    return topic, channel, slug


def cmd_project(args):
    """프로젝트 관리 — db.cli에 위임. --from-plan 지원."""
    if "--from-plan" in args:
        idx = args.index("--from-plan")
        if idx + 1 < len(args):
            plan_path = args[idx + 1]
            topic, channel, slug = _create_from_plan(plan_path)
            # 기존 create 로직에 위임
            from auto_agent.db.cli import cmd_project as _cmd_project
            _cmd_project(["create", slug, topic])
            return
        else:
            print_error("--from-plan 뒤에 기획안 경로를 지정하세요.")
            sys.exit(1)

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

        # canonical package data에 JSON 저장
        styles_dir = get_data_dir() / "artstyle" / "styles"
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

        # canonical data dir 스타일만 삭제 가능
        canonical_styles = str(get_data_dir() / "artstyle" / "styles")
        if not matched["path"].startswith(canonical_styles):
            print_error("canonical 아트스타일 디렉토리 밖의 스타일은 삭제할 수 없습니다.")
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
        until_step = _get_arg(args[1:], "--until") or None

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
            session = sm.start(project_slug, from_step=from_step, only_step=only_step, stop_after_step=until_step)
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
    """데이터 수집 (YouTube, 트렌드, 경쟁채널, 외부 신호)."""
    from auto_agent.paths import get_vault_dir

    print_header("Auto Agent — 데이터 수집")
    signal_import = None
    signal_import_url = None
    signal_target = "market/social"
    signal_name = None
    for i, arg in enumerate(args):
        if arg == "--signals-import" and i + 1 < len(args):
            signal_import = args[i + 1]
        elif arg == "--signals-import-url" and i + 1 < len(args):
            signal_import_url = args[i + 1]
        elif arg == "--target" and i + 1 < len(args):
            signal_target = args[i + 1]
        elif arg == "--name" and i + 1 < len(args):
            signal_name = args[i + 1]

    if not args or "--all" in args:
        # yt-dlp로 경쟁 채널 + 트렌딩 수집
        try:
            from auto_agent.modules.data_collector.ytdlp_collector import YtdlpCollector
            vault = get_vault_dir()
            ytdlp = YtdlpCollector(vault)

            console.print("  [dim]경쟁 채널 수집 (yt-dlp)...[/dim]")
            comp_result = ytdlp.collect_competitors(vault / "channels" / "_watchlist.md")
            print_success(f"경쟁 채널: {comp_result['collected']}개 영상 수집")

            console.print("  [dim]트렌딩 수집 (yt-dlp)...[/dim]")
            trending = ytdlp.collect_trending()
            print_success(f"트렌딩: {len(trending)}개 영상 수집")
        except Exception as e:
            print_warning(f"yt-dlp 수집 실패: {e}")

        # YouTube Analytics (우리 채널 성과)
        try:
            from auto_agent.modules.data_collector.youtube_analytics import YouTubeAnalytics
            for ch in ["iromism", "semoji"]:
                console.print(f"  [dim]{ch} Analytics 수집...[/dim]")
                yt = YouTubeAnalytics(ch)
                data = yt.save_to_vault(vault)
                if data.get("info"):
                    print_success(f"{ch}: 구독자 {data['info']['subscribers']:,}")
        except Exception as e:
            print_warning(f"YouTube Analytics: {e}")

        # 기존 DataCollector도 실행
        try:
            from auto_agent.modules.data_collector.collector import DataCollector
            collector = DataCollector()
            collector.collect_all()
        except Exception as e:
            print_warning(f"DataCollector: {e}")

        print_success("전체 수집 완료")
    elif "--competitors" in args:
        from auto_agent.modules.data_collector.ytdlp_collector import YtdlpCollector
        vault = get_vault_dir()
        ytdlp = YtdlpCollector(vault)
        result = ytdlp.collect_competitors(vault / "channels" / "_watchlist.md")
        print_success(f"경쟁 채널: {result['collected']}개 영상 수집")
    elif "--trending" in args:
        from auto_agent.modules.data_collector.ytdlp_collector import YtdlpCollector
        vault = get_vault_dir()
        ytdlp = YtdlpCollector(vault)
        trending = ytdlp.collect_trending()
        print_success(f"트렌딩: {len(trending)}개 영상 수집")
    elif "--signals" in args:
        from auto_agent.modules.data_collector.collector import DataCollector
        collector = DataCollector()
        collector.collect_signals()
        print_success("외부 신호 수집 완료")
    elif signal_import:
        from pathlib import Path
        from auto_agent.modules.data_collector.signal_feed_collector import SignalFeedCollector
        collector = SignalFeedCollector(vault_dir=get_vault_dir())
        output = collector.import_snapshot(Path(signal_import), signal_target)
        print_success(f"외부 신호 snapshot import 완료: {output}")
    elif signal_import_url:
        from auto_agent.modules.data_collector.signal_feed_collector import SignalFeedCollector
        collector = SignalFeedCollector(vault_dir=get_vault_dir())
        output = collector.import_snapshot_url(signal_import_url, signal_target, name=signal_name)
        print_success(f"외부 신호 URL import 완료: {output}")
    else:
        print_error("Usage: auto-agent collect [--all|--competitors|--trending|--signals|--signals-import <file> --target <market/social|market/communities|market/news> | --signals-import-url <url> --target <market/social|market/communities|market/news> [--name <snapshot-name>]]")


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


def cmd_plan_trend(args):
    """주제 기획 (Stage 0 — trend-analyst)."""
    from auto_agent.modules.agent_runner import AgentRunner

    channel = "이로미즘"
    seed = None
    autoresearch = False
    max_rounds = 5
    provider = None

    for i, arg in enumerate(args):
        if arg == "--channel" and i + 1 < len(args):
            channel = args[i + 1]
        elif arg == "--seed" and i + 1 < len(args):
            seed = args[i + 1]
        elif arg == "--autoresearch":
            autoresearch = True
        elif arg == "--rounds" and i + 1 < len(args):
            max_rounds = int(args[i + 1])
        elif arg == "--provider" and i + 1 < len(args):
            provider = args[i + 1]

    if autoresearch:
        mode = f"AutoResearch ({max_rounds}라운드)"
    elif seed:
        mode = "시드 모드"
    else:
        mode = "자율 모드"

    print_header(f"Auto Agent — 주제 기획 ({mode})")
    console.print(f"  채널: [accent]{channel}[/accent]")
    if provider:
        console.print(f"  provider: [accent]{provider}[/accent]")
    if seed:
        console.print(f"  시드: [accent]{seed}[/accent]")
    if autoresearch:
        console.print(f"  모드: [accent]카파시 AutoResearch 루프[/accent]")

    runner = AgentRunner(provider=provider)
    result = runner.run_trend_analyst(
        channel=channel, seed=seed,
        autoresearch=autoresearch, max_rounds=max_rounds,
    )

    if result["status"] == "success":
        print_success("기획안 생성 완료")
        _notify_plan_result(channel, mode)
    else:
        print_error(f"기획안 생성 실패: {result.get('stderr', '')[:200]}")


def cmd_analyze(args):
    """성과 분석 (Stage 4 — performance-analyst)."""
    from auto_agent.modules.agent_runner import AgentRunner

    channel = "이로미즘"
    video_id = None
    weekly = False
    provider = None

    for i, arg in enumerate(args):
        if arg == "--channel" and i + 1 < len(args):
            channel = args[i + 1]
        elif arg == "--video" and i + 1 < len(args):
            video_id = args[i + 1]
        elif arg == "--weekly":
            weekly = True
        elif arg == "--provider" and i + 1 < len(args):
            provider = args[i + 1]

    if not video_id and not weekly:
        print_error("Usage: auto-agent analyze [--video <id> | --weekly] --channel <name>")
        sys.exit(1)

    mode = "weekly" if weekly else "video"
    label = "주간 리뷰" if weekly else f"영상 분석 ({video_id})"
    print_header(f"Auto Agent — {label}")
    console.print(f"  채널: [accent]{channel}[/accent]")
    if provider:
        console.print(f"  provider: [accent]{provider}[/accent]")

    runner = AgentRunner(provider=provider)
    result = runner.run_performance_analyst(mode=mode, channel=channel, video_id=video_id)

    if result["status"] == "success":
        print_success(f"{label} 완료")
        import os
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        if webhook:
            from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier
            notifier = DiscordNotifier(webhook_url=webhook)
            notifier.send(f"📊 **{channel} {label} 완료**\n→ 볼트 확인")
    else:
        print_error(f"분석 실패: {result.get('stderr', '')[:200]}")


def cmd_cron(args):
    """cron 스케줄 설정 (인텔리전스 루프)."""
    if not args or args[0] == "setup":
        workspace = str(get_workspace_dir())
        python = sys.executable
        from auto_agent.scripts.setup_cron import setup_cron
        setup_cron(workspace, python)
    elif args[0] == "list":
        import subprocess
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        console.print(result.stdout if result.returncode == 0 else "crontab 비어있음")
    elif args[0] == "remove":
        from auto_agent.scripts.setup_cron import remove_cron
        remove_cron()
    else:
        print_error("Usage: auto-agent cron [setup|list|remove]")


def cmd_auto_kairos(args):
    """원클릭 영상 제작 — 스타일 선택 → 주제 선택 → 프로젝트 생성 → 파이프라인 실행."""
    from auto_agent.scripts.project_paths import slugify

    # ── 채널↔아트스타일 매핑 ──
    CHANNEL_STYLES = {
        "이로미즘": "quirky_cartoon",
        "세모지": "semoji",
    }

    print_header("Auto Kairos — 원클릭 영상 제작")
    console.print()

    dur = None  # 커스텀 모드에서만 사용

    # ═══════════════════════════════════════════════
    # Step 1: 아트스타일 선택
    # ═══════════════════════════════════════════════
    styles_dir = get_data_dir() / "artstyle" / "styles"
    style_files = sorted(styles_dir.glob("*.json"))
    style_map = {}
    for sf in style_files:
        try:
            d = json.loads(sf.read_text(encoding="utf-8"))
            style_map[sf.stem] = d.get("name", sf.stem)
        except Exception:
            pass

    console.print("  [bold]Step 1.[/bold] 아트스타일 선택\n")
    console.print("    1. 이로미즘 (quirky_cartoon)")
    console.print("    2. 세모지 (semoji)")
    console.print("    3. 커스텀 (직접 지정)")
    console.print()

    choice = input("  선택 [1/2/3, 기본=1]: ").strip() or "1"

    if choice == "1":
        channel = "이로미즘"
        art_style = "quirky_cartoon"
        writing_style = "iromism"
    elif choice == "2":
        channel = "세모지"
        art_style = "semoji"
        writing_style = "semoji"
    elif choice == "3":
        channel = None
        art_style = None
        writing_style = None
        # 커스텀: 스타일 목록 표시
        console.print("\n  사용 가능한 스타일:")
        style_keys = list(style_map.keys())
        for i, key in enumerate(style_keys, 1):
            console.print(f"    {i}. {style_map[key]} ({key})")
        sidx = input(f"\n  스타일 번호 [1-{len(style_keys)}]: ").strip()
        try:
            art_style = style_keys[int(sidx) - 1]
        except (ValueError, IndexError):
            print_error("잘못된 선택입니다.")
            sys.exit(1)
    else:
        print_error(f"잘못된 선택: {choice}")
        sys.exit(1)

    console.print(f"\n  → 스타일: [accent]{art_style}[/accent]"
                  + (f"  채널: [accent]{channel}[/accent]" if channel else ""))
    console.print()

    # ═══════════════════════════════════════════════
    # Step 2: 주제 선택
    # ═══════════════════════════════════════════════
    topic = None
    plan_path = None

    if channel in ("이로미즘", "세모지"):
        # 2A: 볼트 기획안에서 추천 주제 로드
        console.print(f"  [bold]Step 2.[/bold] 주제 선택 ({channel} 추천)\n")
        candidates = _load_vault_candidates(channel)

        if candidates:
            for i, c in enumerate(candidates[:5], 1):
                score = c.get("topic_score", c.get("score", "?"))
                title = c.get("title", "")
                brief = c.get("creative_brief", {})
                angle = brief.get("core_angle", c.get("angle", ""))[:60]
                urgency = brief.get("urgency", "")
                console.print(f"    [bold]{i}.[/bold] [{score}점] {title}")
                if angle:
                    console.print(f"       [dim]{angle}...[/dim]")
                if urgency:
                    console.print(f"       [yellow]{urgency}[/yellow]")
                console.print()

            console.print(f"    {len(candidates[:5]) + 1}. 직접 입력")
            console.print()
            tidx = input(f"  선택 [1-{len(candidates[:5]) + 1}, 기본=1]: ").strip() or "1"

            try:
                idx = int(tidx) - 1
                if 0 <= idx < len(candidates[:5]):
                    selected = candidates[idx]
                    topic = selected.get("title", "")
                    # 기획안 경로 찾기
                    plan_path = _find_plan_path(channel)
                else:
                    topic = None  # 직접 입력으로
            except (ValueError, IndexError):
                topic = None

        if not topic:
            topic = input("  주제를 입력하세요: ").strip()
            if not topic:
                print_error("주제가 필요합니다.")
                sys.exit(1)
    else:
        # 2B: 커스텀 — 직접 입력
        console.print("  [bold]Step 2.[/bold] 주제 및 설정\n")
        topic = input("  주제를 입력하세요: ").strip()
        if not topic:
            print_error("주제가 필요합니다.")
            sys.exit(1)
        dur = input("  영상 길이 (분, 기본=10): ").strip() or "10"

    console.print(f"\n  → 주제: [accent]{topic}[/accent]")
    console.print()

    # ═══════════════════════════════════════════════
    # Step 3: 프로젝트 생성 + 파이프라인 실행
    # ═══════════════════════════════════════════════
    console.print("  [bold]Step 3.[/bold] 프로젝트 생성 & 파이프라인 시작\n")

    slug = slugify(topic)
    config = {"art_style": art_style}
    if writing_style:
        config["writing_style"] = writing_style
    if choice == "3" and dur:
        try:
            config["duration_minutes"] = int(dur)
        except ValueError:
            pass

    # DB에 프로젝트 생성
    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()

    # 기존 프로젝트 재사용 — 같은 slug가 있으면 새로 만들지 않음
    existing = pm.get_project(slug=slug)
    if existing:
        console.print(f"  [yellow]기존 프로젝트 재사용: {slug} (id={existing['id']})[/yellow]")
        pid = existing["id"]
    else:
        pid = pm.create_project(
            name=topic[:50],
            slug=slug,
            topic=topic,
            config=config,
            channel=channel,
        )
        print_success(f"프로젝트 생성: [accent]{slug}[/accent]")

    # 파이프라인 실행
    _run_pipeline(slug)


def _load_vault_candidates(channel: str) -> list:
    """볼트 insights/planning/ 에서 최신 autoresearch JSON의 candidates를 로드."""
    import unicodedata

    try:
        from auto_agent.paths import get_vault_dir
        vault = get_vault_dir()
    except Exception:
        # 환경변수 미설정 시 하드코딩 폴백
        vault = Path("/Volumes/kairos/kairos_vault/kairos-vault")

    planning_dir = vault / "insights" / "planning"
    if not planning_dir.exists():
        return []

    # 채널명으로 필터링, 날짜 내림차순
    channel_tag = unicodedata.normalize("NFC", channel)
    research_files = sorted(
        [
            path for path in planning_dir.glob("*-autoresearch.json")
            if channel_tag in unicodedata.normalize("NFC", path.name)
        ],
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )

    if not research_files:
        return []

    latest = research_files[0]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        candidates = data.get("candidates", [])
        # topic_score 내림차순 정렬
        candidates.sort(key=lambda c: c.get("topic_score", 0), reverse=True)
        return candidates[:5]
    except Exception:
        return []


def _format_autoresearch_summary(channel: str, candidates: list, limit: int = 5) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📋 **[{today}] {channel} AutoResearch 결과**", ""]
    for idx, candidate in enumerate(candidates[:limit], start=1):
        score = candidate.get("topic_score", 0)
        title = candidate.get("title", "")
        hook = candidate.get("hook", "")
        bridge = candidate.get("bridge_reason", "")
        timing = candidate.get("timing_window", "")
        lines.append(f"**{idx}. [{score}점] {title}**")
        if hook:
            lines.append(f"훅: {hook}")
        if timing:
            lines.append(f"타이밍: {timing}")
        if bridge:
            lines.append(f"브리지: {bridge[:220]}")
        lines.append("")
    return "\n".join(lines).strip()


def _notify_plan_result(channel: str, mode: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook:
        return

    summary = _format_autoresearch_summary(channel, _load_vault_candidates(channel))
    completion = f"📋 **{channel} 기획안 생성 완료** ({mode})\n→ 볼트 insights/planning/ 확인"

    stage0_channel_id = (
        os.getenv("DISCORD_STAGE0_CHANNEL_ID", "").strip()
        or os.getenv("TEAM_DISCORD_CHANNEL_ID", "").strip()
    )
    if stage0_channel_id:
        try:
            from auto_agent.modules.discord_bot_notify import DiscordBotNotify
            bot = DiscordBotNotify(channel_id=stage0_channel_id)
            thread_name = f"[{datetime.now().strftime('%Y-%m-%d')}] {channel} AutoResearch"
            thread_id = bot.create_thread(thread_name)
            if thread_id:
                bot.send_to_thread(summary)
                bot.send_to_channel(f"✅ **{channel} 기획안 생성 완료** — 스레드에서 상세 결과 확인")
                return
        except Exception:
            pass

    from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier
    notifier = DiscordNotifier(webhook_url=webhook)
    notifier.send(completion)
    if summary:
        notifier.send(summary)


def _find_plan_path(channel: str) -> str | None:
    """최신 기획안 마크다운 경로 반환."""
    try:
        from auto_agent.paths import get_vault_dir
        vault = get_vault_dir()
    except Exception:
        vault = Path("/Volumes/kairos/kairos_vault/kairos-vault")

    planning_dir = vault / "insights" / "planning"
    if not planning_dir.exists():
        return None

    channel_tag = "이로미즘" if channel == "이로미즘" else "세모지"
    plan_files = sorted(
        planning_dir.glob(f"*-{channel_tag}-기획안.md"),
        reverse=True,
    )
    return str(plan_files[0]) if plan_files else None


def cmd_plan(args):
    """auto-agent plan — 파이프라인 외부 기획안 생성 (v1 + 래칫)"""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent plan")
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--project", required=True, help="프로젝트 slug")
    parser.add_argument("--style", default="", dest="writing_style", help="문체 스타일 (예: semoji)")
    parser.add_argument("--channel", default="", help="채널명")
    parser.add_argument("--overwrite", action="store_true", help="기존 editorial_brief 덮어쓰기")
    parser.add_argument(
        "--mode", choices=["auto", "manual", "skip"], default="auto",
        help="auto: LLM 자가 Q&A로 5대 DNA 레버 포함 v1 생성 (기본). "
             "manual: brief-interviewer 소크라테스 인터뷰 (사용자 대면). "
             "skip: 레거시 간단 초안 (5대 레버 없이 빠르게 생성)."
    )
    parser.add_argument(
        "--no-ratchet", action="store_true",
        help="brief-reviewer 래칫 루프 건너뛰기 (기본: 실행)"
    )
    parser.add_argument(
        "--max-rounds", type=int, default=3,
        help="래칫 루프 최대 라운드 (기본 3)"
    )
    parsed = parser.parse_args(args)

    from auto_agent.modules.content_planner_module import (
        generate_planner_brief,
        generate_auto_brief,
        save_brief,
        save_brief_versioned,
        ratchet_brief_v1,
    )

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    project = pm.resolve_project(parsed.project)
    if not project:
        console.print(f"[red]프로젝트를 찾을 수 없습니다: {parsed.project}[/red]")
        import sys
        sys.exit(1)

    project_dir = Path(project["output_dir"])
    mode = parsed.mode

    # brief_mode를 project_config.json에 기록 (하류 스텝이 참조)
    try:
        config_path = project_dir / "project_config.json"
        if config_path.exists():
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            cfg = {}
        cfg["brief_mode"] = mode
        project_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        console.print(f"[yellow]project_config.json 기록 실패 (계속 진행): {e}[/yellow]")

    console.print(f"[blue]기획안 생성 중...[/blue] 주제: {parsed.topic} / mode: {mode}")

    # 래칫 포함 실행 (auto 모드 + 래칫 활성 시)
    if mode == "auto" and not parsed.no_ratchet:
        feedback = ratchet_brief_v1(
            project_dir=project_dir,
            topic=parsed.topic,
            mode="auto",
            writing_style=parsed.writing_style,
            channel=parsed.channel,
            max_rounds=parsed.max_rounds,
        )
        console.print()
        console.print(f"[green]v1 최종 점수:[/green] {feedback.get('score_total', 0)}/100")
        console.print(f"  verdict: {feedback.get('verdict', '?')}")
        console.print(f"  rounds: {feedback.get('round', 1)}")
        console.print(f"  next_action: {feedback.get('next_action', '?')}")
        console.print()
        console.print(f"[dim]다음 단계: auto-agent run --project {parsed.project}[/dim]")
        return

    # 래칫 없이 단발 생성
    if mode == "auto":
        brief = generate_auto_brief(
            topic=parsed.topic,
            writing_style=parsed.writing_style,
            channel=parsed.channel,
        )
    else:
        # manual: 기본 planner 초안 (사용자가 이후 편집)
        # skip: 간단 초안
        brief = generate_planner_brief(
            topic=parsed.topic,
            writing_style=parsed.writing_style,
            channel=parsed.channel,
        )

    try:
        path = save_brief_versioned(brief, project_dir, version="v1",
                                    overwrite=parsed.overwrite)
        console.print(f"[green]기획안 저장 완료:[/green] {path}")
        console.print(f"  core_question: {brief.get('core_question', '')}")
        console.print(f"  tone_goal: {brief.get('tone_goal', '')}")
        must_cover = brief.get("must_cover", [])
        if must_cover:
            console.print(f"  must_cover ({len(must_cover)}개):")
            for item in must_cover:
                console.print(f"    - {item}")
        console.print()
        console.print(f"[dim]다음 단계: auto-agent run --project {parsed.project}[/dim]")
    except FileExistsError as e:
        console.print(f"[red]{e}[/red]")


def cmd_series(args):
    """장편 시리즈 모드: plan, run."""
    import argparse

    parser = argparse.ArgumentParser(prog="auto-agent series", description="장편 시리즈 모드")
    series_sub = parser.add_subparsers(dest="series_cmd")

    # series plan
    sp_plan = series_sub.add_parser("plan", help="시리즈 기획안 생성")
    sp_plan.add_argument("--topic", required=True, help="시리즈 주제 (예: LG 브랜드 역사)")
    sp_plan.add_argument("--channel", default="세모지", help="채널명")
    sp_plan.add_argument("--style", default="semoji", dest="writing_style", help="문체 스타일")
    sp_plan.add_argument("--episodes", type=int, default=8, dest="total_episodes", help="총 편수")
    sp_plan.add_argument("--out", required=True, help="series_plan.json 저장 경로")

    # series run
    sp_run = series_sub.add_parser("run", help="시리즈 전편 Stage 2까지 실행")
    sp_run.add_argument("--plan", required=True, help="series_plan.json 경로")
    sp_run.add_argument("--output-dir", required=True, dest="output_dir", help="시리즈 출력 루트 디렉토리")
    sp_run.add_argument("--dry-run", action="store_true", dest="dry_run", help="실제 실행 없이 구조만 생성")

    parsed = parser.parse_args(args)

    if not parsed.series_cmd:
        parser.print_help()
        return

    if parsed.series_cmd == "plan":
        from auto_agent.modules.series_planner_module import (
            generate_series_plan_from_topic,
            save_series_plan,
            validate_series_plan,
        )
        plan = generate_series_plan_from_topic(
            topic=parsed.topic,
            channel=parsed.channel,
            writing_style=parsed.writing_style,
            total_episodes=parsed.total_episodes,
        )
        errors = validate_series_plan(plan)
        if errors:
            console.print(f"[red]기획안 검증 오류:[/red] {errors}")
        else:
            save_series_plan(plan, Path(parsed.out))
            console.print(f"[green]시리즈 기획안 저장:[/green] {parsed.out}")
            console.print(f"  편수: {plan['total_episodes']}편")
            for ep in plan.get("episodes", []):
                console.print(f"  EP{ep['episode_number']:02d}: {ep['title']}")

    elif parsed.series_cmd == "run":
        from auto_agent.modules.series_planner_module import load_series_plan
        from auto_agent.orchestrator.series_runner import series_run
        plan = load_series_plan(Path(parsed.plan))
        result = series_run(
            plan,
            output_base=Path(parsed.output_dir),
            dry_run=parsed.dry_run,
        )
        console.print(f"[green]시리즈 실행 완료:[/green]")
        console.print(f"  완료: {result['episodes_completed']}편")
        if result["episodes_failed"]:
            console.print(f"  [red]실패: EP{result['episodes_failed']}[/red]")


def cmd_video(args):
    """씬 연출용 비디오 검색 + Gemini 분석.

    하위 명령:
      search   --query <q> [--limit 10]
      analyze  --video-id <id> [--video-id <id2> ...] [--force]
      list
    """
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent video")
    sub = parser.add_subparsers(dest="video_cmd")

    sp = sub.add_parser("search", help="yt-dlp 검색 + 적합도 재정렬 (Gemini X)")
    sp.add_argument("--query", required=True)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--max-duration", type=int, default=None, help="초 단위, 이보다 길면 제외")
    sp.add_argument("--min-duration", type=int, default=None, help="초 단위, 이보다 짧으면 제외")
    sp.add_argument("--keywords", default=None, help="쉼표 구분 토큰 — 적합도 재정렬용")
    sp.add_argument("--full-desc", action="store_true", help="설명 전문 표시")

    sp = sub.add_parser("scene-search", help="씬 → 자동 쿼리 + 키워드 → search")
    sp.add_argument("--project", help="프로젝트 slug")
    sp.add_argument("--scene-specs", help="scene_specs.json 경로 (project 대신)")
    grp = sp.add_mutually_exclusive_group(required=True)
    grp.add_argument("--scene-id")
    grp.add_argument("--scene-index", type=int)
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--max-duration", type=int, default=1800)
    sp.add_argument("--min-duration", type=int, default=30)
    sp.add_argument("--extra-query", default=None, help="자동 쿼리에 덧붙일 키워드")
    sp.add_argument("--full-desc", action="store_true")

    sp = sub.add_parser("analyze", help="선택한 video_id 다운로드 + Gemini 분석")
    sp.add_argument("--video-id", action="append", required=True, dest="video_ids")
    sp.add_argument("--force", action="store_true", help="캐시 무시하고 재분석")

    sub.add_parser("list", help="캐시된 클립 목록")

    parsed = parser.parse_args(args)
    if not parsed.video_cmd:
        parser.print_help()
        return

    from auto_agent.tools import video_search

    def _print_results(results, full_desc=False):
        for i, r in enumerate(results, 1):
            risk = r["license"]["risk"]
            risk_color = {"low": "green", "high": "red", "unknown": "yellow"}.get(risk, "white")
            dur = r.get("duration_sec") or 0
            mins = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "?:??"
            views = f"{r.get('view_count') or 0:,}"
            score = r.get("_relevance_score")
            score_str = f" 적합도={score:.1f}" if score is not None else ""
            console.print(f"[bold]{i:2d}. {r['title']}[/bold]{score_str}")
            console.print(f"    {r['channel']} · {mins} · {views} views")
            console.print(f"    id=[cyan]{r['video_id']}[/cyan]  "
                          f"라이선스=[{risk_color}]{r['license']['label']}[/{risk_color}] "
                          f"({r['license']['note']})")
            if full_desc and r.get("description_snippet"):
                console.print(f"    [dim]{r['description_snippet']}[/dim]")
            console.print(f"    {r['url']}\n")

    if parsed.video_cmd == "search":
        kw = set(k.strip() for k in (parsed.keywords or "").split(",") if k.strip()) or None
        results = video_search.search(
            parsed.query, limit=parsed.limit,
            max_duration=parsed.max_duration,
            min_duration=parsed.min_duration,
            keywords=kw,
        )
        if not results:
            print_warning("검색 결과 없음 (필터 후)")
            return
        console.print(f"\n[accent]'{parsed.query}'[/accent] — {len(results)}개 후보\n")
        _print_results(results, full_desc=parsed.full_desc)
        print_success("분석할 video_id 선택 후: auto-agent video analyze --video-id <id>")

    elif parsed.video_cmd == "scene-search":
        scene, results = video_search.search_for_scene(
            project_slug=parsed.project,
            scene_specs_path=parsed.scene_specs,
            scene_id=parsed.scene_id,
            scene_index=parsed.scene_index,
            limit=parsed.limit,
            max_duration=parsed.max_duration,
            min_duration=parsed.min_duration,
            extra_query=parsed.extra_query,
        )
        head = scene.get("headline") or scene.get("scene_id") or "(no headline)"
        console.print(f"\n[accent]씬: {head}[/accent]")
        narr = (scene.get("narration") or "")[:200]
        if narr:
            console.print(f"  [dim]{narr}[/dim]\n")
        if not results:
            print_warning("검색 결과 없음")
            return
        console.print(f"  → {len(results)}개 후보\n")
        _print_results(results, full_desc=parsed.full_desc)

    elif parsed.video_cmd == "analyze":
        for vid in parsed.video_ids:
            console.print(f"  [dim]{vid}: 다운로드+분석...[/dim]")
            try:
                result = video_search.analyze(vid, force=parsed.force)
                scenes = result.get("analysis", {}).get("scenes", [])
                print_success(f"{vid} 완료 — {len(scenes)} 장면")
            except Exception as e:
                print_error(f"{vid} 실패: {e}")

    elif parsed.video_cmd == "list":
        items = video_search.list_cached()
        if not items:
            console.print("[dim]캐시된 클립 없음[/dim]")
            return
        for it in items:
            mark = "✓" if it["analyzed"] else "·"
            console.print(f"  {mark} [cyan]{it['video_id']}[/cyan] {it['title'] or ''} "
                          f"({it['license_label']}/{it['license_risk']})")


def cmd_tts(args):
    """TTS 전처리 → 생성 → 자막 생성 일괄 실행."""
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="auto-agent tts")
    parser.add_argument("--project", required=True, help="프로젝트 slug 또는 uuid")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="이미 생성된 씬 스킵 (기본 on)")
    parser.add_argument("--force", action="store_true",
                        help="기존 TTS·자막 파일 무시하고 전체 재생성")
    parser.add_argument("--workers", type=int, default=3, help="병렬 TTS 생성 수 (기본 3)")
    parser.add_argument("--tts-only", action="store_true", help="TTS 생성만 (자막 생성 스킵)")
    parser.add_argument("--subtitle-only", action="store_true", help="자막 생성만 (TTS 스킵)")
    parsed = parser.parse_args(args)

    # 프로젝트 경로 resolve
    from auto_agent.db.connection import db_exists
    project_dir = None
    if db_exists():
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.resolve_project(parsed.project)
        if project:
            project_dir = Path(project["output_dir"])
    if not project_dir:
        from auto_agent.paths import get_workspace_dir
        project_dir = get_workspace_dir() / "output" / parsed.project
    if not project_dir.exists():
        console.print(f"[red]프로젝트 디렉토리 없음: {project_dir}[/red]")
        return

    skip_existing = not parsed.force

    # ── Phase A: TTS 생성 ──────────────────────────────────────────────────
    if not parsed.subtitle_only:
        import json
        from auto_agent.tools.elevenlabs import ElevenLabsClient

        scene_specs_path = project_dir / "scene_specs.json"
        if not scene_specs_path.exists():
            console.print(f"[red]scene_specs.json 없음: {scene_specs_path}[/red]")
            return
        scene_specs = json.loads(scene_specs_path.read_text(encoding="utf-8"))
        scenes_raw = scene_specs.get("scenes", scene_specs) if isinstance(scene_specs, dict) else scene_specs

        def _make_scene_entry(s, i):
            """narration → original (TTSPreprocessor 적용),
               narration_tts → processed (에이전트 전처리 완료, TTSPreprocessor 스킵)."""
            narration = s.get("narration", "")
            narration_tts = s.get("narration_tts", "")
            entry = {
                "scene_number": s.get("sceneNumber", i + 1),
                "original_script_text": narration,
            }
            if narration_tts.strip():
                entry["processed_script_text"] = narration_tts
            return entry

        storyboard = {
            "project_title": scene_specs.get("title", parsed.project) if isinstance(scene_specs, dict) else parsed.project,
            "scenes": [
                _make_scene_entry(s, i)
                for i, s in enumerate(scenes_raw)
                if s.get("narration", "").strip()
            ],
        }
        total = len(storyboard["scenes"])
        console.print(f"\n[accent]TTS 생성[/accent] — {total}개 씬 (workers={parsed.workers}, skip_existing={skip_existing})")

        # 임시 스토리보드 파일 저장 후 generate_from_storyboard 호출
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(storyboard, tf, ensure_ascii=False)
            tmp_path = Path(tf.name)

        try:
            client = ElevenLabsClient()
            result = client.generate_from_storyboard(
                storyboard_path=tmp_path,
                output_dir=project_dir,
                skip_existing=skip_existing,
                max_workers=parsed.workers,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        ok = sum(1 for r in result.tts_results if r.status == "completed")
        ts_count = sum(1 for r in result.tts_results if r.alignment_path)
        console.print(f"  완료: {ok}/{total}  타임스탬프: {ts_count}개")
        for r in result.tts_results:
            ts = "✓ ts" if r.alignment_path else "  --"
            status = "✓" if r.status == "completed" else "✗"
            console.print(f"  [{status}] 씬 {r.scene_number:03d}  {r.duration:.2f}s  {ts}")

        # tts_results.json 저장 (스토리보드 duration 표시용)
        tts_results_payload = {
            "results": [
                {
                    "scene": r.scene_number,
                    "status": r.status,
                    "duration": r.duration,
                    "alignment_path": str(r.alignment_path) if r.alignment_path else None,
                }
                for r in result.tts_results
            ]
        }
        tts_results_path = project_dir / "tts_results.json"
        with open(tts_results_path, "w", encoding="utf-8") as f:
            json.dump(tts_results_payload, f, ensure_ascii=False, indent=2)
        console.print(f"  [dim]tts_results.json 저장완료 ({len(result.tts_results)}건)[/dim]")

    # ── Phase B: 자막 생성 ────────────────────────────────────────────────
    if not parsed.tts_only:
        import subprocess, sys
        console.print(f"\n[accent]자막 생성[/accent]")
        env = os.environ.copy()
        env["PROJECT_DIR"] = str(project_dir)
        proc = subprocess.run(
            [sys.executable, "-m", "auto_agent.scripts.generate_subtitles"],
            env=env,
        )
        if proc.returncode != 0:
            console.print("[red]자막 생성 실패[/red]")
        else:
            console.print("[green]자막 생성 완료[/green]")


def cmd_multi_contents(args):
    """멀티포맷 콘텐츠 생성 — 쇼츠/블로그/카드뉴스/스레드 + SNS 스케줄."""
    import argparse

    parser = argparse.ArgumentParser(prog="auto-agent multi-contents")
    parser.add_argument("--project", required=True, help="프로젝트 slug 또는 uuid")
    parsed = parser.parse_args(args)

    # 1. 프로젝트 resolve
    from auto_agent.db.project_manager import ProjectManager

    pm = ProjectManager()
    project = pm.resolve_project(parsed.project)
    if not project:
        print_error(f"프로젝트를 찾을 수 없습니다: {parsed.project}")
        sys.exit(1)

    slug = project["slug"]
    project_dir = Path(project["output_dir"])

    # 2. 필수 파일 존재 확인
    scene_specs = project_dir / "scene_specs.json"
    manifest = project_dir / "remotion" / "public" / "manifest.json"
    if not manifest.exists():
        manifest = project_dir / "manifest.json"

    if not scene_specs.exists():
        print_error(f"scene_specs.json 이 없습니다: {scene_specs}")
        console.print("  파이프라인 Stage 2까지 먼저 실행하세요.")
        sys.exit(1)
    if not manifest.exists():
        print_error(f"manifest.json 이 없습니다")
        console.print("  파이프라인 Stage 3까지 먼저 실행하세요.")
        sys.exit(1)

    # 3. multi-contents 출력 디렉토리 생성
    multi_dir = project_dir / "multi-contents"
    multi_dir.mkdir(parents=True, exist_ok=True)

    print_header("Multi-Contents — 멀티포맷 콘텐츠 생성")
    console.print(f"  프로젝트: [accent]{slug}[/accent]")
    console.print(f"  출력 경로: [accent]{multi_dir}[/accent]")
    console.print()

    # 4. 스킬 파일 로드
    skill_path = get_data_dir() / "skills" / "agents" / "multi-contents-director" / "SKILL.md"
    if not skill_path.exists():
        print_error(f"스킬 파일을 찾을 수 없습니다: {skill_path}")
        sys.exit(1)
    skill_text = skill_path.read_text(encoding="utf-8")

    # 5. 입력 파일들 수집
    specs_text = scene_specs.read_text(encoding="utf-8")
    manifest_text = manifest.read_text(encoding="utf-8")

    research_report = project_dir / "research_report.json"
    research_text = ""
    if research_report.exists():
        research_text = research_report.read_text(encoding="utf-8")

    upload_info = project_dir / "upload_info.json"
    upload_text = ""
    if upload_info.exists():
        upload_text = upload_info.read_text(encoding="utf-8")

    # 5.5. TTS 결과에서 씬별 duration 추출 (쇼츠 타임코드 기반 분할용)
    tts_results_path = project_dir / "tts_results.json"
    scene_duration_text = ""
    if tts_results_path.exists():
        tts_data = json.loads(tts_results_path.read_text(encoding="utf-8"))
        tts_lines = []
        cumulative = 0.0
        for r in tts_data.get("results", []):
            sn = r.get("scene", 0)
            dur = r.get("duration", 0)
            tts_lines.append(f"씬{sn}: {dur:.1f}초 (누적: {cumulative:.0f}-{cumulative+dur:.0f}초)")
            cumulative += dur
        if tts_lines:
            scene_duration_text = (
                f"# 씬별 오디오 길이 (TTS 기준)\n"
                f"총 {cumulative:.0f}초 ({cumulative/60:.1f}분)\n\n"
                + "\n".join(tts_lines)
                + "\n\n⚠️ 쇼츠 분할 시 반드시 이 duration을 참고하여 30~60초 구간으로 묶으세요.\n"
                  "씬 수가 아닌 **실제 오디오 길이 합산**이 30~60초가 되어야 합니다."
            )

    # 6. 프롬프트 구성
    prompt_parts = [
        f"# SKILL\n{skill_text}",
        f"# scene_specs.json\n```json\n{specs_text}\n```",
        f"# manifest.json\n```json\n{manifest_text}\n```",
    ]
    if scene_duration_text:
        prompt_parts.append(scene_duration_text)
    if research_text:
        prompt_parts.append(f"# research_report.json\n```json\n{research_text}\n```")
    if upload_text:
        prompt_parts.append(f"# upload_info.json\n```json\n{upload_text}\n```")

    # 기존 완료 파일 스캔
    existing = [f.name for f in multi_dir.iterdir() if f.is_file()] if multi_dir.exists() else []
    resume_note = ""
    if existing:
        resume_note = (
            f"\n\n## 이미 완성된 파일 (스킵)\n"
            f"{', '.join(existing)}\n"
            f"위 파일은 이미 완성되었으므로 건너뛰고, 아직 생성되지 않은 파일부터 진행하세요."
        )

    prompt_parts.append(
        f"\n프로젝트 '{slug}'의 멀티포맷 콘텐츠를 생성하세요. "
        f"출력 경로: {multi_dir}"
        f"{resume_note}"
    )
    prompt = "\n\n".join(prompt_parts)

    # 7. Claude CLI 실행
    cli_path = shutil.which("claude") or os.environ.get("CLAUDE_CLI", "claude")
    console.print("  [accent]Claude CLI[/accent] multi-contents-director 실행 중...")
    console.print()

    result = subprocess.run(
        [
            cli_path, "-p", prompt,
            "--allowedTools", "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "--model", "claude-sonnet-4-5-20250929",
            "--max-turns", "80",
        ],
        cwd=str(project_dir),
        env={**os.environ},
    )

    if result.returncode == 0:
        print_success("멀티포맷 콘텐츠 생성 완료!")
        console.print(f"  결과: [accent]{multi_dir}[/accent]")
        # JSON 유효성 검사
        _validate_multi_contents(multi_dir)
    else:
        print_error(f"multi-contents-director 실행 실패 (exit code: {result.returncode})")
        sys.exit(1)


def _validate_multi_contents(multi_dir: Path):
    """multi-contents 출력 JSON 파일 유효성 검사."""
    import json as _json
    for f in multi_dir.glob("*.json"):
        try:
            _json.loads(f.read_text(encoding="utf-8"))
            console.print(f"  ✓ {f.name}")
        except _json.JSONDecodeError as e:
            print_warning(f"  ✗ {f.name} — JSON 에러: {e}")

    expected = ["shorts_manifest.json", "card_news.json", "threads_post.json", "sns_schedule.json"]
    missing = [n for n in expected if not (multi_dir / n).exists()]
    if missing:
        print_warning(f"  미생성 파일: {', '.join(missing)}")
    if (multi_dir / "blog.md").exists():
        console.print(f"  ✓ blog.md")
    else:
        print_warning(f"  ✗ blog.md 미생성")


def _run_pipeline(slug: str):
    """파이프라인을 백그라운드로 실행."""
    console.print()
    console.print("  파이프라인을 시작합니다...")
    console.print(f"  [dim]auto-agent run --project {slug}[/dim]\n")

    from auto_agent.orchestrator.runner import PipelineRunner
    runner = PipelineRunner(slug)
    runner.run()


def cmd_vault_sync(args):
    """프로젝트 wiki/claims를 볼트(02-research)로 push. Phase 4 — research-redesign spec.

    옵션:
      --project <slug|uuid>   대상 프로젝트
      --dry-run               write 안 하고 변경사항만 출력
      --force                 confidence 낮아도 진행
      --queue-only            NAS 호출 안 하고 큐에만 추가
      --process-queue         이전 큐 항목 재시도
    """
    import argparse
    from auto_agent.research.vault_sync import sync_project_to_vault, SyncOptions
    from auto_agent.research.vault_sync_queue import (
        VaultSyncLock, enqueue, list_queue, mark_stale, pop_next, dispose,
    )
    from auto_agent.db.project_manager import ProjectManager

    parser = argparse.ArgumentParser(prog="auto-agent vault-sync")
    parser.add_argument("--project", help="프로젝트 slug 또는 uuid")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--queue-only", action="store_true", dest="queue_only")
    parser.add_argument("--process-queue", action="store_true", dest="process_queue")
    parser.add_argument("--list-queue", action="store_true", dest="list_queue_only")
    ns = parser.parse_args(args)

    # --list-queue: 큐 항목만 출력
    if ns.list_queue_only:
        items = list_queue()
        if not items:
            console.print("[dim]큐 비어있음[/dim]")
            return
        console.print(f"[accent]큐 항목 {len(items)}개[/accent]")
        for p in items:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                console.print(f"  • {p.name} — {data.get('project_slug', '?')}")
            except Exception:
                console.print(f"  • {p.name} (parse 실패)")
        return

    # --process-queue: 큐 비우기 시도
    if ns.process_queue:
        marked = mark_stale(max_age_hours=24)
        if marked:
            console.print(f"[yellow]stale 마킹: {len(marked)}개[/yellow]")
        items = list_queue()
        if not items:
            console.print("[dim]큐 비어있음[/dim]")
            return
        console.print(f"[accent]큐 처리 시작 — {len(items)}개[/accent]")
        with VaultSyncLock(timeout=5) as locked:
            if not locked:
                print_error("다른 sync가 진행 중. 잠시 후 재시도.")
                sys.exit(1)
            for item_path in items:
                try:
                    data = json.loads(item_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                slug = data.get("project_slug", "")
                pm = ProjectManager()
                proj = pm.get_project(slug=slug) or pm.get_project(uuid=slug)
                if not proj:
                    console.print(f"[yellow]  ⚠ {slug} — 프로젝트 없음, dispose[/yellow]")
                    dispose(item_path)
                    continue
                proj_dir = Path(proj.get("output_dir", ""))
                opts = SyncOptions(force=ns.force)
                result = sync_project_to_vault(proj_dir, options=opts)
                if result.queued:
                    console.print(f"[yellow]  ⚠ {slug} — 다시 큐로 ({result.queue_reason})[/yellow]")
                    continue  # dispose 안 함
                console.print(f"[green]  ✓ {slug} — {len(result.topics)}개 토픽[/green]")
                dispose(item_path)
        return

    # 일반 sync (--project 필수)
    if not ns.project:
        print_error("--project 또는 --process-queue / --list-queue 필요")
        sys.exit(1)

    pm = ProjectManager()
    proj = pm.get_project(slug=ns.project) or pm.get_project(uuid=ns.project)
    if not proj:
        print_error(f"프로젝트 없음: {ns.project}")
        sys.exit(1)
    proj_dir = Path(proj.get("output_dir", ""))
    if not proj_dir.exists():
        print_error(f"프로젝트 디렉토리 없음: {proj_dir}")
        sys.exit(1)

    options = SyncOptions(
        dry_run=ns.dry_run,
        force=ns.force,
        queue_only=ns.queue_only,
    )

    with VaultSyncLock(timeout=5) as locked:
        if not locked:
            print_error("다른 sync가 진행 중. 잠시 후 재시도.")
            sys.exit(1)
        console.print(f"[accent]볼트 sync 시작[/accent] — {ns.project}")
        if ns.dry_run:
            console.print("[dim](dry-run — 실제 write 안 함)[/dim]")
        result = sync_project_to_vault(proj_dir, options=options)

    if result.queued:
        # 큐에 보관
        enqueue(result.project_slug, {"reason": result.queue_reason})
        console.print(f"[yellow]큐에 보관됨[/yellow] — {result.queue_reason}")
        return

    # 결과 출력
    console.print(f"[green]완료[/green] — vault: {result.vault_root}")
    for r in result.topics:
        ent = r.get("vault_entity_slug", "?")
        mt = r.get("match_type", "?")
        conf = r.get("confidence", 0)
        added = r.get("claims_appended", 0)
        skipped = r.get("claims_skipped", 0)
        wiki = len(r.get("wiki_pages", []))
        runs = r.get("raw_runs_copied", 0)
        errs = len(r.get("errors", []))
        status = "✓" if not r.get("errors") else "⚠"
        console.print(
            f"  {status} {r['project_topic_slug']:30} → {ent:20} "
            f"({mt}, {conf:.2f}) — claims +{added} ~{skipped} / wiki {wiki} / raw {runs} / err {errs}"
        )
    # ledger sync 결과 표시
    if result.ledger or result.ledger_unmatched:
        total_pushed = sum(result.ledger.values())
        console.print(f"\n[accent]✨ Claims Ledger Sync[/accent] — push {total_pushed}건 / unmatched {result.ledger_unmatched}건")
        for entity, n in sorted(result.ledger.items(), key=lambda x: -x[1]):
            if n:
                console.print(f"  → {entity:30} +{n}")

    if result.errors:
        console.print(f"[red]상위 오류 {len(result.errors)}건[/red]")
        for e in result.errors:
            console.print(f"  • {e}")


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
    "vault-sync": cmd_vault_sync,
    "collect": cmd_collect,
    "link": cmd_link,
    "watchlist": cmd_watchlist,
    "plan": cmd_plan,
    "plan-trend": cmd_plan_trend,
    "analyze": cmd_analyze,
    "cron": cmd_cron,
    "sync": cmd_sync,
    "pull": cmd_pull,
    "update": cmd_update,
    "auto-kairos": cmd_auto_kairos,
    "multi-contents": cmd_multi_contents,
    "series": cmd_series,
    "video": cmd_video,
    "tts": cmd_tts,
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
        ("auto-kairos", "원클릭 영상 제작 (스타일→주제→실행)"),
        ("multi-contents --project <slug>", "멀티포맷 콘텐츠 (쇼츠/블로그/카드뉴스)"),
        ("tts --project <slug>", "TTS 전처리·생성·자막 일괄 실행"),
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
