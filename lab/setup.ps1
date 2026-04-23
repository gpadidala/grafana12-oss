# Windows / PowerShell bootstrap for the grafana12-oss lab.
# Equivalent to `make up` on Mac / Linux.
#
# Usage:
#   cd lab
#   .\setup.ps1            # bring the stack up (idempotent)
#   .\setup.ps1 down       # stop (preserve volumes)
#   .\setup.ps1 reset      # nuke including volumes
#   .\setup.ps1 status     # container status + URLs
#   .\setup.ps1 logs       # tail grafana logs

param(
    [Parameter(Position=0)][string]$Action = "up"
)

$ErrorActionPreference = "Stop"

# --- 1. Sanity checks -------------------------------------------------------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: docker not found. Install Docker Desktop and retry." -ForegroundColor Red
    exit 1
}

# Must be run from lab/ (where .env + .env.example live)
if (-not (Test-Path ".env.example")) {
    Write-Host "ERROR: run this from the lab\ directory (where .env.example lives)." -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)"
    exit 1
}

# --- 2. Auto-create .env from .env.example if missing -----------------------
if (-not (Test-Path ".env")) {
    Write-Host ">> .env not found — seeding from .env.example" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"

    # Replace the CHANGE_ME placeholders with lab-only defaults so anonymous
    # Admin works out of the box. These are LAB values — never use in prod.
    (Get-Content .env) `
        -replace 'GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME.*',     'GF_SECURITY_ADMIN_PASSWORD=admin' `
        -replace 'GF_SECURITY_SECRET_KEY=CHANGE_ME.*',         'GF_SECURITY_SECRET_KEY=lab-only-32bytes-0123456789abcdef0123456789' `
        -replace 'GF_DATABASE_PASSWORD=CHANGE_ME.*',           'GF_DATABASE_PASSWORD=grafana-lab-db' `
        -replace 'POSTGRES_ROOT_PASSWORD=CHANGE_ME.*',         'POSTGRES_ROOT_PASSWORD=grafana-lab-root' `
        -replace 'RENDERER_AUTH_TOKEN=CHANGE_ME.*',            'RENDERER_AUTH_TOKEN=lab-only-renderer-token-32bytes' `
      | Set-Content .env

    Write-Host ">> .env created with lab defaults" -ForegroundColor Green
}

# --- 3. Resolve compose command (v2 plugin 'docker compose' OR legacy v1) ---
$composeArgs = @()
try {
    docker compose version | Out-Null 2>$null
    $composeCmd = "docker"
    $composeArgs += "compose"
} catch {
    $composeCmd = "docker-compose"
}

# Always pass --env-file + -f so we don't depend on CWD
$composeArgs += @(
    "--env-file", ".env",
    "-f", "compose\docker-compose.yml",
    "-p", "grafana12-oss-lab"
)

# --- 4. Dispatch ------------------------------------------------------------
switch ($Action) {
    "up" {
        Write-Host ">> Building images + starting stack (first run pulls ~1.5GB)..." -ForegroundColor Cyan
        & $composeCmd @composeArgs up -d --build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        Write-Host "`n>> Waiting for Grafana /api/health (up to 2 min)..." -ForegroundColor Cyan
        $deadline = (Get-Date).AddMinutes(2)
        $ready = $false
        while ((Get-Date) -lt $deadline) {
            try {
                $body = Invoke-RestMethod -Uri "http://localhost:3012/api/health" -TimeoutSec 3
                if ($body.database -eq "ok") { $ready = $true; break }
            } catch { }
            Start-Sleep -Seconds 2
        }
        if (-not $ready) {
            Write-Host "!! Grafana did not become ready in 2 min. Run: .\setup.ps1 logs" -ForegroundColor Red
            exit 1
        }

        & $composeCmd @composeArgs ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
        Write-Host ""
        Write-Host "  Grafana UI    --> http://localhost:3012   (anonymous Admin, or admin/admin)" -ForegroundColor Green
        Write-Host "  Prometheus UI --> http://localhost:9092"
        Write-Host "  Loki API      --> http://localhost:3112"
        Write-Host "  Tempo API     --> http://localhost:3212"
        Write-Host "  Pyroscope UI  --> http://localhost:4042"
        Write-Host "  Alloy UI      --> http://localhost:12346"
    }

    "down"  { & $composeCmd @composeArgs down }
    "reset" { & $composeCmd @composeArgs down -v --remove-orphans }
    "status" { & $composeCmd @composeArgs ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}' }
    "logs"  { & $composeCmd @composeArgs logs -f grafana }
    "build" { & $composeCmd @composeArgs build --pull }
    default {
        Write-Host "Unknown action: $Action"
        Write-Host "Valid: up | down | reset | status | logs | build"
        exit 1
    }
}
