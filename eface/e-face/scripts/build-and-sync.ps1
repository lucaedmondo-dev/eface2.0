param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Join-Path $root '..'
$frontend = Join-Path $projectRoot 'frontend'
$backendDist = Join-Path $projectRoot 'backend\frontend_dist'
$backgroundSrc = Join-Path $frontend 'src\assets\room-backgrounds'
$backgroundDst = Join-Path $backendDist 'src\assets\room-backgrounds'

Write-Host "[1/5] Installing dependencies..." -ForegroundColor Cyan
if (-not $SkipInstall) {
    Push-Location $frontend
    try {
        npm install
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  skipped (per flag)" -ForegroundColor Yellow
}

Write-Host "[2/5] Building frontend bundle..." -ForegroundColor Cyan
Push-Location $frontend
try {
    npm run build
} finally {
    Pop-Location
}

Write-Host "[3/5] Cleaning backend frontend_dist..." -ForegroundColor Cyan
if (Test-Path $backendDist) {
    Get-ChildItem $backendDist -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $backendDist | Out-Null
}

Write-Host "[4/5] Copying dist -> backend/frontend_dist" -ForegroundColor Cyan
Copy-Item (Join-Path $frontend 'dist\*') $backendDist -Recurse

Write-Host "[5/5] Syncing custom backgrounds" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $backgroundDst -Force | Out-Null
if (Test-Path $backgroundSrc) {
    Copy-Item (Join-Path $backgroundSrc '*') $backgroundDst -Recurse -Force
}

Write-Host 'Done.' -ForegroundColor Green
