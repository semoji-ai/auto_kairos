# =============================================================
# Auto Kairos — 설치 스크립트 (Windows PowerShell)
# =============================================================

$ErrorActionPreference = "Stop"

function Write-Step   { param($msg) Write-Host "`n-- $msg --" -ForegroundColor White }
function Write-Info   { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Fail   { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) { $ScriptDir = $PWD.Path }
$SkillsDir = Join-Path $env:USERPROFILE ".claude\skills"
$Errors = 0

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Auto Kairos 설치" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# =============================================================
Write-Step "1. 시스템 의존성 확인"
# =============================================================

# Python
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    $parts = $pyVer.Split('.')
    if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
        Write-Info "Python $pyVer"
    } else {
        Write-Fail "Python 3.10+ 필요 (현재: $pyVer)"
        $Errors++
    }
} catch {
    Write-Fail "Python 미설치 — https://python.org"
    $Errors++
}

# Node.js
$NodeOk = $false
try {
    $nodeVer = node -e "console.log(process.versions.node)" 2>$null
    $nodeMajor = [int]($nodeVer.Split('.')[0])
    if ($nodeMajor -ge 18) {
        Write-Info "Node.js v$nodeVer"
        $NodeOk = $true
    } else {
        Write-Fail "Node.js 18+ 필요 (현재: v$nodeVer)"
        $Errors++
    }
} catch {
    # volta / nvm-windows 확인
    $voltaNode = Join-Path $env:USERPROFILE ".volta\bin\node.exe"
    if (Test-Path $voltaNode) {
        $env:PATH = "$env:USERPROFILE\.volta\bin;$env:PATH"
        Write-Info "Node.js (volta)"
        $NodeOk = $true
    } else {
        Write-Fail "Node.js 미설치 — https://nodejs.org"
        $Errors++
    }
}

# ffmpeg
try {
    ffmpeg -version 2>&1 | Out-Null
    Write-Info "ffmpeg 설치됨"
} catch {
    Write-Warn "ffmpeg 미설치 — 영상 렌더링에 필요 (choco install ffmpeg)"
}

# Claude Code CLI
try {
    claude --version 2>&1 | Out-Null
    Write-Info "Claude Code CLI 설치됨"
} catch {
    Write-Fail "Claude Code CLI 미설치 — npm install -g @anthropic-ai/claude-code"
    $Errors++
}

if ($Errors -gt 0) {
    Write-Host ""
    Write-Fail "$Errors 개 필수 의존성 누락. 위 안내에 따라 설치 후 다시 실행하세요."
    exit 1
}

# =============================================================
Write-Step "2. Python 패키지 설치"
# =============================================================

