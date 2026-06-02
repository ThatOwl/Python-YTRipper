$aliasScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$global:YTRIPPER_REPO_ROOT = Split-Path -Parent $aliasScriptDir

function ConvertFrom-YtRipperAliasConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $config = @{}
    foreach ($rawLine in Get-Content -Path $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $match = [regex]::Match($line, '^(?<key>[A-Za-z_][A-Za-z0-9_]*)=(?<value>.*)$')
        if (-not $match.Success) {
            continue
        }

        $value = $match.Groups["value"].Value.Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $config[$match.Groups["key"].Value] = $value
    }

    return $config
}

function Resolve-YtRipperAliasPath {
    param(
        [AllowNull()]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    $resolved = $Value
    if ($resolved.StartsWith('${HOME}')) {
        $resolved = Join-Path $HOME $resolved.Substring(7).TrimStart('/', '\')
    } elseif ($resolved.StartsWith('$HOME')) {
        $resolved = Join-Path $HOME $resolved.Substring(5).TrimStart('/', '\')
    } elseif ($resolved.StartsWith('~/') -or $resolved.StartsWith('~\')) {
        $resolved = Join-Path $HOME $resolved.Substring(2)
    }

    $resolved = [Environment]::ExpandEnvironmentVariables($resolved)
    return $resolved -replace '/', '\'
}

$aliasConfig = Join-Path $global:YTRIPPER_REPO_ROOT "config\shell_aliases.conf"
$legacyAliasConfig = Join-Path $global:YTRIPPER_REPO_ROOT "shell_aliases.conf"

$aliasConfigValues = @{}
if (Test-Path $aliasConfig -PathType Leaf) {
    $aliasConfigValues = ConvertFrom-YtRipperAliasConfig -Path $aliasConfig
} elseif (Test-Path $legacyAliasConfig -PathType Leaf) {
    $aliasConfigValues = ConvertFrom-YtRipperAliasConfig -Path $legacyAliasConfig
}

$global:TAGDIR_DEFAULT_DIRECTORY = $null
$global:YTF_DEFAULT_FILE = Join-Path $HOME "RipperTarget\paste-here.txt"

if ($aliasConfigValues.ContainsKey("TAGDIR_DEFAULT_DIRECTORY")) {
    $global:TAGDIR_DEFAULT_DIRECTORY = Resolve-YtRipperAliasPath $aliasConfigValues["TAGDIR_DEFAULT_DIRECTORY"]
}
if ($aliasConfigValues.ContainsKey("YTF_DEFAULT_FILE")) {
    $global:YTF_DEFAULT_FILE = Resolve-YtRipperAliasPath $aliasConfigValues["YTF_DEFAULT_FILE"]
}

$global:START_W_ARGS_SCRIPT = Join-Path $global:YTRIPPER_REPO_ROOT "start_w_args.ps1"
$global:START_AUTOTAGGER_SCRIPT = Join-Path $global:YTRIPPER_REPO_ROOT "start_autotagger_w_args.ps1"
$global:SHOW_LARGE_FILES_PS1 = Join-Path $global:YTRIPPER_REPO_ROOT "scripts\show_large_files.ps1"

function global:Invoke-YtRipperFromRepoRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [string[]]$ScriptArguments = @()
    )

    Push-Location $global:YTRIPPER_REPO_ROOT
    try {
        & $ScriptPath @ScriptArguments
        return $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function global:Resolve-YtRipperTagDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HelperName,
        [string[]]$DirectoryArgs = @()
    )

    if ($DirectoryArgs.Count -gt 1) {
        throw "Usage: $HelperName [directory]"
    }

    if ($DirectoryArgs.Count -eq 1) {
        return $DirectoryArgs[0]
    }

    if (-not [string]::IsNullOrWhiteSpace($global:TAGDIR_DEFAULT_DIRECTORY)) {
        return $global:TAGDIR_DEFAULT_DIRECTORY
    }

    return (Get-Location).Path
}

function global:tagLoop {
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @("--loop") | Out-Null
}

function global:tagStatus {
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @("status") | Out-Null
}

function global:tagRun {
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @("run") | Out-Null
}

function global:tagDir {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$DirectoryArgs
    )

    $directory = Resolve-YtRipperTagDirectory -HelperName "tagDir" -DirectoryArgs $DirectoryArgs
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @(
        "scan-dir",
        "--directory", $directory,
        "--scan-scope", "missing-any"
    ) | Out-Null
}

function global:tagDirFast {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$DirectoryArgs
    )

    $directory = Resolve-YtRipperTagDirectory -HelperName "tagDirFast" -DirectoryArgs $DirectoryArgs
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @(
        "scan-dir",
        "--directory", $directory,
        "--scan-scope", "missing-any",
        "--no-enrich"
    ) | Out-Null
}

function global:tagDirAll {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$DirectoryArgs
    )

    $directory = Resolve-YtRipperTagDirectory -HelperName "tagDirAll" -DirectoryArgs $DirectoryArgs
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @(
        "scan-dir",
        "--directory", $directory,
        "--scan-scope", "all"
    ) | Out-Null
}

function global:tagApply {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$CsvArgs
    )

    if ($CsvArgs.Count -ne 1) {
        throw "Usage: tagApply <tag_suggestions.csv>"
    }

    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_AUTOTAGGER_SCRIPT -ScriptArguments @(
        "apply-csv",
        "--csv", $CsvArgs[0],
        "--overwrite-mode", "missing"
    ) | Out-Null
}

function global:ytf {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$FileArgs
    )

    if ($FileArgs.Count -lt 1) {
        throw "Usage: ytf <file>"
    }

    $scriptArguments = @("-f", $FileArgs[0])
    if ($FileArgs.Count -gt 1) {
        $scriptArguments += $FileArgs[1..($FileArgs.Count - 1)]
    }

    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_W_ARGS_SCRIPT -ScriptArguments $scriptArguments | Out-Null
}

function global:ytp {
    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_W_ARGS_SCRIPT -ScriptArguments @("-f", $global:YTF_DEFAULT_FILE) | Out-Null
}

function global:ytl {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ExtraArgs
    )

    $scriptArguments = @("--loop")
    if ($ExtraArgs.Count -gt 0) {
        $scriptArguments += $ExtraArgs
    }

    Invoke-YtRipperFromRepoRoot -ScriptPath $global:START_W_ARGS_SCRIPT -ScriptArguments $scriptArguments | Out-Null
}

function global:ytl-h {
    ytl --help
}

function global:slf {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ExtraArgs
    )

    if (Test-Path $global:SHOW_LARGE_FILES_PS1 -PathType Leaf) {
        Push-Location $global:YTRIPPER_REPO_ROOT
        try {
            & $global:SHOW_LARGE_FILES_PS1 @ExtraArgs
        } finally {
            Pop-Location
        }
        return
    }

    throw "The 'slf' helper could not find scripts/show_large_files.ps1."
}

function global:slf-h {
    slf --help
}
