. .\utils.ps1

# Main script 
$ytUrl = "https://www.dropbox.com/scl/fi/wqnuqe65xd0bxn3ed2ous/com.google.android.youtube_18.45.43-1541152192_minAPI26-arm64-v8a-armeabi-v7a-x86-x86_64-nodpi-_apkmirror.com.apk?rlkey=fkujhctrb1dko978htdl0r9bi&dl=0"
$version = [regex]::Match($ytUrl, '\d+(\.\d+)+').Value

$repositories = @{
    "revanced-cli" = "revanced/revanced-cli"
    "revanced-patches" = "revanced/revanced-patches"
    "revanced-integrations" = "revanced/revanced-integrations"
}

$repoOwner = $env:GITHUB_REPOSITORY_OWNER
$repoName = $env:GITHUB_REPOSITORY_NAME
$accessToken = $accessToken = $env:GITHUB_TOKEN
$tagName = Get-Date -Format "dd-MM-yyyy"
$apkFilePath = "youtube-revanced*.apk"
$patchFilePath = "revanced-patches*.jar"

# Perform Download-RepositoryAssets
foreach ($repo in $repositories.Keys) {
    Download-RepositoryAssets -repoName $repo -repoUrl $repositories[$repo]
}

# Get the body content of the script repository release
$scriptRepoLatestRelease = $null
try {
    $scriptRepoLatestRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/$repoOwner/$repoName/releases/latest" -Headers @{ Authorization = "token $accessToken" }
} catch {
    Install-ZuluJDK
    Download-YoutubeAPK -ytUrl $ytUrl -version $version
    Apply-Patches -version $version -ytUrl $ytUrl
    Sign-PatchedAPK -version $version
    Update-VersionFile -version $version
    Upload-ToGithub
    Create-GitHubRelease -tagName $tagName -accessToken $accessToken -apkFilePath $apkFilePath -patchFilePath $patchFilePath
    exit
}
$scriptRepoBody = $scriptRepoLatestRelease.body

# Get the downloaded patch file name
$downloadedPatchFileName = (Get-ChildItem -Filter "revanced-patches*.jar").BaseName

# Check if the body content matches the downloaded patch file name
if (Check-ReleaseBody -scriptRepoBody $scriptRepoBody -downloadedPatchFileName $downloadedPatchFileName) {
    Install-ZuluJDK
    Download-YoutubeAPK -ytUrl $ytUrl -version $version
    Apply-Patches -version $version -ytUrl $ytUrl
    Sign-PatchedAPK -version $version
    Update-VersionFile -version $version
    Upload-ToGithub
    Create-GitHubRelease -tagName $tagName -accessToken $accessToken -apkFilePath $apkFilePath -patchFilePath $patchFilePath
} else {
    Write-Host "Skipping because patched." -ForegroundColor Yellow
}
