# Run from the project folder: .\scripts\setup-local.ps1 [--check-only]
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BootstrapPython = $null
foreach ($Candidate in @('python3.13', 'python3.12', 'python', 'python3')) {
    if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
        try {
            $VersionCheck = & $Candidate -c "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $VersionCheck) { $BootstrapPython = $VersionCheck.Trim(); break }
        } catch { }
    }
}
if (-not $BootstrapPython -and (Get-Command py -ErrorAction SilentlyContinue)) {
    try {
        $VersionCheck = & py -3 -c "import sys; print(sys.executable if sys.version_info >= (3, 9) else '')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $VersionCheck) { $BootstrapPython = $VersionCheck.Trim() }
    } catch { }
}
if (-not $BootstrapPython) {
    if ($args -contains '--check-only') {
        Write-Host 'FAIL: Python is missing. Run setup without --check-only.'
        exit 1
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host 'Install 64-bit Python 3.12 or 3.13 from python.org, then rerun this script.'
        exit 1
    }
    & winget install --id Python.Python.3.13 --exact --source winget
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    foreach ($Candidate in @("$env:LOCALAPPDATA\Programs\Python\Python313\python.exe", "$env:ProgramFiles\Python313\python.exe")) {
        if (Test-Path $Candidate) { $BootstrapPython = $Candidate; break }
    }
    if (-not $BootstrapPython) {
        Write-Host 'Python installed. Reopen PowerShell and rerun this script so its PATH is refreshed.'
        exit 1
    }
}
& $BootstrapPython "$ProjectRoot\scripts\setup_local.py" @args
exit $LASTEXITCODE
