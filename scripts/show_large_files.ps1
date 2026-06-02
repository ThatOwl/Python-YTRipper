$minSeconds = 8 * 60
$sortBy = "duration"
$outConsole = $false
$outText = $false
$outCsv = $false
$jobs = 1
$rootDir = "."
$extensions = @(".mp3", ".m4a", ".mp4")

function Show-Usage {
    @"
Usage: show_large_files.ps1 [options] [rootdir]

Path:
  rootdir            Directory tree to scan (default: current directory)

Output:
  -c, --console      Output to console
  -t, --text         Output to text file named: <date>_<rootdir>_Large-Files.txt
  -v, --csv          Output to CSV file named:  <date>_<rootdir>_Large-Files.csv

Filtering & sorting:
  -m <minutes>       Minimum duration (default: 8)
  -s <field>         Sort by: duration | size | name
  -p <jobs>          Accepted for parity; currently scans sequentially

Info:
  --info             Show environment & dependency info
  -h, --help         Show this help

Dependencies:
    - ffprobe        (from ffmpeg)  -> media duration detection

Examples:
  .\show_large_files.ps1 --console --text D:\media
  .\show_large_files.ps1 -c --csv -m 20 -s size D:\media
"@ | Write-Output
}

function Format-Duration {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Seconds
    )

    return [TimeSpan]::FromSeconds($Seconds).ToString("hh\:mm\:ss")
}

function Get-ColorName {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Seconds
    )

    if ($Seconds -lt 1200) {
        return "Green"
    }
    if ($Seconds -lt 3600) {
        return "Yellow"
    }
    return "Red"
}

function Get-ReadableFileSize {
    param(
        [Parameter(Mandatory = $true)]
        [long]$Bytes
    )

    $units = @("B", "KB", "MB", "GB", "TB")
    $size = [double]$Bytes
    $unitIndex = 0

    while ($size -ge 1024 -and $unitIndex -lt ($units.Count - 1)) {
        $size /= 1024
        $unitIndex += 1
    }

    if ($unitIndex -eq 0) {
        return "{0} {1}" -f [int][math]::Round($size), $units[$unitIndex]
    }

    return "{0:N1} {1}" -f $size, $units[$unitIndex]
}

function Get-ScanRows {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ResolvedRootDir,
        [Parameter(Mandatory = $true)]
        [int]$MinimumSeconds,
        [Parameter(Mandatory = $true)]
        [string[]]$AllowedExtensions
    )

    $files = Get-ChildItem -Path $ResolvedRootDir -File -Recurse | Where-Object {
        $AllowedExtensions -contains $_.Extension.ToLowerInvariant()
    }

    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($file in $files) {
        $durationRaw = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $file.FullName 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($durationRaw)) {
            continue
        }

        $durationSeconds = 0
        if (-not [int]::TryParse(($durationRaw.Trim().Split(".")[0]), [ref]$durationSeconds)) {
            continue
        }

        if ($durationSeconds -le $MinimumSeconds) {
            continue
        }

        $rows.Add([PSCustomObject]@{
            DurationSeconds = $durationSeconds
            SizeBytes = [int64]$file.Length
            SizeHuman = Get-ReadableFileSize -Bytes $file.Length
            Directory = $file.DirectoryName
            Name = $file.Name
            FullName = $file.FullName
        })
    }

    return $rows
}

$index = 0
while ($index -lt $args.Count) {
    $arg = $args[$index]
    switch ($arg) {
        "-c" { $outConsole = $true }
        "--console" { $outConsole = $true }
        "-t" { $outText = $true }
        "--text" { $outText = $true }
        "-v" { $outCsv = $true }
        "--csv" { $outCsv = $true }
        "-m" {
            $index += 1
            if ($index -ge $args.Count) {
                throw "Missing value for -m"
            }
            $minSeconds = [int]$args[$index] * 60
        }
        "-s" {
            $index += 1
            if ($index -ge $args.Count) {
                throw "Missing value for -s"
            }
            $sortBy = $args[$index]
        }
        "-p" {
            $index += 1
            if ($index -ge $args.Count) {
                throw "Missing value for -p"
            }
            $jobs = [int]$args[$index]
        }
        "--info" {
            $ffprobePath = Get-Command ffprobe -ErrorAction SilentlyContinue
            Write-Output "Media scan tool info"
            Write-Output "-------------------"
            Write-Output ("ffprobe:      {0}" -f $(if ($ffprobePath) { $ffprobePath.Source } else { "no" }))
            Write-Output ("PowerShell:   {0}" -f $PSVersionTable.PSVersion)
            Write-Output ("Parallelism:  {0} job(s) requested, sequential scan currently used" -f $jobs)
            Write-Output ("Extensions:   {0}" -f ($extensions -join " "))
            Write-Output ("Min duration: {0} minutes" -f ($minSeconds / 60))
            exit 0
        }
        "-h" { Show-Usage; exit 0 }
        "--help" { Show-Usage; exit 0 }
        default {
            if ($arg.StartsWith("-")) {
                throw "Unknown option: $arg"
            }
            if ($rootDir -ne ".") {
                throw "Only one rootdir may be provided"
            }
            $rootDir = $arg
        }
    }
    $index += 1
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "ffprobe not found (install ffmpeg)."
}

if (-not (Test-Path $rootDir -PathType Container)) {
    throw "rootdir does not exist or is not a directory: $rootDir"
}
$resolvedRoot = (Resolve-Path -Path $rootDir).Path

$rootLeaf = Split-Path -Leaf $resolvedRoot
if ([string]::IsNullOrWhiteSpace($rootLeaf)) {
    $rootLeaf = "root"
}

$rootSafe = ($rootLeaf -replace '[^A-Za-z0-9_.-]', '_')
$dateStamp = Get-Date -Format "yyyy_MM_dd"
$outTxt = "${dateStamp}_${rootSafe}_Large-Files.txt"
$outCsvFile = "${dateStamp}_${rootSafe}_Large-Files.csv"

$rows = Get-ScanRows -ResolvedRootDir $resolvedRoot -MinimumSeconds $minSeconds -AllowedExtensions $extensions

switch ($sortBy) {
    "duration" { $rows = $rows | Sort-Object DurationSeconds }
    "size" { $rows = $rows | Sort-Object SizeBytes }
    "name" { $rows = $rows | Sort-Object Name }
    default { throw "Invalid sort field: $sortBy" }
}

if ($outText) {
    $textRows = foreach ($row in $rows) {
        "{0}`t | `t{1}`t | `t{2}`t | `t{3}" -f $row.SizeHuman, (Format-Duration -Seconds $row.DurationSeconds), $row.Directory, $row.Name
    }
    Set-Content -Path $outTxt -Value $textRows
}

if ($outCsv) {
    $csvRows = foreach ($row in $rows) {
        [PSCustomObject]@{
            filesize = $row.SizeHuman
            duration = Format-Duration -Seconds $row.DurationSeconds
            directory = $row.Directory
            filename = $row.Name
        }
    }
    $csvRows | Export-Csv -Path $outCsvFile -NoTypeInformation
}

if ($outConsole) {
    foreach ($row in $rows) {
        Write-Host ("{0}`t | `t{1}`t | `t{2}`t | `t{3}" -f $row.SizeHuman, (Format-Duration -Seconds $row.DurationSeconds), $row.Directory, $row.Name) -ForegroundColor (Get-ColorName -Seconds $row.DurationSeconds)
    }
}
