# Foothold Extended Installer
# Usage: powershell -c "irm https://bojotex.github.io/Foothold-Extended/install.ps1 | iex"

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# -- Branding -----------------------------------------------------------------
function Write-Banner {
    Write-Host ""
    Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |           FOOTHOLD EXTENDED INSTALLER              |" -ForegroundColor Cyan
    Write-Host "  |     DCS Multiplayer PvE Campaign by Lekaa          |" -ForegroundColor Cyan
    Write-Host "  +----------------------------------------------------+" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($msg)  { Write-Host "  [*] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "  [+] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "  [X] $msg" -ForegroundColor Red }

# -- Python check -------------------------------------------------------------
function Test-Python {
    try {
        $ver = & python --version 2>&1
        if ($ver -match 'Python (\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) { return $true }
        }
    } catch { }
    return $false
}

function Install-Python {
    Write-Warn "Python >= 3.10 not found. Installing via winget..."
    try {
        & winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                     [System.Environment]::GetEnvironmentVariable("Path", "User")
        if (Test-Python) {
            Write-Ok "Python 3.12 installed successfully."
            return $true
        }
    } catch { }
    Write-Fail "Could not install Python automatically."
    Write-Host "  Please install Python 3.12+ from https://python.org/downloads" -ForegroundColor Gray
    Write-Host "  Make sure to check 'Add Python to PATH' during install." -ForegroundColor Gray
    return $false
}

# -- Download setup.py from latest release ------------------------------------
function Get-SetupScript {
    $api = "https://api.github.com/repos/BojoteX/Foothold-Extended/releases/latest"
    $headers = @{ 'User-Agent' = 'Foothold-Installer' }

    Write-Step "Fetching latest release info..."
    try {
        $release = Invoke-RestMethod -Uri $api -Headers $headers -TimeoutSec 15
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 404) {
            Write-Fail "No releases found. The project may not have a release yet."
        } elseif ($code -eq 403) {
            Write-Fail "GitHub API rate limit. Wait a few minutes and try again."
        } else {
            Write-Fail "Could not reach GitHub: $_"
        }
        return $null
    }

    Write-Ok "Latest release: $($release.tag_name)"

    # Find setup.py in assets
    $asset = $release.assets | Where-Object { $_.name -eq 'setup.py' } | Select-Object -First 1
    if (-not $asset) {
        Write-Fail "setup.py not found in release assets."
        return $null
    }

    $tmp = Join-Path $env:TEMP "foothold_setup.py"
    Write-Step "Downloading installer..."

    $progressPref = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmp -UseBasicParsing -TimeoutSec 60
    } finally {
        $ProgressPreference = $progressPref
    }

    if (!(Test-Path $tmp)) {
        Write-Fail "Download failed."
        return $null
    }

    Write-Ok "Installer downloaded."
    return $tmp
}

# == MAIN =====================================================================

Write-Banner

# 1. Python
if (Test-Python) {
    Write-Ok "Python found."
} else {
    if (!(Install-Python)) {
        Write-Host ""
        Write-Host "  Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
}

# 2. Download setup.py
$setup = Get-SetupScript
if (-not $setup) {
    Write-Host ""
    Write-Host "  Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# 3. Launch
Write-Step "Launching Foothold Extended Setup..."
Write-Host ""
try {
    & python $setup
    $exitCode = $LASTEXITCODE
} finally {
    Remove-Item $setup -Force -ErrorAction SilentlyContinue
}

exit $exitCode
