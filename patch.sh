#!/bin/bash

source utils.sh

# Main script 
accessToken=$GITHUB_TOKEN
repoName=$GITHUB_REPOSITORY_NAME
repoOwner=$GITHUB_REPOSITORY_OWNER
ytUrl="https://www.dropbox.com/scl/fi/wqnuqe65xd0bxn3ed2ous/com.google.android.youtube_18.45.43-1541152192_minAPI26-arm64-v8a-armeabi-v7a-x86-x86_64-nodpi-_apkmirror.com.apk?rlkey=fkujhctrb1dko978htdl0r9bi&dl=0"
version=$(echo $ytUrl | grep -oP '\d+(\.\d+)+')

declare -A repositories=(
    ["revanced-cli"]="revanced/revanced-cli"
    ["revanced-patches"]="revanced/revanced-patches"
    ["revanced-integrations"]="revanced/revanced-integrations"
)

# Perform download_repository_assets
for repo in "${!repositories[@]}"; do
    download_repository_assets "$repo" "${repositories[$repo]}"
done

# Get the body content of the script repository release
scriptRepoLatestRelease=$(req "https://api.github.com/repos/$repoOwner/$repoName/releases/latest" - 2>/dev/null || true)
scriptRepoBody=$(echo "$scriptRepoLatestRelease" | jq -r '.body')

# Get the downloaded patch file name
downloadedPatchFileName=$(ls -1 revanced-patches*.jar | basename)

# Patch if no release
if [ -z "$scriptRepoBody" ]; then
    download_youtube_apk "$ytUrl" "$version"
    apply_patches "$version" "$ytUrl"
    sign_patched_apk "$version"
    update_version_file "$version"
    upload_to_github
    create_github_release "$accessToken" "$repoOwner" "$repoName"
    exit 0
fi

# Check if the body content matches the downloaded patch file name
if check_release_body "$scriptRepoBody" "$downloadedPatchFileName"; then
    download_youtube_apk "$ytUrl" "$version"
    apply_patches "$version" "$ytUrl"
    sign_patched_apk "$version"
    update_version_file "$version"
    upload_to_github
    create_github_release "$accessToken" "$repoOwner" "$repoName"
else
    color_red "Skipping because patched."
fi
