# Publish a genuine local screenshot to the project READMEs in one commit.
# Run through PUBLISH_SCREENSHOT.bat from a clean, up-to-date main branch.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
Set-Location $repoRoot

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("git {0} failed with exit code {1}" -f ($Arguments -join " "), $LASTEXITCODE)
    }
}

if ((& git rev-parse --is-inside-work-tree).Trim() -ne "true") {
    throw "Run this script inside the vGUITAR Git checkout."
}
$branch = (& git branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Expected branch main; actual branch: $branch"
}
$dirty = @(& git status --porcelain --untracked-files=no)
if ($dirty.Count -ne 0) {
    throw "Commit or stash existing tracked changes before publishing the screenshot."
}
Invoke-Git fetch origin main
$localSha = (& git rev-parse HEAD).Trim()
$remoteSha = (& git rev-parse origin/main).Trim()
if ($localSha -ne $remoteSha) {
    throw "Local branch is not identical to origin/main; run: git pull --ff-only origin main"
}

$imageRel = "vguitar/assets/screenshot-main.png"
$imagePath = Join-Path $repoRoot ($imageRel.Replace("/", "\"))
if (-not (Test-Path -LiteralPath $imagePath -PathType Leaf)) {
    throw ("Screenshot not found: {0}. Run capture_screenshot.py first." -f $imagePath)
}
$bytes = [System.IO.File]::ReadAllBytes($imagePath)
$signature = @(137, 80, 78, 71, 13, 10, 26, 10)
if ($bytes.Length -lt 1024) { throw "Screenshot PNG is too small." }
for ($i = 0; $i -lt 8; $i++) {
    if ($bytes[$i] -ne $signature[$i]) { throw "Screenshot file is not a PNG." }
}
function Read-UInt32BE([byte[]]$Data, [int]$Offset) {
    return (($Data[$Offset] -shl 24) -bor
            ($Data[$Offset + 1] -shl 16) -bor
            ($Data[$Offset + 2] -shl 8) -bor
            $Data[$Offset + 3])
}
$width = Read-UInt32BE $bytes 16
$height = Read-UInt32BE $bytes 20
if ($width -lt 600 -or $height -lt 400) {
    throw ("Screenshot resolution too small: {0}x{1}" -f $width, $height)
}
Write-Host ("Screenshot: {0}x{1} ({2} bytes)" -f $width, $height, $bytes.Length)

$marker = "vguitar/assets/screenshot-main.png"
$entries = @(
    @{ File = "README.md"; Header = "## Установка";
       Section = "## Интерфейс"; Alt = "Главное окно vGUITAR Note Trainer" },
    @{ File = "README.en.md"; Header = "## Installation";
       Section = "## Application preview"; Alt = "vGUITAR Note Trainer main window" }
)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($entry in $entries) {
    $path = Join-Path $repoRoot $entry.File
    $original = [System.IO.File]::ReadAllText($path)
    if ($original.Contains($marker)) { continue }
    $header = $entry.Header
    $at = $original.IndexOf($header, [System.StringComparison]::Ordinal)
    if ($at -lt 0) { throw ("Missing README heading {0} in {1}" -f $header, $entry.File) }
    $newline = if ($original.Contains("`r`n")) { "`r`n" } else { "`n" }
    $addition = $entry.Section + $newline + $newline +
        ("![{0}]({1})" -f $entry.Alt, $marker) +
        $newline + $newline
    $updated = $original.Insert($at, $addition)
    [System.IO.File]::WriteAllText($path, $updated, $utf8NoBom)
}

Invoke-Git add -- README.md README.en.md
Invoke-Git add --force -- $imageRel
$allowed = @("README.md", "README.en.md", $imageRel)
$staged = @(& git diff --cached --name-only)
foreach ($path in $staged) {
    if ($path -notin $allowed) {
        throw ("Unexpected staged file: {0}; aborting commit." -f $path)
    }
}
if ($imageRel -notin $staged) {
    throw "Screenshot has not been staged; aborting."
}
Invoke-Git commit -m "docs: publish actual application screenshot in both READMEs"
Invoke-Git push origin main
Write-Host "Screenshot and both README updates published to origin/main."
