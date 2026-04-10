"""
tools_routes.py
----------------
fontagent / chartagent 대시보드 연결 라우터.

fontagent: 포트 8123에서 동적 HTTP 서버 실행 → 이 라우터가 자동 시작 + 상태 체크
chartagent: 정적 HTML 갤러리 생성 → /chartagent-dash/ 경로로 서빙
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import socket
import sys
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from auto_agent.paths import get_workspace_dir

router = APIRouter(prefix="/tools", tags=["tools"])

# 환경변수 우선, 없으면 ~/Projects/{name} 기본값
FONTAGENT_ROOT = Path(os.environ.get("FONTAGENT_ROOT", Path.home() / "Projects" / "fontagent"))
CHARTAGENT_ROOT = Path(os.environ.get("CHARTAGENT_ROOT", Path.home() / "Projects" / "chartagent"))
FONTAGENT_PORT = 8123

FONTAGENT_REPO = "https://github.com/semoji-ai/fontagent.git"
CHARTAGENT_REPO = "https://github.com/semoji-ai/chartagent.git"

_fontagent_proc: subprocess.Popen | None = None
_fontagent_lock = threading.Lock()


def _clone_and_install(repo_url: str, target_dir: Path, pip_target: Path) -> bool:
    """리포 클론 + pip install -e 실행. 성공 시 True."""
    try:
        if not target_dir.exists():
            logger.info("클론 중: %s → %s", repo_url, target_dir)
            result = subprocess.run(
                ["git", "clone", repo_url, str(target_dir)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error("git clone 실패: %s", result.stderr[:500])
                return False
        logger.info("pip install -e %s", pip_target)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", "-e", str(pip_target)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            logger.error("pip install 실패: %s", result.stderr[:500])
            return False
        return True
    except Exception as e:
        logger.error("클론/설치 실패: %s", e)
        return False


def _fontagent_is_running() -> bool:
    """포트 8123에 fontagent가 응답하는지 확인."""
    try:
        with socket.create_connection(("127.0.0.1", FONTAGENT_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _start_fontagent_sync() -> bool:
    """fontagent 서버 시작. 없으면 자동 클론 후 시작."""
    global _fontagent_proc
    if _fontagent_is_running():
        return True
    if not FONTAGENT_ROOT.exists():
        logger.info("fontagent 미설치 — 자동 클론+설치 시작")
        ok = _clone_and_install(FONTAGENT_REPO, FONTAGENT_ROOT, FONTAGENT_ROOT)
        if not ok:
            return False
    with _fontagent_lock:
        if _fontagent_is_running():
            return True
        try:
            log_path = FONTAGENT_ROOT / "fontagent_serve.log"
            log_fh = open(log_path, "a")
            _fontagent_proc = subprocess.Popen(
                [
                    sys.executable, "-m", "fontagent.cli",
                    "--root", str(FONTAGENT_ROOT),
                    "serve",
                    "--host", "127.0.0.1",
                    "--port", str(FONTAGENT_PORT),
                ],
                cwd=str(FONTAGENT_ROOT),
                stdout=log_fh,
                stderr=log_fh,
            )
            for _ in range(40):
                if _fontagent_is_running():
                    # vault가 비어있으면 백그라운드로 scan --system 실행
                    _scan_vault_if_empty()
                    return True
                time.sleep(0.1)
            logger.warning("fontagent 서버 시작 타임아웃 — 로그: %s", log_path)
            return False
        except Exception as e:
            logger.error("fontagent 시작 실패: %s", e)
            return False


def _scan_vault_if_empty():
    """vault가 비어있으면 백그라운드로 scan --system 실행."""
    try:
        vault_dir = FONTAGENT_ROOT / "vault"
        if vault_dir.exists() and any(vault_dir.iterdir()):
            return  # vault에 데이터 있으면 스킵
        logger.info("fontagent vault 비어있음 — 백그라운드로 scan --system 시작")
        scan_log = FONTAGENT_ROOT / "fontagent_scan.log"
        scan_fh = open(scan_log, "a")
        subprocess.Popen(
            [
                sys.executable, "-m", "fontagent.cli",
                "--root", str(FONTAGENT_ROOT),
                "scan", "--system",
            ],
            cwd=str(FONTAGENT_ROOT),
            stdout=scan_fh,
            stderr=scan_fh,
        )
        logger.info("scan --system 백그라운드 실행 시작 — 로그: %s", scan_log)
    except Exception as e:
        logger.warning("vault scan 실패 (무시): %s", e)


def _generate_chartagent_dashboard_sync(out_dir: Path) -> dict:
    """chartagent 대시보드 정적 HTML 생성. 없으면 자동 클론 후 생성."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if not CHARTAGENT_ROOT.exists():
        logger.info("chartagent 미설치 — 자동 클론+설치 시작")
        ok = _clone_and_install(CHARTAGENT_REPO, CHARTAGENT_ROOT, CHARTAGENT_ROOT / "src")
        if not ok:
            return {"ok": False, "error": "chartagent 자동 설치 실패. git/pip 로그를 확인하세요."}
    try:
        from chartagent.runners.dashboard_runner import write_chartagent_dashboard
        write_chartagent_dashboard(out_dir)
        return {"ok": True}
    except ImportError:
        pass
    except Exception as e:
        return {"ok": False, "error": str(e)}

    # fallback: subprocess
    try:
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home())}
        import os
        env.update(os.environ)
        result = subprocess.run(
            ["python3", "-m", "chartagent.cli", "dashboard", "--out-dir", str(out_dir)],
            cwd=str(CHARTAGENT_ROOT / "src"),
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr[:500]}
        return {"ok": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "생성 시간 초과 (2분)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 라우트 ───────────────────────────────────────────────────────────────────

_FONTAGENT_PAGE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FontAgent</title>
  <link rel="stylesheet" href="/static/style.css">
  <style>
    .tools-page {{ display:flex; flex-direction:column; height:100vh; margin:0; padding:0; background:#09090b; color:#e4e4e7; }}
    .tools-header {{ padding:14px 20px; border-bottom:1px solid rgba(255,255,255,0.06); display:flex; align-items:center; gap:12px; flex-wrap:wrap; flex-shrink:0; }}
    .tools-header h2 {{ margin:0; font-size:17px; font-weight:700; }}
    .tools-desc {{ margin:0; color:#71717a; font-size:13px; flex:1; }}
    .badge {{ font-size:11px; padding:3px 10px; border-radius:20px; font-weight:600; }}
    .badge-ok {{ background:rgba(34,197,94,0.15); color:#86efac; }}
    .badge-off {{ background:rgba(239,68,68,0.12); color:#fca5a5; }}
    .btn {{ border-radius:6px; padding:5px 14px; cursor:pointer; font-size:12px; border:none; }}
    .btn-primary {{ background:#3b82f6; color:#fff; }}
    .btn-secondary {{ background:rgba(255,255,255,0.08); color:#d4d4d8; border:1px solid rgba(255,255,255,0.12); text-decoration:none; display:inline-block; }}
    .tools-frame {{ border:none; flex:1; width:100%; }}
    .tools-placeholder {{ flex:1; display:flex; align-items:center; justify-content:center; color:#52525b; text-align:center; }}
    #toast {{ position:fixed; bottom:20px; right:20px; background:#ef4444; color:#fff; padding:8px 16px; border-radius:8px; font-size:13px; display:none; }}
  </style>
</head>
<body>
<div class="tools-page">
  <div class="tools-header">
    <a href="/" style="color:#60a5fa; font-size:13px; text-decoration:none;">← 대시보드</a>
    <h2>🔤 FontAgent</h2>
    <p class="tools-desc">한국어 폰트 검색 · 설치 · Remotion export</p>
    <span id="badge" class="{badge_class}">{badge_text}</span>
    {start_btn}
  </div>
  {content}
</div>
<div id="toast"></div>
<script>
async function startServer() {{
  const btn = document.getElementById('start-btn');
  if (btn) {{ btn.disabled = true; btn.textContent = '시작 중...'; }}
  const res = await fetch('/tools/api/fontagent/start', {{method:'POST'}});
  const data = await res.json();
  if (data.running) location.reload();
  else {{
    const t = document.getElementById('toast');
    t.textContent = '서버 시작 실패. 터미널에서 fontagent serve를 확인하세요.';
    t.style.display = 'block';
    setTimeout(() => t.style.display='none', 4000);
    if (btn) {{ btn.disabled = false; btn.textContent = '서버 시작'; }}
  }}
}}
</script>
</body>
</html>"""

_CHARTAGENT_PAGE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ChartAgent</title>
  <style>
    .tools-page {{ display:flex; flex-direction:column; height:100vh; margin:0; padding:0; background:#09090b; color:#e4e4e7; }}
    .tools-header {{ padding:14px 20px; border-bottom:1px solid rgba(255,255,255,0.06); display:flex; align-items:center; gap:12px; flex-wrap:wrap; flex-shrink:0; }}
    .tools-header h2 {{ margin:0; font-size:17px; font-weight:700; }}
    .tools-desc {{ margin:0; color:#71717a; font-size:13px; flex:1; }}
    .btn {{ border-radius:6px; padding:5px 14px; cursor:pointer; font-size:12px; border:none; }}
    .btn-primary {{ background:#3b82f6; color:#fff; }}
    .btn-secondary {{ background:rgba(255,255,255,0.08); color:#d4d4d8; border:1px solid rgba(255,255,255,0.12); text-decoration:none; display:inline-block; }}
    .tools-frame {{ border:none; flex:1; width:100%; }}
    .tools-placeholder {{ flex:1; display:flex; align-items:center; justify-content:center; color:#52525b; text-align:center; }}
    #gen-status {{ padding:10px 20px; color:#fcd34d; font-size:12px; display:none; flex-shrink:0; border-bottom:1px solid rgba(255,255,255,0.04); }}
    #toast {{ position:fixed; bottom:20px; right:20px; padding:8px 16px; border-radius:8px; font-size:13px; display:none; }}
    #toast.ok {{ background:#22c55e; color:#fff; }}
    #toast.err {{ background:#ef4444; color:#fff; }}
  </style>
</head>
<body>
<div class="tools-page">
  <div class="tools-header">
    <a href="/" style="color:#60a5fa; font-size:13px; text-decoration:none;">← 대시보드</a>
    <h2>📊 ChartAgent</h2>
    <p class="tools-desc">차트 종류 및 테마별 미리보기 갤러리</p>
    <button onclick="generateDashboard()" class="btn btn-primary" id="gen-btn">{gen_btn_text}</button>
    {open_btn}
  </div>
  <div id="gen-status">생성 중... (최대 2분 소요)</div>
  {content}
</div>
<div id="toast"></div>
<script>
async function generateDashboard() {{
  const btn = document.getElementById('gen-btn');
  const status = document.getElementById('gen-status');
  btn.disabled = true;
  btn.textContent = '생성 중...';
  status.style.display = 'block';
  try {{
    const res = await fetch('/tools/api/chartagent/generate', {{method:'POST'}});
    const data = await res.json();
    if (data.ok) location.reload();
    else {{
      const t = document.getElementById('toast');
      t.className = 'err';
      t.textContent = '생성 실패: ' + (data.error || '알 수 없는 오류');
      t.style.display = 'block';
      setTimeout(() => t.style.display='none', 6000);
      btn.disabled = false;
      btn.textContent = '재시도';
    }}
  }} catch(e) {{
    alert('오류: ' + e);
    btn.disabled = false;
    btn.textContent = '재시도';
  }} finally {{
    status.style.display = 'none';
  }}
}}
</script>
</body>
</html>"""


@router.get("/fontagent", response_class=HTMLResponse)
async def fontagent_page(request: Request):
    running = await asyncio.to_thread(_fontagent_is_running)
    if running:
        badge_class = "badge badge-ok"
        badge_text = f"서버 실행 중 (포트 {FONTAGENT_PORT})"
        start_btn = f'<a href="http://127.0.0.1:{FONTAGENT_PORT}" target="_blank" class="btn btn-secondary">새 탭에서 열기</a>'
        content = f'<iframe src="http://127.0.0.1:{FONTAGENT_PORT}" class="tools-frame"></iframe>'
    else:
        badge_class = "badge badge-off"
        badge_text = "서버 꺼짐"
        start_btn = '<button id="start-btn" onclick="startServer()" class="btn btn-primary">서버 시작</button>'
        content = '<div class="tools-placeholder"><p>fontagent 서버를 시작하면 여기에 폰트 검색 대시보드가 임베드됩니다.</p></div>'

    html = _FONTAGENT_PAGE.format(
        badge_class=badge_class,
        badge_text=badge_text,
        start_btn=start_btn,
        content=content,
    )
    return HTMLResponse(html)


@router.post("/api/fontagent/start")
async def fontagent_start():
    ok = await asyncio.to_thread(_start_fontagent_sync)
    return JSONResponse({"running": ok})


@router.get("/api/fontagent/status")
async def fontagent_status():
    running = await asyncio.to_thread(_fontagent_is_running)
    return JSONResponse({"running": running})


@router.get("/chartagent", response_class=HTMLResponse)
async def chartagent_page(request: Request):
    out_dir = get_workspace_dir() / "chartagent_dashboard"
    generated = (out_dir / "index.html").exists()

    gen_btn_text = "재생성" if generated else "대시보드 생성"
    open_btn = (
        '<a href="/chartagent-dash/index.html" target="_blank" class="btn btn-secondary">새 탭에서 열기</a>'
        if generated else ""
    )
    content = (
        '<iframe src="/chartagent-dash/index.html" class="tools-frame"></iframe>'
        if generated
        else '<div class="tools-placeholder"><div><p>차트 종류별 · 테마별 갤러리를 생성하려면 위 버튼을 클릭하세요.</p><p style="font-size:12px;color:#52525b">chartagent dashboard 명령으로 정적 HTML 갤러리를 생성합니다.</p></div></div>'
    )

    html = _CHARTAGENT_PAGE.format(
        gen_btn_text=gen_btn_text,
        open_btn=open_btn,
        content=content,
    )
    return HTMLResponse(html)


@router.post("/api/chartagent/generate")
async def chartagent_generate():
    # CHARTAGENT_ROOT 없어도 _generate_chartagent_dashboard_sync 내부에서 자동 클론
    out_dir = get_workspace_dir() / "chartagent_dashboard"
    result = await asyncio.to_thread(_generate_chartagent_dashboard_sync, out_dir)
    return JSONResponse(result)
