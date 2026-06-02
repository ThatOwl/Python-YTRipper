[CmdletBinding()]
param(
    [switch]$NoAliases,
    [switch]$SkipProfile,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$repoName = "Python-YTRipper"
$repoMarker = "source\yt_ripper.py"
$repoCloneUrl = "https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git"

function Show-PowerShellExecutionPolicyNote {
    Write-Host "PowerShell script note:"
    Write-Host "  Recommended non-admin setup: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned"
    Write-Host "  One-shot setup only:        powershell -ExecutionPolicy Bypass -File .\microtools\install.ps1"
    Write-Host "  This installer only writes user/repo files; it does not require an admin PowerShell."
    Write-Host ""
}

function Install-ShellAliasesConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $configDir = Join-Path $RepoRoot "config"
    $configFile = Join-Path $configDir "shell_aliases.conf"
    $legacyConfigFile = Join-Path $RepoRoot "shell_aliases.conf"

    New-Item -ItemType Directory -Path $configDir -Force | Out-Null

    if ((Test-Path $legacyConfigFile -PathType Leaf) -and -not (Test-Path $configFile -PathType Leaf)) {
        Move-Item -Path $legacyConfigFile -Destination $configFile
        Write-Host "Migrated legacy alias config to: $configFile"
    }

    if (Test-Path $configFile -PathType Leaf) {
        $content = Get-Content -Path $configFile -Raw
        if ($content -notmatch '(?m)^(#\s*)?TAGDIR_DEFAULT_DIRECTORY=') {
            Add-Content -Path $configFile -Value @'

# Optional default directory used by `tagDir`, `tagDirFast`, and `tagDirAll`.
# Leave commented out to let those helpers default to your current shell directory.
# TAGDIR_DEFAULT_DIRECTORY="$HOME/RipperTarget"
'@
            Write-Host "Updated alias config with tagger defaults: $configFile"
        } else {
            Write-Host "Alias config already exists: $configFile"
        }
        return
    }

    Set-Content -Path $configFile -Value @'
# Python-YTRipper shell aliases configuration
# This file is read by both microtools/shell_aliases.sh and microtools/shell_aliases.ps1.
# Override these values for your environment.

# Default file used by `ytp` (calls ytf <file>)
YTF_DEFAULT_FILE="$HOME/RipperTarget/paste-here.txt"

# Optional default directory used by `tagDir`, `tagDirFast`, and `tagDirAll`.
# Leave commented out to let those helpers default to your current shell directory.
# TAGDIR_DEFAULT_DIRECTORY="$HOME/RipperTarget"
'@

    Write-Host "Created alias config: $configFile"
}

function Install-PowerShellAliases {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    if ($NoAliases) {
        Write-Host "Skipping PowerShell alias setup because -NoAliases was supplied."
        return
    }

    $aliasesFile = Join-Path $RepoRoot "microtools\shell_aliases.ps1"
    $profilePath = $PROFILE.CurrentUserCurrentHost
    if (-not $profilePath) {
        $profilePath = $PROFILE
    }

    if (-not (Test-Path $aliasesFile -PathType Leaf)) {
        Write-Warning "Alias file not found: $aliasesFile"
        return
    }

    if ($SkipProfile) {
        Write-Host "Skipping PowerShell profile update because -SkipProfile was supplied."
        Write-Host "To load helpers manually in a shell, run:"
        Write-Host "  . `"$aliasesFile`""
        return
    }

    $sourceLine = ". `"$aliasesFile`""

    if (-not $Yes) {
        Write-Host ""
        Write-Host "PowerShell helper functions are loaded by adding this dot-source line to your user profile:"
        Write-Host "  $sourceLine"
        Write-Host "Profile file:"
        Write-Host "  $profilePath"
        Write-Host "This affects only your user profile, not machine-wide PowerShell settings."
        $answer = Read-Host "Add or update this profile entry? [y/N]"
        if ($answer -notmatch '^(?i:y|yes)$') {
            Write-Host "Skipped PowerShell profile update."
            return
        }
    }

    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir -PathType Container)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    if (-not (Test-Path $profilePath -PathType Leaf)) {
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }

    $lines = Get-Content -Path $profilePath
    $filteredLines = foreach ($line in $lines) {
        if ($line -match 'microtools[\\/]+shell_aliases\.ps1') {
            continue
        }
        $line
    }

    if ($filteredLines.Count -ne $lines.Count) {
        Set-Content -Path $profilePath -Value $filteredLines
    }

    $profileContents = Get-Content -Path $profilePath
    if ($profileContents -contains $sourceLine) {
        Write-Host "PowerShell aliases already configured in $profilePath"
        return
    }

    Add-Content -Path $profilePath -Value $sourceLine
    Write-Host "Added PowerShell aliases to $profilePath"
}

