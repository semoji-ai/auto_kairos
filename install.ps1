# ─────────────────────────────────────────────
# Auto Kairos v3 — 올인원 설치 스크립트 (Windows PowerShell)
# ─────────────────────────────────────────────

$ErrorActionPreference = "Stop"

function Write-Header {
    Write-Host ""
    Write-Host "+=================================================+" -ForegroundColor Cyan
    Write-Host "|  Auto Kairos v3 - AI Video Production Pipeline    |" -ForegroundColor Cyan
    Write-Host "+=================================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Info    { param($msg) Write-Host "* $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Fail    { param($msg) Write-Host "[X] $msg" -ForegroundColor Red; exit 1 }

# ═══════════════════════════════════════
# Step 1: 시스템 의존성
# ═══════════════════════════════════════

function Ensure-Python {
    try {
        $ver = python --version 2>&1
        $pyMinor = python -c "import sys; print(sys.version_info.minor)" 2>&1
        if ([int]$pyMinor -ge 10) {
            Write-Info "Python $ver [OK]"
            return
        }
        Write-Warn "Python 3.10+ 필요"
    } catch {}
    Write-Info "Python 설치 중..."
    try { winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements }
    catch { Write-Fail "Python을 수동 설치하세요: https://python.org" }
    Write-Success "Python 설치 완료 (터미널 재시작 필요할 수 있음)"
}

function Ensure-Node {
    try { $v = node --version 2>&1; Write-Info "Node.js $v [OK]"; return } catch {}
    Write-Info "Node.js 설치 중..."
    try { winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements }
    catch { Write-Fail "Node.js를 수동 설치하세요: https://nodejs.org" }
    Write-Success "Node.js 설치 완료"
}

function Ensure-FFmpeg {
    try { ffmpeg -version 2>&1 | Out-Null; Write-Info "ffmpeg [OK]"; return } catch {}
    Write-Info "ffmpeg 설치 중..."
    try { winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements }
    catch { Write-Warn "ffmpeg를 수동 설치하세요: https://ffmpeg.org" }
    Write-Success "ffmpeg 설치 완료"
}

# ═══════════════════════════════════════
# Step 2: 패키지 설치
# ═══════════════════════════════════════

function Install-Package {
    $scriptDir = Split-Path -Parent $PSCommandPath
    if (-not $scriptDir) { $scriptDir = $PWD.Path }
    Write-Info "auto-kairos 패키지 설치 중..."
    pip install -e "$scriptDir[all]"
    Write-Success "auto-kairos 설치 완료"
}

# ═══════════════════════════════════════
# Step 3: 워크스페이스 설정
# ═══════════════════════════════════════

function Setup-Workspace {
    Write-Host ""
    Write-Host "-- 워크스페이스 설정 --" -ForegroundColor White
    Write-Host ""

    $default = "$env:USERPROFILE\my-video-project"
    $wsPath = Read-Host "? 워크스페이스 경로 (Enter로 기본값: $default)"
    if ([string]::IsNullOrWhiteSpace($wsPath)) { $wsPath = $default }
    $script:WORKSPACE = (Resolve-Path $wsPath -ErrorAction SilentlyContinue).Path
    if (-not $script:WORKSPACE) { $script:WORKSPACE = $wsPath }

    if ((Test-Path "$script:WORKSPACE\output") -or (Test-Path "$script:WORKSPACE\auto_agent.db")) {
        Write-Info "기존 워크스페이스 감지 -> v2->v3 업그레이드"
        auto-kairos init $script:WORKSPACE --upgrade
    } else {
        Write-Info "새 워크스페이스 생성"
        auto-kairos init $script:WORKSPACE
    }
    Write-Success "워크스페이스 준비 완료: $script:WORKSPACE"
}

# ═══════════════════════════════════════
# Step 4: .env 설정
# ═══════════════════════════════════════

function Setup-Env {
    Write-Host ""
    Write-Host "-- API 키 설정 --" -ForegroundColor White
    Write-Host ""

    $envFile = "$script:WORKSPACE\.env"
    $script:HAS_SUPABASE = $false

    if (Test-Path $envFile) {
        Write-Info "기존 .env 파일 감지"
        $content = Get-Content $envFile -Raw
        if ($content -match 'SUPABASE_URL=.+') {
            Write-Info "Supabase 설정 확인됨"
            $script:HAS_SUPABASE = $true
            return
        }
    } else {
        $example = "$script:WORKSPACE\.env.example"
        if (Test-Path $example) { Copy-Item $example $envFile }
        else { New-Item $envFile -ItemType File | Out-Null }
        Write-Info ".env 파일 생성됨"
    }

    Write-Info "팀 프로젝트 공유를 위해 Supabase 설정이 필요합니다."
    $sbUrl = Read-Host "? Supabase URL (없으면 Enter로 건너뛰기)"

    if (-not [string]::IsNullOrWhiteSpace($sbUrl)) {
        $sbKey = Read-Host "? Supabase Anon Key"
        Add-Content $envFile "`n# Supabase (팀 프로젝트 공유)`nSUPABASE_URL=$sbUrl`nSUPABASE_KEY=$sbKey"
        Write-Success "Supabase 설정 완료"
        $script:HAS_SUPABASE = $true
    } else {
        Write-Info "Supabase 건너뜀 (나중에 .env에서 설정 가능)"
    }

    # 필수 키 안내
    $missing = @()
    $c = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
    if ($c -notmatch 'ELEVENLABS_API_KEY=.+') { $missing += "ELEVENLABS_API_KEY (TTS)" }
    if ($c -notmatch 'OPENAI_API_KEY=.+') { $missing += "OPENAI_API_KEY (자막)" }
    if ($missing.Count -gt 0) {
        Write-Warn "다음 API 키가 설정되지 않았습니다 (나중에 .env 편집):"
        $missing | ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkGray }
    }
}

