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
    if ($Offset -lt 0 -or ($Offset + 4) -gt $Data.Length) {
        throw "PNG dimension field is incomplete."
    }
    # Shift operators can silently truncate values when applied to byte data.
    # Multiply as UInt64 before combining so 0x0000042E correctly yields 1070.
    return [uint32](([uint64]$Data[$Offset] * 16777216) +
                    ([uint64]$Data[$Offset + 1] * 65536) +
                    ([uint64]$Data[$Offset + 2] * 256) +
                    [uint64]$Data[$Offset + 3])
}
$width = Read-UInt32BE $bytes 16
$height = Read-UInt32BE $bytes 20
if ($width -lt 600 -or $height -lt 400) {
    throw ("Screenshot resolution too small: {0}x{1}" -f $width, $height)
}
Write-Host ("Screenshot: {0}x{1} ({2} bytes)" -f $width, $height, $bytes.Length)

$marker = "vguitar/assets/screenshot-main.png"
# Keep this script ASCII-only for Windows PowerShell 5.1 compatibility.
# Insert the screenshot before the first Markdown section in each README.
$readmeFiles = @("README.md", "README.en.md")
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
foreach ($name in $readmeFiles) {
    $path = Join-Path $repoRoot $name
    $original = [System.IO.File]::ReadAllText($path)
    if ($original.Contains($marker)) { continue }
    $firstSection = [System.Text.RegularExpressions.Regex]::Match(
        $original, '(?m)^## '
    )
    if (-not $firstSection.Success) {
        throw ("No Markdown section found in {0}" -f $name)
    }
    $newline = if ($original.Contains("`r`n")) { "`r`n" } else { "`n" }
    $addition = "![vGUITAR Note Trainer main window]($marker)" + $newline + $newline
    $updated = $original.Insert($firstSection.Index, $addition)
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