function Print-PostInstallHelp {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Repository: $RepoRoot"
    Write-Host "Start the app with:"
    Write-Host "  Set-Location `"$RepoRoot`""
    Write-Host "  .\start_w_args.ps1 --loop"
    Write-Host "  .\start_autotagger_w_args.ps1 --loop"
    Write-Host "  tagDir `"$HOME\Music`""
    Write-Host ""
    Write-Host "README:"
    Write-Host "  $RepoRoot\README.md"
    Write-Host "  $RepoRoot\README_Autotagger.md"
    Write-Host "  $RepoRoot\README_windows.md"
    Write-Host "Please open the README for usage, flags, loop mode, and setup details."
    Write-Host ""
    Write-Host "Or use the virtual environment Python directly:"
    Write-Host "  .\.venv\Scripts\python.exe .\source\yt_ripper.py --help"
}

function Install-OptionalShellHelpers {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    if ($NoAliases) {
        Write-Host "Skipping alias config and profile setup because -NoAliases was supplied."
        return
    }

    Install-ShellAliasesConfig -RepoRoot $RepoRoot
    Install-PowerShellAliases -RepoRoot $RepoRoot
}

function Find-RepoRoot {
    $currentDir = (Get-Location).Path
    if (Test-Path (Join-Path $currentDir $repoMarker) -PathType Leaf) {
        return $currentDir
    }

    foreach ($child in Get-ChildItem -Directory) {
        $candidate = Join-Path $child.FullName $repoMarker
        if (Test-Path $candidate -PathType Leaf) {
            return $child.FullName
        }
    }

    return $null
}

function New-YtRipperVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $venvPath = Join-Path $RepoRoot ".venv"
    if (Test-Path $venvPath -PathType Container) {
        return
    }

    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venvPath
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $venvPath
    } else {
        throw "Could not find Python. Install Python 3 or make 'py'/'python' available on PATH."
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed."
    }
}

function Install-RepoDependencies {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython -PathType Leaf)) {
        throw "Virtual environment Python not found: $venvPython"
    }

    Write-Host "Installing dependencies..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip."
    }

    & $venvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements."
    }
}

Show-PowerShellExecutionPolicyNote

$repoRoot = Find-RepoRoot

if ($repoRoot) {
    Write-Host "Detected existing repository at: $repoRoot"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "1) Update (clone fresh, may overwrite settings)"
    Write-Host "2) Use existing installation"
    Write-Host "3) Cancel"
    $choice = Read-Host "Enter choice [1-3]"

    switch ($choice) {
        "1" {
            Write-Host "Updating repository..."
            $parentDir = Split-Path -Parent $repoRoot
            Set-Location $parentDir
            $currentName = Split-Path -Leaf $repoRoot
            $backupPath = Join-Path $parentDir "${currentName}_backup"

            if (Test-Path $backupPath) {
                Remove-Item -Path $backupPath -Recurse -Force
            }

            Move-Item -Path $repoRoot -Destination $backupPath
            Write-Host "Backed up existing repo to: $backupPath"
        }
        "2" {
            Write-Host "Using existing installation at: $repoRoot"
            New-YtRipperVenv -RepoRoot $repoRoot
            Install-RepoDependencies -RepoRoot $repoRoot
            Install-OptionalShellHelpers -RepoRoot $repoRoot
            Print-PostInstallHelp -RepoRoot $repoRoot
            exit 0
        }
        "3" {
            Write-Host "Cancelled."
            exit 0
        }
        default {
            Write-Error "Invalid choice. Cancelled."
            exit 1
        }
    }
}

Write-Host "Cloning repository..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Could not find 'git' on PATH."
}

& git clone $repoCloneUrl
if ($LASTEXITCODE -ne 0) {
    throw "git clone failed."
}

$clonedRepoRoot = Join-Path (Get-Location).Path $repoName
Set-Location $clonedRepoRoot

Write-Host "Setting up virtual environment..."
New-YtRipperVenv -RepoRoot $clonedRepoRoot
Install-RepoDependencies -RepoRoot $clonedRepoRoot
Install-OptionalShellHelpers -RepoRoot $clonedRepoRoot
Print-PostInstallHelp -RepoRoot $clonedRepoRoot
