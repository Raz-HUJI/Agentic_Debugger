param(
    [switch]$ReloadProfile
)

$ErrorActionPreference = "Stop"

function Write-Ok([string]$Message) {
    Write-Host "[agent_fix installer] $Message" -ForegroundColor Green
}

function Write-Info([string]$Message) {
    Write-Host "[agent_fix installer] $Message" -ForegroundColor Cyan
}

$repoPath = $PSScriptRoot
$agentFixPy = Join-Path $repoPath "agent_fix.py"

if (-not (Test-Path $agentFixPy)) {
    throw "Could not find agent_fix.py at '$agentFixPy'. Run this script from the project root."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH. Install Python and ensure 'python' works in PowerShell."
}

if (-not (Test-Path $PROFILE)) {
    $profileDir = Split-Path $PROFILE -Parent
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Info "Created PowerShell profile at '$PROFILE'."
}

$startMarker = "# >>> agent_fix command >>>"
$endMarker = "# <<< agent_fix command <<<"

$block = @"
$startMarker
function agent_fix {
    & python "$agentFixPy" @args
}
$endMarker
"@

$profileContent = [System.IO.File]::ReadAllText($PROFILE)
$escapedStart = [regex]::Escape($startMarker)
$escapedEnd = [regex]::Escape($endMarker)
$pattern = "(?ms)$escapedStart.*?$escapedEnd\r?\n?"

if ([regex]::IsMatch($profileContent, $pattern)) {
    $updated = [regex]::Replace($profileContent, $pattern, ($block + [Environment]::NewLine))
    [System.IO.File]::WriteAllText($PROFILE, $updated)
    Write-Info "Updated existing agent_fix command in profile."
} else {
    if ($profileContent.Length -gt 0 -and -not $profileContent.EndsWith([Environment]::NewLine)) {
        [System.IO.File]::AppendAllText($PROFILE, [Environment]::NewLine)
    }
    [System.IO.File]::AppendAllText($PROFILE, $block + [Environment]::NewLine)
    Write-Info "Added agent_fix command to profile."
}

if ($ReloadProfile) {
    . $PROFILE
    Write-Ok "Profile reloaded. You can use 'agent_fix' now."
} else {
    Write-Ok "Installation complete."
    Write-Host "Run this command to load it now:  . `$PROFILE"
}

