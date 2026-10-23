# vGUITAR historical tags and current GitHub Release.
# Requires Windows PowerShell 5.1+, Git, and (for -PublishRelease) GitHub CLI.
# Existing tag names are never moved or force-updated.
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$PushAll,
    [switch]$PublishRelease
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repoName = "TheColdVoid1337/vGUITAR"
$releaseSubject = "docs(sync): vGUITAR v0.5.4 bilingual docs, icon and release preparation"
$releaseTag = "v0.5.4"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Require-Success([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed (exit code $LASTEXITCODE)." }
}

Push-Location $projectRoot
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is required. Install Git for Windows first."
    }

    $branch = (& git branch --show-current).Trim()
    Require-Success "git branch"
    if ($branch -ne "main") {
        throw "Checkout the project's main branch before running this script (current: $branch)."
    }

    $dirty = @(& git status --porcelain)
    Require-Success "git status"
    if ($dirty.Count -gt 0) {
        throw "Working tree has uncommitted changes; commit or stash them before tagging."
    }

    Write-Host "Fetching full Git history and any existing tags..." -ForegroundColor Cyan
    & git fetch --tags origin
    Require-Success "git fetch"
    $commitLines = @(& git log main --format="%H|%s" -n 200)
    Require-Success "git log"
    $releaseMatches = @($commitLines | Where-Object { $_.EndsWith("|$releaseSubject") })
    if ($releaseMatches.Count -ne 1) {
        throw "Expected exactly one v0.5.4 documentation release commit on main; found $($releaseMatches.Count). Run git pull --ff-only origin main first."
    }
    $releaseSha = ($releaseMatches[0] -split "\|")[0]

    $entries = @(
    @{ Tag = "v0.1.0"; Commit = "592de96085603272a17c93d6e9abc00714fe3e85" }
    @{ Tag = "v0.2.0"; Commit = "fb93fc0bb01ca70e90f705a617e45a4e15506f76" }
    @{ Tag = "v0.3.0"; Commit = "44228e8b3edbaf9c3a2ea049b61689b0d54e9b15" }
    @{ Tag = "v0.4.0"; Commit = "5cfd920e5bfbd90804c325b9ed46c4d1790ccecd" }
    @{ Tag = "v0.4.1"; Commit = "bb17329687e9a5e40211e1e0ea6323806e539a1e" }
    @{ Tag = "v0.4.2"; Commit = "0d42a1a3f5fc6917c5ab1cab5d73264dc1b9d177" }
    @{ Tag = "v0.4.3"; Commit = "9fb667020321937629e71a1f8f6e71985d3a4784" }
    @{ Tag = "v0.4.4"; Commit = "4c51380f819bb09eb182feaa2edf266c79fc7f8e" }
    @{ Tag = "v0.4.5"; Commit = "737a89f1271af1e762caff3ba62492dbf7434cd5" }
    @{ Tag = "v0.4.6"; Commit = "f414b551bf47441ef67a710688d211a7b1d2e1cc" }
    @{ Tag = "v0.4.7"; Commit = "74f42c048554ea7eea5abb5c9bc113f560ac3e2c" }
    @{ Tag = "v0.4.8"; Commit = "8461a091884cf570d9b94753e14accf43af5d82f" }
    @{ Tag = "v0.4.9"; Commit = "534e41cb08b5764f160de35c02d7ef824ce7ddbd" }
    @{ Tag = "v0.5.0"; Commit = "41222d42a89f6395a94b11747be3362185eb4234" }
    @{ Tag = "v0.5.1"; Commit = "42b46b5cd832b5a9e97402a42095d8194fe66f23" }
    @{ Tag = "v0.5.2"; Commit = "ac465ee86f603834a8362d8f5c947f2d7fe322ca" }
    @{ Tag = "v0.5.3"; Commit = "fb179fbb5aed9880ec4137a2aef4fe68596c8d15" }
        @{ Tag = "v0.5.4"; Commit = $releaseSha }
    )

    # Preflight all historical versions and tag collisions BEFORE creating anything.
    $toCreate = @()
    foreach ($entry in $entries) {
        $tag = [string]$entry.Tag
        $sha = [string]$entry.Commit
        & git cat-file -e ("{0}^{{commit}}" -f $sha) 2>$null
        Require-Success "Commit lookup for $tag"
        $versionText = (& git show ("{0}:VERSION.json" -f $sha) | Out-String)
        Require-Success "VERSION.json lookup for $tag"
        $version = ($versionText | ConvertFrom-Json).version
        if ([string]$version -ne $tag.Substring(1)) {
            throw "$tag expects VERSION.json=$($tag.Substring(1)) but commit $sha contains $version"
        }
        & git show-ref --verify --quiet ("refs/tags/{0}" -f $tag)
        if ($LASTEXITCODE -eq 0) {
            $actual = (& git rev-parse ("refs/tags/{0}^{{commit}}" -f $tag)).Trim()
            Require-Success "Read existing tag $tag"
            if ($actual -ne $sha) {
                throw "Tag $tag already points to $actual instead of $sha. Refusing to overwrite it."
            }
            Write-Host "Existing tag OK: $tag -> $($sha.Substring(0, 12))" -ForegroundColor DarkGreen
        } elseif ($LASTEXITCODE -eq 1) {
            $toCreate += $entry
            Write-Host "Tag to create: $tag -> $($sha.Substring(0, 12))"
        } else {
            throw "Could not check tag $tag"
        }
    }

    if ($DryRun) {
        Write-Host "DRY RUN: $($toCreate.Count) tags would be created. No tags, pushes or release performed." -ForegroundColor Yellow
        return
    }

    foreach ($entry in $toCreate) {
        $tag = [string]$entry.Tag
        $sha = [string]$entry.Commit
        & git tag -a $tag $sha -m ("vGUITAR {0} - historical version" -f $tag)
        Require-Success "Create annotated tag $tag"
        Write-Host "Created $tag"
    }

    if ($PushAll) {
        foreach ($entry in $entries) {
            $tag = [string]$entry.Tag
            & git push origin ("refs/tags/{0}" -f $tag)
            Require-Success "Push tag $tag"
        }
        Write-Host "All 18 tags pushed to origin." -ForegroundColor Green
    }

    if ($PublishRelease) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
            throw "GitHub CLI (gh) is required to publish a Release. Install it and run 'gh auth login'."
        }
        & gh auth status
        Require-Success "gh auth status"
        if (-not $PushAll) {
            & git push origin ("refs/tags/{0}" -f $releaseTag)
            Require-Success "Push release tag"
        }
        # Windows PowerShell 5.1 converts native stderr (including gh's
        # expected 404 "release not found") into a terminating NativeCommandError
        # when ErrorActionPreference is Stop. Silence only this existence probe.
        # Restore the fail-fast preference before running the create operation.
        $oldErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & gh release view $releaseTag --repo $repoName --json tagName *> $null
            $releaseExists = ($LASTEXITCODE -eq 0)
        }
        finally {
            $ErrorActionPreference = $oldErrorActionPreference
        }
        if ($releaseExists) {
            Write-Host "Release $releaseTag already exists; skipping publication without overwriting notes." -ForegroundColor Yellow
        } else {
            & gh release create $releaseTag --repo $repoName --title "vGUITAR Note Trainer $releaseTag" --notes-file "docs/releases/v0.5.4.md" --verify-tag --latest
            Require-Success "Create GitHub Release"
            Write-Host "GitHub Release published: https://github.com/$repoName/releases/tag/$releaseTag" -ForegroundColor Green
        }
    } else {
        Write-Host "All historical tags are present locally. Use -PushAll -PublishRelease to publish." -ForegroundColor Green
    }
}
finally {
    Pop-Location
}
