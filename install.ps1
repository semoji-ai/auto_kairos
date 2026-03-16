# ─────────────────────────────────────────────
# Auto Kairos — 설치 스크립트 (Windows PowerShell)
# ─────────────────────────────────────────────

$ErrorActionPreference = "Stop"

function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  Auto Kairos v3 — AI Video Production Pipeline ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info    { param($msg) Write-Host "▸ $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail    { param($msg) Write-Host "❌ $msg" -ForegroundColor Red; exit 1 }

# ── Python 확인/설치 ──
function Ensure-Python {
    try {
        $ver = python --version 2>&1
        Write-Info "Python 감지됨: $ver"
        $pyVer = python -c "import sys; print(sys.version_info.minor)"
        if ([int]$pyVer -lt 10) {
            Write-Warn "Python 3.10 이상이 필요합니다"
            Write-Info "https://python.org 에서 최신 버전을 설치해주세요"
            exit 1
        }
    } catch {
        Write-Info "Python 설치 중 (winget)..."
        try {
            winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            Write-Success "Python 설치 완료 — 터미널을 재시작해주세요"
            exit 0
        } catch {
            Write-Fail "Python을 수동으로 설치해주세요: https://python.org"
        }
    }
}

# ── Node.js 확인/설치 ──
function Ensure-Node {
    try {
        $ver = node --version 2>&1
        Write-Info "Node.js 감지됨: $ver"
    } catch {
        Write-Info "Node.js 설치 중 (winget)..."
        try {
            winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
            Write-Success "Node.js 설치 완료 — 터미널을 재시작해주세요"
            exit 0
        } catch {
            Write-Fail "Node.js를 수동으로 설치해주세요: https://nodejs.org"
        }
    }
}

# ── ffmpeg 확인/설치 ──
function Ensure-FFmpeg {
    try {
        ffmpeg -version 2>&1 | Out-Null
        Write-Info "ffmpeg 감지됨"
    } catch {
        Write-Info "ffmpeg 설치 중 (winget)..."
        try {
            winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
            Write-Success "ffmpeg 설치 완료"
        } catch {
            Write-Warn "ffmpeg를 수동으로 설치해주세요: https://ffmpeg.org"
        }
    }
}

# ── auto-kairos 패키지 설치 ──
function Install-Package {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (-not $scriptDir) { $scriptDir = $PWD.Path }

    Write-Info "auto-kairos 패키지 설치 중..."
    pip install -e "$scriptDir[all]"
    Write-Success "auto-kairos 패키지 설치 완료"
}

# ── 완료 메시지 ──
function Write-Completion {
    Write-Host ""
    Write-Success "Auto Kairos v3 설치 완료!"
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor White
    Write-Host ""
    Write-Host "  # 새 워크스페이스 만들기" -ForegroundColor DarkGray
    Write-Host "  auto-kairos init C:\Users\$env:USERNAME\my-video-project"
    Write-Host ""
    Write-Host "  # 기존 v2 워크스페이스 업그레이드" -ForegroundColor DarkGray
    Write-Host "  auto-kairos init C:\Users\$env:USERNAME\my-video-project --upgrade"
    Write-Host ""
    Write-Host "  # 워크스페이스에서 Claude Code 실행" -ForegroundColor DarkGray
    Write-Host "  cd ~/my-video-project"
    Write-Host "  claude"
    Write-Host ""
}

# ── 메인 ──
Write-Header
Ensure-Python
Ensure-Node
Ensure-FFmpeg
Write-Host ""
Install-Package
Write-Completion
