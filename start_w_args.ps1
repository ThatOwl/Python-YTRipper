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

Write-Host "Using virtual environment interpreter: $venvPython"

$env:PROJECT_ROOT = $scriptDir
$sourcePath = Join-Path $scriptDir "source"
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $sourcePath
} else {
    $env:PYTHONPATH = "$sourcePath;$($env:PYTHONPATH)"
}

Write-Host "Starting application 'Python-YTRipper'..."
& $venvPython (Join-Path $scriptDir "source\yt_ripper.py") @args
exit $LASTEXITCODE