Push-Location $ScriptDir
try {
    pip install -e ".[all]" 2>&1 | Select-Object -Last 3
    Write-Info "Python 패키지 설치 완료"
} catch {
    Write-Warn "pip install 실패 — 수동 설치 필요: pip install -e `".[all]`""
}

# 추가 의존성
pip install python-multipart mutagen matplotlib 2>$null | Out-Null

# whisperx 확인
try {
    python -c "import whisperx" 2>$null
    Write-Info "WhisperX 설치됨"
} catch {
    Write-Warn "WhisperX 미설치 — 자막에 필요 (선택: pip install whisperx)"
}
Pop-Location

# =============================================================
Write-Step "3. Node.js 패키지 설치 (Remotion)"
# =============================================================

$remotionDir = Join-Path $ScriptDir "remotion"
if ($NodeOk -and (Test-Path $remotionDir)) {
    Push-Location $remotionDir
    npm install 2>&1 | Select-Object -Last 3
    Write-Info "Remotion 패키지 설치 완료"

    # 대시보드 번들 빌드
    if (Test-Path "vite.thumb.config.ts") {
        npx vite build --config vite.thumb.config.ts 2>&1 | Select-Object -Last 2
        npx vite build --config vite.editor.config.ts 2>&1 | Select-Object -Last 2
        Write-Info "대시보드 번들 빌드 완료"
    }
    Pop-Location
} else {
    Write-Warn "Remotion 설치 건너뜀"
}

# =============================================================
Write-Step "4. 환경변수 설정"
# =============================================================

$envFile = Join-Path $ScriptDir ".env"
$envExample = Join-Path $ScriptDir ".env.example"

if (Test-Path $envFile) {
    Write-Info ".env 파일 존재"
} elseif (Test-Path $envExample) {
    Copy-Item $envExample $envFile
    Write-Warn ".env 파일 생성됨 — API 키를 입력하세요: $envFile"
}

# 필수 키 확인
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    foreach ($key in @("ELEVENLABS_API_KEY", "FAL_API_KEY", "SERPER_API_KEY")) {
        if ($envContent -match "$key=.+" -and $envContent -notmatch "$key=YOUR_") {
            Write-Info "$key OK"
        } else {
            Write-Warn "$key 미설정"
        }
    }
}

# =============================================================
Write-Step "5. 데이터베이스 초기화"
# =============================================================

$dbFile = Join-Path $ScriptDir "auto_agent.db"
if (Test-Path $dbFile) {
    Write-Info "데이터베이스 존재"
} else {
    try {
        python -c "from auto_agent.db.project_manager import ProjectManager; pm = ProjectManager(); print('DB initialized')" 2>$null
        Write-Info "데이터베이스 초기화 완료"
    } catch {
        Write-Warn "DB 초기화 실패 — 첫 실행 시 자동 생성됩니다"
    }
}

# =============================================================
Write-Step "6. 디렉토리 구조 생성"
# =============================================================

New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir "output") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir "remotion\public\manifests") 2>$null | Out-Null
Write-Info "디렉토리 준비 완료"

# =============================================================
Write-Step "7. Claude Code 슬래시 스킬 설치"
# =============================================================

New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null

$SkillCount = 0
foreach ($skillName in @("auto-kairos", "kairos-research", "kairos-write", "kairos-product")) {
    $src = Join-Path $ScriptDir "skills\$skillName\SKILL.md"
    $destDir = Join-Path $SkillsDir $skillName

    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item $src (Join-Path $destDir "SKILL.md") -Force
        Write-Info "스킬 설치: /$skillName"
        $SkillCount++
    }
}

if ($SkillCount -gt 0) {
    Write-Info "$SkillCount 개 스킬 설치 완료"
} else {
    Write-Warn "스킬 파일 없음 — skills/ 디렉토리 확인 필요"
}

# =============================================================
Write-Step "8. 환경변수 프로필 설정"
# =============================================================

Write-Host ""
Write-Info "KAIROS_HOME 환경변수를 설정하세요:"
Write-Host "  `$env:KAIROS_HOME = `"$ScriptDir`""
Write-Host ""
Write-Host "  영구 설정:"
Write-Host "  [Environment]::SetEnvironmentVariable('KAIROS_HOME', '$ScriptDir', 'User')"

# =============================================================
Write-Step "9. 설치 검증"
# =============================================================

try {
    python -c "from auto_agent.cli import main; print('CLI OK')" 2>$null
    Write-Info "auto-agent CLI 정상"
} catch {
    Write-Warn "auto-agent CLI 확인 실패"
}

# =============================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Auto Kairos 설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  사용법:"
Write-Host "    auto-agent project create     프로젝트 생성"
Write-Host "    auto-agent run --project X    파이프라인 실행"
Write-Host "    auto-agent dashboard          대시보드 (http://localhost:8080)"
Write-Host ""
Write-Host "  Claude Code 슬래시 스킬:"
Write-Host "    /auto-kairos [주제]           전체 파이프라인"
Write-Host "    /kairos-research [slug]       Stage 1 리서치"
Write-Host "    /kairos-write [slug]          Stage 2 원고+연출"
Write-Host "    /kairos-product [slug]        Stage 3 에셋조립"
Write-Host ""
