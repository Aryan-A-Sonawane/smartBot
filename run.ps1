# =============================================================================
#  SmartBot - Local Dev Runner
#  Usage: .\run.ps1 [options]
#
#  Options:
#    -BackendOnly    Start only the FastAPI backend
#    -FrontendOnly   Start only the Next.js frontend
#    -SkipInstall    Skip pip/npm install steps (faster restart)
#    -Tests          Run pytest instead of starting the server
# =============================================================================

param (
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$SkipInstall,
    [switch]$Tests
)

Set-StrictMode -Version Latest
# Note: NOT "Stop". Native tools here (pip, uvicorn, pytest) write normal logs
# and warnings to stderr; under "Stop" the first such line aborts the script.
# We check $LASTEXITCODE explicitly after the commands that matter instead.
$ErrorActionPreference = "Continue"

# ---- Paths ------------------------------------------------------------------
$Root    = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Venv    = Join-Path $Backend ".venv"
$Python  = Join-Path $Venv "Scripts\python.exe"

# ---- Colours ----------------------------------------------------------------
function Write-Header  { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }
function Write-OK      { param($msg) Write-Host "  $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  $msg" -ForegroundColor Red }

# ---- Prerequisites ----------------------------------------------------------
function Assert-Command {
    param($Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Err "Required command not found: $Name"
        Write-Err "Please install it and re-run this script."
        exit 1
    }
}

Write-Header "SmartBot - checking prerequisites"
Assert-Command "python"
Assert-Command "node"
Assert-Command "npm"

# ---- Virtual environment ----------------------------------------------------
# Two independent checks:
#   1. Structure - does the venv have a working python.exe? If not (missing or a
#      foreign/corrupt venv), recreate it.
#   2. Dependencies - are the backend packages importable? A venv can be
#      structurally fine yet have no site-packages (e.g. checked out without
#      them); in that case we must install even when -SkipInstall was passed.
Write-Header "Backend - virtual environment"
$VenvCreated = $false
$StructureOk = $false
if (Test-Path $Python) {
    try {
        & $Python -m pip --version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $StructureOk = $true }
    } catch {
        $StructureOk = $false
    }
}
if (-not $StructureOk) {
    if (Test-Path $Venv) {
        Write-Warn "Existing .venv has no working Python - recreating ..."
        Remove-Item -Recurse -Force $Venv
    }
    Write-Warn "Creating .venv ..."
    python -m venv $Venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Python)) {
        Write-Err "Failed to create the virtual environment."
        exit 1
    }
    $VenvCreated = $true
    Write-OK "Created $Venv"
} else {
    Write-OK ".venv Python is usable"
}

$DepsOk = $false
try {
    & $Python -c "import fastapi, uvicorn, fitz" 2>$null
    if ($LASTEXITCODE -eq 0) { $DepsOk = $true }
} catch {
    $DepsOk = $false
}

if ($VenvCreated -or (-not $DepsOk) -or (-not $SkipInstall)) {
    if (-not $DepsOk -and $SkipInstall) {
        Write-Warn "Backend dependencies are missing - installing despite -SkipInstall"
    }
    Write-Header "Backend - installing dependencies"
    & $Python -m pip install -q --upgrade pip
    & $Python -m pip install -q -r (Join-Path $Backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Dependency installation failed (see pip output above)."
        exit 1
    }
    Write-OK "pip install complete"
} else {
    Write-Warn "Skipping pip install (-SkipInstall, dependencies already present)"
}

# ---- Run tests mode ---------------------------------------------------------
if ($Tests) {
    Write-Header "Running pytest (offline - no API key required)"
    Set-Location $Backend
    & $Python -m pytest tests/ -v --tb=short
    exit $LASTEXITCODE
}

# ---- Frontend install -------------------------------------------------------
if (-not $BackendOnly) {
    Write-Header "Frontend - installing dependencies"
    if (-not $SkipInstall) {
        Set-Location $Frontend
        npm install --silent
        Write-OK "npm install complete"
    } else {
        Write-Warn "Skipping npm install (-SkipInstall)"
    }
}

# ---- Show config summary ----------------------------------------------------
Write-Header "Configuration"
$EnvFile = Join-Path $Backend ".env"
if (Test-Path $EnvFile) {
    # Read the env file and display non-secret values
    $envLines = Get-Content $EnvFile | Where-Object { $_ -match "^[A-Z]" -and $_ -notmatch "API_KEY" }
    foreach ($line in $envLines) { Write-OK $line }
    Write-Warn "GEMINI_API_KEY = [hidden]"
} else {
    Write-Warn ".env not found - copy backend/.env.example to backend/.env and fill in GEMINI_API_KEY"
}

# ---- Start processes --------------------------------------------------------
$jobs = @()

if (-not $FrontendOnly) {
    Write-Header "Starting backend on http://localhost:8000"
    $backendJob = Start-Job -Name "backend" -ScriptBlock {
        param($python, $backendDir)
        Set-Location $backendDir
        & $python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 2>&1
    } -ArgumentList $Python, $Backend
    $jobs += $backendJob
    Write-OK "Backend job started (id=$($backendJob.Id))"
}

# Wait a moment for the backend to start before spinning up the frontend
if (-not $FrontendOnly -and -not $BackendOnly) {
    Start-Sleep -Seconds 3
}

if (-not $BackendOnly) {
    Write-Header "Starting frontend on http://localhost:3000"
    $frontendJob = Start-Job -Name "frontend" -ScriptBlock {
        param($frontendDir)
        Set-Location $frontendDir
        npm run dev 2>&1
    } -ArgumentList $Frontend
    $jobs += $frontendJob
    Write-OK "Frontend job started (id=$($frontendJob.Id))"
}

# ---- Wait + stream output ---------------------------------------------------
Write-Header "Both services running - press Ctrl+C to stop"
Write-Host ""
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "  Docs     : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend : http://localhost:3000" -ForegroundColor White
Write-Host ""

try {
    while ($true) {
        foreach ($job in $jobs) {
            $out = Receive-Job -Job $job -ErrorAction SilentlyContinue
            if ($out) {
                $tag = if ($job.Name -eq "backend") { "[backend]" } else { "[frontend]" }
                $color = if ($job.Name -eq "backend") { "DarkCyan" } else { "DarkGreen" }
                foreach ($line in ($out -split "`n")) {
                    if ($line.Trim()) {
                        Write-Host "$tag $line" -ForegroundColor $color
                    }
                }
            }
            # Restart a job that crashed unexpectedly
            if ($job.State -eq "Failed") {
                Write-Err "[$($job.Name)] crashed - check output above"
            }
        }
        Start-Sleep -Milliseconds 300
    }
} finally {
    Write-Header "Shutting down ..."
    foreach ($job in $jobs) {
        Stop-Job  -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        Write-OK "Stopped $($job.Name)"
    }
    Write-Host ""
    Write-Host "Goodbye." -ForegroundColor Cyan
}
