function Download-RepositoryAssets {
    param (
        [string]$repoName,
        [string]$repoUrl
    )

    $repoApiUrl = "https://api.github.com/repos/$repoUrl/releases/latest"
    $response = Invoke-RestMethod -Uri $repoApiUrl

    $assetUrls = $response.assets | Where-Object { $_.name -match $repoName } | ForEach-Object { "$($_.browser_download_url) $($_.name)" }

    foreach ($url in $assetUrls) {
        $urlParts = $url -split ' '
        Write-Host "Downloading asset: $($urlParts[1]) from: $($urlParts[0])" -ForegroundColor Cyan
        Invoke-WebRequest -Uri $urlParts[0] -OutFile $urlParts[1] -UseBasicParsing -Verbose
    }
}

function Download-YoutubeAPK {
    param (
        [string]$ytUrl,
        [string]$version
    )

    $youtubeDownloadUrl = "$($ytUrl -replace '0$', '1')"
    Write-Host "Downloading YouTube APK from: $youtubeDownloadUrl" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $youtubeDownloadUrl -OutFile "youtube-v$version.apk" -UseBasicParsing -Verbose
}

function Apply-Patches {
    param (
        [string]$version,
        [string]$ytUrl
    )

    # Process patches
    $lines = Get-Content -Path .\patches.txt

    $includePatches = @()
    $excludePatches = @()

    foreach ($line in $lines) {
        if ($line -match '^([+|-])\s*(.+)') {
            $patchName = $Matches[2]

            if ($Matches[1] -eq '+') {
                $includePatches += "--include", $patchName
            } elseif ($Matches[1] -eq '-') {
                $excludePatches += "--exclude", $patchName
            }
        }
    }

    # Apply patches using Revanced tools
    java -jar revanced-cli*.jar patch `
        --merge revanced-integrations*.apk `
        --patch-bundle revanced-patches*.jar `
        $($excludePatches + $includePatches) `
        --out "patched-youtube-v$version.apk" `
        "youtube-v$version.apk"
}

function Sign-PatchedAPK {
    param (
        [string]$version
    )

    # Sign the patched APK
    $apksigner = Get-ChildItem -Path "$env:ANDROID_SDK_ROOT/build-tools" -Filter apksigner -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    & $apksigner.FullName sign --ks public.jks `
        --ks-key-alias public `
        --ks-pass pass:public `
        --key-pass pass:public `
        --in "patched-youtube-v$version.apk" `
        --out "youtube-revanced-v$version.apk"
}

function Update-VersionFile {
    param (
        [string]$version
    )

    # Obtain highest supported version information using revanced-cli
    $packageInfo = java -jar revanced-cli*.jar list-versions -f com.google.android.youtube revanced-patches*.jar
    $highestSupportedVersion = [regex]::Matches($packageInfo, '\d+(\.\d+)+') | ForEach-Object { $_.Value } | Sort-Object -Descending | Select-Object -First 1

    # Remove all lines containing version information
    (Get-Content -Path .\version.txt) -notmatch '[0-9.]' | Set-Content -Path .\version.txt

    # Write highest supported version to version.txt
    if ($highestSupportedVersion -eq $version) {
        Add-Content -Path .\version.txt -Value "Same $highestSupportedVersion version"
    } elseif ($highestSupportedVersion -ne $version) {
        Add-Content -Path .\version.txt -Value "Supported version is $highestSupportedVersion, Please update!"
    }
}

function Upload-ToGithub {
    # Upload version.txt to Github
    git config --global user.email "$env:GITHUB_ACTOR_ID+$env:GITHUB_ACTOR@users.noreply.github.com" > $null
    git config --global user.name "$((gh api "/users/$env:GITHUB_ACTOR" | ConvertFrom-Json).name)" > $null
    git add version.txt > $null
    git commit -m "Update version" --author=. > $null
    git push origin main > $null
}

function Create-GitHubRelease {
    param (
        [string]$tagName,
        [string]$accessToken,
        [string]$apkFilePath,
        [string]$patchFilePath
    )

    $patchFileName = (Get-Item $patchFilePath).BaseName
    $apkFileName = (Get-Item $apkFilePath).Name
    
    $releaseData = @{
        tag_name = $tagName
        target_commitish = "main" 
        name = "Release $tagName"
        body = "$patchFileName"  
    } | ConvertTo-Json

    # Check if the release with the same tag already exists
    try {
        $existingRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/$repoOwner/$repoName/releases/tags/$tagName" -Headers @{ Authorization = "token $accessToken" }

        # If the release exists, delete it
        Invoke-RestMethod -Uri "https://api.github.com/repos/$repoOwner/$repoName/releases/$($existingRelease.id)" -Headers @{ Authorization = "token $accessToken" } -Method Delete
        Write-Host "Existing release deleted with tag $tagName."

        # Continue to create a new release
        $newRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/$repoOwner/$repoName/releases" -Headers @{ Authorization = "token $accessToken" } -Method Post -Body $releaseData -ContentType "application/json"
        $releaseId = $newRelease.id

        # Upload APK file
        $uploadUrlApk = "https://uploads.github.com/repos/$repoOwner/$repoName/releases/$releaseId/assets?name=$apkFileName"
        Invoke-RestMethod -Uri $uploadUrlApk -Headers @{ Authorization = "token $accessToken" } -Method Post -InFile $apkFilePath -ContentType "application/zip" | Out-Null

        Write-Host "GitHub Release created with ID $releaseId."
    } catch {
        Write-Host "No existing release found with tag $tagName."

        # Create a new release
        $newRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/$repoOwner/$repoName/releases" -Headers @{ Authorization = "token $accessToken" } -Method Post -Body $releaseData -ContentType "application/json"
        $releaseId = $newRelease.id

        # Upload APK file
        $uploadUrlApk = "https://uploads.github.com/repos/$repoOwner/$repoName/releases/$releaseId/assets?name=$apkFileName"
        Invoke-RestMethod -Uri $uploadUrlApk -Headers @{ Authorization = "token $accessToken" } -Method Post -InFile $apkFilePath -ContentType "application/zip" | Out-Null

        Write-Host "GitHub Release created with ID $releaseId."
    }
}

function Check-ReleaseBody {
    param (
        [string]$scriptRepoBody,
        [string]$downloadedPatchFileName
    )

    # Compare body content with downloaded patch file name
    if ($scriptRepoBody -ne $downloadedPatchFileName) {
        return $true 
    } else {
        return $false  
    }
}

function Install-ZuluJDK {
    
    $urlResponse = Invoke-RestMethod -Uri "https://api.azul.com/zulu/download/community/v1.0/bundles/latest/?jdk_version=&bundle_type=jdk&javafx=false&ext=msi&os=windows&arch=x86&hw_bitness=64" -UseBasicParsing
    $url = $urlResponse.url

    $zuluTag = $urlResponse.jdk_version -replace ' ', '.'
    "ZuluTag=$zuluTag" >> $env:GITHUB_ENV

    Invoke-RestMethod -Uri $url -OutFile "Temp\zulu-jdk-win_x64.msi" -UseBasicParsing

    Write-Verbose "Installing Zulu JDK"

    Start-Process -FilePath "msiexec" -ArgumentList '/i "Temp\zulu-jdk-win_x64.msi" /quiet /qb /norestart' -Wait

    Remove-Item -Path "Temp\zulu-jdk-win_x64.msi" -Force
}