# ═══════════════════════════════════════
# Step 5: 프로젝트 동기화
# ═══════════════════════════════════════

function Sync-Projects {
    if (-not $script:HAS_SUPABASE) { return }

    Write-Host ""
    Write-Host "-- 프로젝트 동기화 --" -ForegroundColor White
    Write-Host ""

    $outputDir = "$script:WORKSPACE\output"
    $env:AUTO_AGENT_WORKSPACE = $script:WORKSPACE

    # 로컬 -> Supabase push
    if (Test-Path $outputDir) {
        $projects = Get-ChildItem $outputDir -Directory | Select-Object -ExpandProperty Name
        if ($projects.Count -gt 0) {
            Write-Info "로컬 프로젝트 $($projects.Count)개 감지:"
            $projects | ForEach-Object { Write-Host "    $_" }
            Write-Host ""
            $doSync = Read-Host "? 로컬 프로젝트를 Supabase에 동기화? (y/N)"
            if ($doSync -match '^[yY]') {
                foreach ($p in $projects) {
                    Write-Info "동기화 중: $p"
                    try { auto-kairos sync --project $p }
                    catch { Write-Warn "동기화 실패: $p" }
                }
                Write-Success "동기화 완료"
            }
        }
    }

    # Supabase -> 로컬 pull
    Write-Host ""
    $doPull = Read-Host "? Supabase에서 팀 프로젝트를 다운로드? (y/N)"
    if ($doPull -match '^[yY]') {
        Write-Info "Supabase 프로젝트 다운로드 중..."
        try { auto-kairos project list }
        catch { Write-Warn "프로젝트 목록 조회 실패" }
        # 사용자가 수동으로 pull
        Write-Info "다운로드할 프로젝트: auto-kairos pull --project <slug>"
    }
}

# ═══════════════════════════════════════
# 완료
# ═══════════════════════════════════════

function Write-Completion {
    Write-Host ""
    Write-Host "+=================================================+" -ForegroundColor Green
    Write-Host "|  Auto Kairos v3 설치 완료!                        |" -ForegroundColor Green
    Write-Host "+=================================================+" -ForegroundColor Green
    Write-Host ""
    Write-Host "시작하기:" -ForegroundColor White
    Write-Host "  cd $script:WORKSPACE"
    Write-Host "  claude"
    Write-Host ""
    Write-Host "유용한 명령어:" -ForegroundColor White
    Write-Host "  auto-kairos dashboard          # 웹 대시보드"
    Write-Host "  auto-kairos project list       # 프로젝트 목록"
    Write-Host "  auto-kairos sync --project X   # Supabase 동기화"
    Write-Host "  auto-kairos pull --project X   # Supabase에서 다운로드"
    Write-Host ""
}

# ═══════════════════════════════════════
# 메인
# ═══════════════════════════════════════

Write-Header

Write-Host "-- 시스템 의존성 확인 --" -ForegroundColor White
Write-Host ""
Ensure-Python
Ensure-Node
Ensure-FFmpeg

Write-Host ""
Write-Host "-- 패키지 설치 --" -ForegroundColor White
Write-Host ""
Install-Package

Setup-Workspace
Setup-Env
Sync-Projects
Write-Completion
