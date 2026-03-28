"""cron 스케줄 자동 설정 — Mac Mini용."""
import subprocess
import sys
from pathlib import Path


MARKER_START = "# === KAIROS INTELLIGENCE LOOP START ==="
MARKER_END = "# === KAIROS INTELLIGENCE LOOP END ==="

CRON_ENTRIES = [
    # KST 05:30 = UTC 20:30 (전일)
    '30 20 * * * cd {workspace} && {python} -m auto_agent.cli collect --all >> {log_dir}/collect.log 2>&1',
    # KST 06:00 이로미즘 = UTC 21:00 (전일)
    '0 21 * * * cd {workspace} && {python} -m auto_agent.cli plan --channel 이로미즘 >> {log_dir}/plan-iromism.log 2>&1',
    # KST 06:10 세모지 = UTC 21:10 (전일)
    '10 21 * * * cd {workspace} && {python} -m auto_agent.cli plan --channel 세모지 >> {log_dir}/plan-semoji.log 2>&1',
    # 일요일 KST 06:00 이로미즘 주간 리뷰 = UTC 21:00 (토요일)
    '0 21 * * 6 cd {workspace} && {python} -m auto_agent.cli analyze --weekly --channel 이로미즘 >> {log_dir}/weekly-iromism.log 2>&1',
    # 일요일 KST 06:10 세모지 주간 리뷰 = UTC 21:10 (토요일)
    '10 21 * * 6 cd {workspace} && {python} -m auto_agent.cli analyze --weekly --channel 세모지 >> {log_dir}/weekly-semoji.log 2>&1',
]


def _get_existing_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _strip_kairos_entries(crontab: str) -> str:
    """기존 인텔리전스 루프 항목만 제거."""
    lines = crontab.split("\n")
    filtered = []
    skip = False
    for line in lines:
        if MARKER_START in line:
            skip = True
            continue
        if MARKER_END in line:
            skip = False
            continue
        if not skip:
            filtered.append(line)
    return "\n".join(filtered)


def setup_cron(workspace: str, python: str = "python3"):
    """cron 엔트리 등록."""
    log_dir = Path(workspace) / "logs" / "intelligence"
    log_dir.mkdir(parents=True, exist_ok=True)

    existing = _get_existing_crontab()
    cleaned = _strip_kairos_entries(existing)

    lines = cleaned.rstrip().split("\n") if cleaned.strip() else []
    lines.append("")
    lines.append(MARKER_START)
    for entry in CRON_ENTRIES:
        lines.append(
            entry.format(
                workspace=workspace,
                python=python,
                log_dir=str(log_dir),
            )
        )
    lines.append(MARKER_END)

    new_crontab = "\n".join(lines).strip() + "\n"
    proc = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0:
        print(f"✅ cron 등록 완료 ({len(CRON_ENTRIES)}개 스케줄)")
        for entry in CRON_ENTRIES:
            print(f"  {entry.split('{')[0].strip()}")
    else:
        print(f"❌ cron 등록 실패: {proc.stderr}")
        sys.exit(1)


def remove_cron():
    """인텔리전스 루프 cron 항목만 제거."""
    existing = _get_existing_crontab()
    cleaned = _strip_kairos_entries(existing)

    proc = subprocess.run(
        ["crontab", "-"],
        input=cleaned.strip() + "\n",
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0:
        print("✅ 인텔리전스 루프 cron 항목 제거 완료")
    else:
        print(f"❌ cron 제거 실패: {proc.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    python = sys.argv[2] if len(sys.argv) > 2 else "python3"
    setup_cron(workspace, python)
