$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (!(Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    $selectedVersion = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($candidateVersion in @("3.13", "3.12")) {
            try {
                & py "-$candidateVersion" -c "import sys; sys.exit(0)" 2>$null
                if ($LASTEXITCODE -eq 0) { $selectedVersion = $candidateVersion; break }
            } catch { }
        }
    }
    if ($selectedVersion) {
        Write-Host "Creating environment with Python $selectedVersion"
        & py "-$selectedVersion" -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
    } else {
        $pathPythonSupported = $false
        if (Get-Command python -ErrorAction SilentlyContinue) {
            try {
                & python -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,12),(3,13)] else 1)" 2>$null
                $pathPythonSupported = ($LASTEXITCODE -eq 0)
            } catch { }
        }
        if (!$pathPythonSupported) { throw "Python 3.12 or 3.13 was not found. Check py -0p or your PATH." }
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
    }
}
if (!(Test-Path -LiteralPath ".venv\dependencies-ready")) {
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Check the network and run again." }
    New-Item ".venv\dependencies-ready" -ItemType File -Force | Out-Null
}
if (!(Test-Path -LiteralPath "frontend\dist\index.html")) { throw "Missing frontend build. Run npm ci and npm run build in the frontend folder." }
Write-Host "Keep this window open. Visit http://127.0.0.1:8765"
& .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
