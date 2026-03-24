"""Rich 포맷터 -- 테이블, 패널 등."""

import json

from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


# ── 상태 배지 ─────────────────────────────────

_STATUS_STYLE = {
    "created": "[dim]생성됨[/dim]",
    "in_progress": "[yellow]진행중[/yellow]",
    "completed": "[green]완료[/green]",
    "failed": "[red]실패[/red]",
    "archived": "[dim]보관됨[/dim]",
}


# ── 프로젝트 ─────────────────────────────────

def project_table(projects: list) -> Table:
    """프로젝트 목록 테이블."""
    table = Table(box=box.ROUNDED, border_style="#F59E0B", title="프로젝트 목록")
    table.add_column("ID", style="cyan", justify="right", width=4)
    table.add_column("이름", style="white bold")
    table.add_column("상태")
    table.add_column("씬", justify="right")
    table.add_column("Slug", style="dim")

    for p in projects:
        table.add_row(
            str(p["id"]),
            p["name"],
            _STATUS_STYLE.get(p["status"], p["status"]),
            str(p["scene_count"]),
            p["slug"],
        )
    return table


def project_info_panel(project: dict, assets: dict = None) -> Panel:
    """프로젝트 상세 정보 패널."""
    lines = [
        f"[accent]ID:[/accent] {project['id']}",
        f"[accent]Slug:[/accent] {project['slug']}",
        f"[accent]상태:[/accent] {_STATUS_STYLE.get(project['status'], project['status'])}",
        f"[accent]주제:[/accent] {project.get('topic') or '-'}",
        f"[accent]테마:[/accent] {project.get('theme') or 'simple'}",
        f"[accent]씬:[/accent] {project['scene_count']}",
        f"[accent]길이:[/accent] {project.get('total_duration_sec', 0):.1f}s",
        f"[accent]출력:[/accent] {project.get('output_dir') or '-'}",
        f"[accent]생성:[/accent] {project.get('created_at') or '-'}",
        f"[accent]수정:[/accent] {project.get('updated_at') or '-'}",
    ]
    if assets:
        lines.append("")
        lines.append("[accent]에셋:[/accent]")
        for atype, count in sorted(assets.items()):
            lines.append(f"  {atype}: {count}")

    return Panel(
        "\n".join(lines),
        title=project["name"],
        border_style="#F59E0B",
    )


def config_panel(config: dict, project_name: str) -> Panel:
    """프로젝트 config JSON 패널."""
    if not config:
        content = "[dim](설정 없음)[/dim]"
        return Panel(content, title=f"Config: {project_name}", border_style="#F59E0B")
    text = json.dumps(config, ensure_ascii=False, indent=2)
    syntax = Syntax(text, "json", theme="monokai", line_numbers=False)
    return Panel(syntax, title=f"Config: {project_name}", border_style="#F59E0B")


# ── 아트스타일 ────────────────────────────────

def style_table(styles: list) -> Table:
    """아트스타일 테이블. styles = [{name, description, path}, ...]"""
    table = Table(box=box.ROUNDED, border_style="#F59E0B", title="아트스타일 목록")
    table.add_column("#", style="cyan", justify="right", width=3)
    table.add_column("이름", style="white bold")
    table.add_column("설명", style="dim")
    table.add_column("경로", style="dim", max_width=40)

    for i, s in enumerate(styles, 1):
        table.add_row(
            str(i),
            s.get("name", "?"),
            (s.get("description") or "")[:60],
            s.get("path", ""),
        )
    return table


# ── 음성 ──────────────────────────────────────

def voice_table(voices: list) -> Table:
    """음성 프리셋 테이블. voices = [{name, voice_id, description, ...}, ...]"""
    table = Table(box=box.ROUNDED, border_style="#F59E0B", title="음성 프리셋")
    table.add_column("#", style="cyan", justify="right", width=3)
    table.add_column("이름", style="white bold")
    table.add_column("Voice ID", style="dim")
    table.add_column("설명", style="dim")

    for i, v in enumerate(voices, 1):
        vid = v.get("voice_id", "")
        table.add_row(
            str(i),
            v.get("name", "?"),
            f"{vid[:16]}..." if len(vid) > 16 else vid,
            (v.get("description") or "")[:50],
        )
    return table


# ── 비용 ──────────────────────────────────────

def cost_table(total: dict, project_costs: list) -> Table:
    """비용 요약 테이블."""
    table = Table(box=box.ROUNDED, border_style="#F59E0B", title="비용 요약")
    table.add_column("프로젝트", style="white bold")
    table.add_column("실행 횟수", justify="right")
    table.add_column("Input Tokens", justify="right")
    table.add_column("Output Tokens", justify="right")
    table.add_column("USD", justify="right", style="accent")

    # 전체
    table.add_row(
        "[accent]전체[/accent]",
        f"{total.get('total_runs', 0):,}",
        f"{total.get('total_tokens_in', 0):,}",
        f"{total.get('total_tokens_out', 0):,}",
        f"${total.get('total_usd', 0):.4f}",
    )
    table.add_section()

    for name, cost in project_costs:
        if cost.get("total_runs", 0) > 0:
            table.add_row(
                name,
                f"{cost['total_runs']:,}",
                f"{cost.get('total_tokens_in', 0):,}",
                f"{cost.get('total_tokens_out', 0):,}",
                f"${cost.get('total_usd', 0):.4f}",
            )
    return table


# ── 버전 ──────────────────────────────────────

def version_table(versions: list, file_type: str) -> Table:
    """버전 히스토리 테이블."""
    table = Table(
        box=box.ROUNDED, border_style="#F59E0B", title=f"버전: {file_type}"
    )
    table.add_column("버전", style="cyan", justify="right", width=6)
    table.add_column("크기", justify="right")
    table.add_column("생성일", style="dim")
    table.add_column("설명")

    for v in versions:
        size_kb = v["file_size"] / 1024 if v["file_size"] else 0
        table.add_row(
            f"v{v['version']:03d}",
            f"{size_kb:.1f}KB",
            v.get("created_at") or "-",
            v.get("description") or "",
        )
    return table


# ── 에셋 ──────────────────────────────────────

def asset_table(assets: list, counts: dict) -> Table:
    """에셋 목록 테이블."""
    table = Table(box=box.ROUNDED, border_style="#F59E0B", title="에셋 목록")
    table.add_column("유형", style="cyan")
    table.add_column("씬", justify="right")
    table.add_column("파일명", style="white")
    table.add_column("크기", justify="right", style="dim")

    for a in assets:
        size_kb = a["file_size"] / 1024 if a["file_size"] else 0
        scene = f"{a['scene_number']:03d}" if a["scene_number"] else "-"
        table.add_row(
            a.get("asset_type", "?"),
            scene,
            a["file_name"],
            f"{size_kb:.1f}KB",
        )

    if counts:
        table.add_section()
        for atype, count in sorted(counts.items()):
            table.add_row(f"[dim]{atype}[/dim]", "", f"[dim]{count}개[/dim]", "")

    return table
