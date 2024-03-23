#!/bin/bash
UserAgent="Chrome/74.0.3729.169"

req() {
    wget -U "$UserAgent" -nv -O "$1" "$2"
}

basename() {
    sed 's/.*\///' | sed 's/\.[^.]*$//'
}

get_latest_version() {
    grep -Evi 'alpha|beta' | grep -oPi '\b\d+(\.\d+)+(?:\-\w+)?(?:\.\d+)?(?:\.\w+)?\b' | sort -ur | grep -m 1 "."
}

get_supported_version() {
    jq -r --arg pkg_name "$1" '.. | objects | select(.name == "\($pkg_name)" and .versions != null) | .versions[-1]' | uniq
}

download_resources() {
    local revancedApiUrl="https://releases.revanced.app/tools"
    local response=$(req - 2>/dev/null "$revancedApiUrl")

    local assetUrls=$( \
        echo "$response" | \
        jq -r '.tools[] | select(.name | test("revanced-(patches|cli).*jar$|revanced-integrations.*apk$")) | .browser_download_url, .name' \
    )

    while read -r downloadUrl && read -r assetName; do
        req "$assetName" "$downloadUrl" 
    done <<< "$assetUrls"
}

# Tiktok not work because not available version supported 
apkpure() {
    name=$1 package=$2
    url="https://apkpure.net/$name/$package/versions"
    version=$(req - 2>/dev/null "https://api.revanced.app/v2/patches/latest" | get_supported_version "$package")
    version="${version:-$(req - "$url" | sed -n 's/.*data-dt-version="\([^"]*\)".*/\1/p' | sed 10q | get_latest_version)}"
    url="https://apkpure.net/$name/$package/download/$version"
    url=$(req - "$url" | sed -n 's/.*href="\(https:\/\/.*\.apkpure\..*\/.*\/APK\/'$package'[^"]*\).*/\1/p' | uniq)
}

apply_patches() {   
    name="$1"
    # Read patches from file
    mapfile -t lines < ./etc/$name-patches.txt

    # Process patches
    for line in "${lines[@]}"; do
        if [[ -n "$line" && ( ${line:0:1} == "+" || ${line:0:1} == "-" ) ]]; then
            patch_name=$(sed -e 's/^[+|-] *//;s/ *$//' <<< "$line") 
            [[ ${line:0:1} == "+" ]] && includePatches+=("--include" "$patch_name")
            [[ ${line:0:1} == "-" ]] && excludePatches+=("--exclude" "$patch_name")
        fi
    done
    
    # Apply patches using Revanced tools
    java -jar revanced-cli*.jar patch \
        --merge revanced-integrations*.apk \
        --patch-bundle revanced-patches*.jar \
        "${excludePatches[@]}" "${includePatches[@]}" \
        --out "patched-$name-v$version.apk" \
        "$name-v$version.apk"
    rm $name-v$version.apk
    unset excludePatches includePatches
}

sign_patched_apk() {   
    name="$1"
    # Sign the patched APK
    apksigner=$(find $ANDROID_SDK_ROOT/build-tools -name apksigner -type f | sort -r | head -n 1)
    $apksigner sign --verbose \
        --ks ./etc/public.jks \
        --ks-key-alias public \
        --ks-pass pass:public \
        --key-pass pass:public \
        --in "patched-$name-v$version.apk" \
        --out "$name-revanced-v$version.apk"
    rm patched-$name-v$version.apk
    unset version
}

create_github_release() {
    name="$1"
    local tagName=$(date +"%d-%m-%Y")
    local patchFilePath=$(find . -type f -name "revanced-patches*.jar")
    local apkFilePath=$(find . -type f -name "$name-revanced*.apk")
    local patchFileName=$(echo "$patchFilePath" | basename)
    local apkFileName=$(echo "$apkFilePath" | basename).apk

    # Only release with APK file
    if [ ! -f "$apkFilePath" ]; then
        exit
    fi

    # Check if the release with the same tag already exists
    local existingRelease=$( \
        wget -qO- \
        --header="Authorization: token $accessToken" \
        "https://api.github.com/repos/$repoOwner/$repoName/releases/tags/$tagName" \
    )

    if [ -n "$existingRelease" ]; then
        local existingReleaseId=$(echo "$existingRelease" | jq -r ".id")

        # Upload additional file to existing release
        local uploadUrlApk="https://uploads.github.com/repos/$repoOwner/$repoName/releases/$existingReleaseId/assets?name=$apkFileName"
        wget -q \
        --header="Authorization: token $accessToken" \
        --header="Content-Type: application/zip" \
        --post-file="$apkFilePath" \
        -O /dev/null "$uploadUrlApk"

    else
        # Create a new release
        local releaseData='{
            "tag_name": "'"$tagName"'",
            "target_commitish": "main",
            "name": "Release '"$tagName"'",
            "body": "'"$patchFileName"'"
        }'
        local newRelease=$( \
            wget -qO- \
            --post-data="$releaseData" \
            --header="Authorization: token $accessToken" \
            --header="Content-Type: application/json" \
            "https://api.github.com/repos/$repoOwner/$repoName/releases" \
        )
        local releaseId=$(echo "$newRelease" | jq -r ".id")

        # Upload APK file
        local uploadUrlApk="https://uploads.github.com/repos/$repoOwner/$repoName/releases/$releaseId/assets?name=$apkFileName"
        wget -q \
        --header="Authorization: token $accessToken" \
        --header="Content-Type: application/zip" \
        --post-file="$apkFilePath" \
        -O /dev/null "$uploadUrlApk"
    fi
}

check_release_body() {
    # Compare body content with downloaded patch file name
    if [ "$scriptRepoBody" != "$downloadedPatchFileName" ]; then
        return 0
    else
        return 1
    fi
}

# Activity patches APK
patch() {
    apkpure "youtube" \
            "com.google.android.youtube"
    apply_patches "youtube"
    sign_patched_apk "youtube"
    create_github_release "youtube"
    apkpure "youtube-music" \
            "com.google.android.apps.youtube.music"
    apply_patches "youtube-music"
    sign_patched_apk "youtube-music"
    create_github_release "youtube-music"
}

# Main script 
accessToken=$GITHUB_TOKEN
repoName=$GITHUB_REPOSITORY_NAME
repoOwner=$GITHUB_REPOSITORY_OWNER

# Perform download_repository_assets
download_resources

# Get the body content of the script repository release
scriptRepoLatestRelease=$( \
    wget -nv -O- 2>/dev/null \
    "https://api.github.com/repos/$repoOwner/$repoName/releases/latest" \
    --header="Authorization: token $accessToken" || true \
)
scriptRepoBody=$(echo "$scriptRepoLatestRelease" | jq -r '.body')

# Get the downloaded patch file name
downloadedPatchFileName=$(ls -1 revanced-patches*.jar | basename)

# Patch if no release
if [ -z "$scriptRepoBody" ]; then
    patch
    exit 0
fi

# Check if the body content matches the downloaded patch file name
if check_release_body ; then
    patch
else
    echo -e "\e[91mSkipping because patched\e[0m"
fi
