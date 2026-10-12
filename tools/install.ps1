[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GamePath,

    [switch]$Latest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$temporaryRoot = $null

function Get-GitHubRepositorySlug {
    param([Parameter(Mandatory = $true)][string]$RepositoryRoot)

    $remoteLines = @(& git -C $RepositoryRoot config --get remote.origin.url 2>$null)
    if ($LASTEXITCODE -ne 0 -or $remoteLines.Count -eq 0) {
        throw 'Cannot determine the GitHub repository. Configure the origin remote first.'
    }

    $remoteUrl = $remoteLines[0].Trim()
    if ($remoteUrl -notmatch 'github\.com[:/](?<Slug>[^/]+/[^/]+?)(?:\.git)?$') {
        throw "The origin remote is not a supported GitHub URL: $remoteUrl"
    }

    return $Matches.Slug
}

function Get-GitHubHeaders {
    $headers = @{
        Accept                 = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'User-Agent'           = 'anomaly-addon-installer'
    }

    $token = $env:GH_TOKEN
    if ([string]::IsNullOrWhiteSpace($token)) {
        $token = $env:GITHUB_TOKEN
    }

    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $headers.Authorization = "Bearer $token"
    }

    return $headers
}

function Copy-AddonFiles {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $sourceRoot = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\', '/')
    Get-ChildItem -LiteralPath $sourceRoot -File -Recurse -Force |
        Where-Object { $_.Name -ne '.gitkeep' } |
        ForEach-Object {
            $relativePath = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
            $destinationPath = Join-Path $Destination $relativePath
            $destinationDirectory = Split-Path -Parent $destinationPath
            New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destinationPath -Force
        }
}

try {
    if (-not (Test-Path -LiteralPath $GamePath -PathType Container)) {
        throw "GamePath does not exist or is not a directory: $GamePath"
    }

    $gameRoot = (Resolve-Path -LiteralPath $GamePath).Path
    $repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
    $sourceGamedata = Join-Path $repositoryRoot 'gamedata'

    if ($Latest) {
        $repositorySlug = Get-GitHubRepositorySlug -RepositoryRoot $repositoryRoot
        $repositoryName = ($repositorySlug -split '/')[-1]
        $headers = Get-GitHubHeaders
        $releaseApiUrl = "https://api.github.com/repos/$repositorySlug/releases/latest"

        Write-Host "Finding the latest release for $repositorySlug..."
        $release = Invoke-RestMethod -Uri $releaseApiUrl -Headers $headers
        $expectedAssetName = "$repositoryName-$($release.tag_name).zip"
        $asset = @($release.assets | Where-Object { $_.name -eq $expectedAssetName }) | Select-Object -First 1

        if ($null -eq $asset) {
            throw "Release $($release.tag_name) does not contain $expectedAssetName."
        }

        $temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("anomaly-addon-" + [guid]::NewGuid().ToString('N'))
        $archivePath = Join-Path $temporaryRoot $expectedAssetName
        $extractPath = Join-Path $temporaryRoot 'extracted'
        New-Item -ItemType Directory -Path $temporaryRoot, $extractPath -Force | Out-Null

        Write-Host "Downloading $expectedAssetName..."
        if ($headers.ContainsKey('Authorization')) {
            $downloadHeaders = $headers.Clone()
            $downloadHeaders.Accept = 'application/octet-stream'
            Invoke-WebRequest -Uri $asset.url -Headers $downloadHeaders -OutFile $archivePath
        }
        else {
            Invoke-WebRequest -Uri $asset.browser_download_url -Headers $headers -OutFile $archivePath
        }

        Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force
        $sourceGamedata = Join-Path $extractPath 'gamedata'
    }

    if (-not (Test-Path -LiteralPath $sourceGamedata -PathType Container)) {
        throw "Addon gamedata does not exist: $sourceGamedata"
    }

    $targetGamedata = Join-Path $gameRoot 'gamedata'
    if (-not (Test-Path -LiteralPath $targetGamedata -PathType Container)) {
        New-Item -ItemType Directory -Path $targetGamedata -Force | Out-Null
    }

    Write-Host "Installing addon files into $targetGamedata..."
    Copy-AddonFiles -Source $sourceGamedata -Destination $targetGamedata

    Write-Host 'Addon installed successfully.'
}
catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($null -ne $temporaryRoot -and (Test-Path -LiteralPath $temporaryRoot)) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
