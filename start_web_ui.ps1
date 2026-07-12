$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Repository root: $scriptDir"

$venvDir = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvDir -PathType Container)) {
    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venvDir
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $venvDir
    } else {
        Write-Error "Could not find Python. Install Python 3 or make 'py'/'python' available on PATH."
        exit 1
    }

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython -PathType Leaf)) {
    Write-Error "Could not find a Python interpreter in $venvDir"
    exit 1
}

$env:PROJECT_ROOT = $scriptDir
$sourcePath = Join-Path $scriptDir "source"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $sourcePath
} else {
    $env:PYTHONPATH = "$sourcePath;$($env:PYTHONPATH)"
}

$hostValue = if ([string]::IsNullOrWhiteSpace($env:YTRIPPER_WEB_HOST)) { "127.0.0.1" } else { $env:YTRIPPER_WEB_HOST }
$portValue = if ([string]::IsNullOrWhiteSpace($env:YTRIPPER_WEB_PORT)) { "8000" } else { $env:YTRIPPER_WEB_PORT }
$reloadValue = if ([string]::IsNullOrWhiteSpace($env:YTRIPPER_WEB_RELOAD)) { "false" } else { $env:YTRIPPER_WEB_RELOAD }

Write-Host "Using virtual environment interpreter: $venvPython"
Write-Host "Starting web UI on http://$hostValue`:$portValue"

$arguments = @(
    "-m", "uvicorn",
    "web.main:app",
    "--app-dir", (Join-Path $scriptDir "source"),
    "--host", $hostValue,
    "--port", $portValue
)

if ($reloadValue -eq "true" -or $reloadValue -eq "1") {
    $arguments += "--reload"
}

& $venvPython @arguments
exit $LASTEXITCODE
