#!/bin/bash

req() {
    wget -nv -O "$2" --header="Authorization: token $accessToken" "$1"
}

download_repository_assets() {
    local repoName=$1
    local repoUrl=$2
    local repoApiUrl="https://api.github.com/repos/$repoUrl/releases/latest"
    local response=$(req "$repoApiUrl" - 2>/dev/null)

    local assetUrls=$(echo "$response" | jq -r --arg repoName "$repoName" '.assets[] | select(.name | contains($repoName)) | .browser_download_url, .name')

    while read -r downloadUrl && read -r assetName; do
        color_green "Downloading asset: $assetName from: $downloadUrl"
        req "$downloadUrl" "$assetName"
    done <<< "$assetUrls"
}

download_youtube_apk() {
    local ytUrl=$1
    local version=$(echo "$ytUrl" | grep -oP '\d+(\.\d+)+')
    local youtubeDownloadUrl="$(echo $ytUrl | sed 's/0$/1/')"
    local assetName="youtube-v$version.apk"
    color_green "Downloading YouTube APK from: $youtubeDownloadUrl"
    req "$youtubeDownloadUrl" "$assetName"
}

apply_patches() {
    version=$1
    ytUrl=$2
    
    # Read patches from file
    mapfile -t lines < ./patches.txt

    # Process patches
    for line in "${lines[@]}"; do
        if [[ -n "$line" && ( ${line:0:1} == "+" || ${line:0:1} == "-" ) ]]; then
            patch_name=$(sed -e 's/^[+|-] *//;s/ *$//' <<< "$line") 
            [[ ${line:0:1} == "+" ]] && includePatches+=("--include" "$patch_name")
            [[ ${line:0:1} == "-" ]] && excludePatches+=("--exclude" "$patch_name")
        fi
    done

    # Apply patches using Revanced tools
    
    color_green "Patching..."
    java -jar revanced-cli*.jar patch \
        --merge revanced-integrations*.apk \
        --patch-bundle revanced-patches*.jar \
        "${excludePatches[@]}" "${includePatches[@]}" \
        --out "patched-youtube-v$version.apk" \
        "youtube-v$version.apk"
    color_green "Done"
}

sign_patched_apk() {
    version=$1
    
    # Sign the patched APK
    color_green "Sign APK"
    apksigner=$(find $ANDROID_SDK_ROOT/build-tools -name apksigner -type f | sort -r | head -n 1)
    $apksigner sign --ks public.jks \
        --ks-key-alias public \
        --ks-pass pass:public \
        --key-pass pass:public \
        --in "patched-youtube-v$version.apk" \
        --out "youtube-revanced-v$version.apk"
    color_green "Done"
}

update_version_file() {
    version=$1
    
    # Obtain highest supported version information using revanced-cli
    packageInfo=$(java -jar revanced-cli*.jar list-versions -f com.google.android.youtube revanced-patches*.jar)
    highestSupportedVersion=$(echo "$packageInfo" | grep -oP '\d+(\.\d+)+' | sort -r | head -n 1)

    # Remove all lines containing version information
    > version.txt
    
    # Write highest supported version to version.txt
    if [[ "$highestSupportedVersion" == "$version" ]]; then
        echo "Same $highestSupportedVersion version" >> version.txt
    elif [[ "$highestSupportedVersion" != "$version" ]]; then
        echo "Supported version is $highestSupportedVersion, Please update!" >> version.txt
    fi
}

upload_to_github() {
    git config --global user.email "$GITHUB_ACTOR_ID+$GITHUB_ACTOR@users.noreply.github.com" > /dev/null
    git config --global user.name "$(gh api "/users/$GITHUB_ACTOR" | jq -r '.name')" > /dev/null
    git add version.txt > /dev/null
    git commit -m "Update version" --author=. > /dev/null
    git push origin main > /dev/null
}

create_github_release() {
    local accessToken="$1"
    local repoOwner="$2"
    local repoName="$3"

    local tagName=$(date +"%d-%m-%Y")
    local patchFilePath=$(find . -type f -name "revanced-patches*.jar")
    local apkFilePath=$(find . -type f -name "youtube-revanced*.apk")
    local patchFileName=$(echo "$patchFilePath" | sed 's/.*\///' | sed 's/\.[^.]*$//')
    local apkFileName=$(echo "$apkFilePath")

    local releaseData=$(cat <<EOF
{
    "tag_name": "$tagName",
    "target_commitish": "main",
    "name": "Release $tagName",
    "body": "$patchFileName"
}
EOF
)

    # Only release with APK file
    if [ ! -f "$apkFilePath" ]; then
        exit
    fi

    # Check if the release with the same tag already exists
    local existingRelease=$(curl -s -H "Authorization: token $accessToken" "https://api.github.com/repos/$repoOwner/$repoName/releases/tags/$tagName")

    if [ -z "$existingRelease" ]; then
        local existingReleaseId=$(echo "$existingRelease" | jq -r ".id")

        # If the release exists, delete it
        curl -s -X DELETE -H "Authorization: token $accessToken" "https://api.github.com/repos/$repoOwner/$repoName/releases/$existingReleaseId" > /dev/null
        color_green "Existing release deleted with tag $tagName."
    fi

    # Create a new release
    local newRelease=$(curl -s -X POST -H "Authorization: token $accessToken" -H "Content-Type: application/json" -d "$releaseData" "https://api.github.com/repos/$repoOwner/$repoName/releases")
    local releaseId=$(echo "$newRelease" | jq -r ".id")

    # Upload APK file
    local uploadUrlApk="https://uploads.github.com/repos/$repoOwner/$repoName/releases/$releaseId/assets?name=$apkFileName"
    curl -s -H "Authorization: token $accessToken" -H "Content-Type: application/zip" --data-binary @"$apkFilePath" "$uploadUrlApk" > /dev/null

    color_green "GitHub Release created with ID $releaseId."
}

check_release_body() {
    scriptRepoBody=$1
    downloadedPatchFileName=$2

    # Compare body content with downloaded patch file name
    if [ "$scriptRepoBody" != "$downloadedPatchFileName" ]; then
        return 0
    else
        return 1
    fi
}

color_green() {
    echo -e "\e[92m[+] $1\e[0m"
}

color_red() {
    echo -e "\e[91m[+] $1\e[0m"
}

basename() {
    sed 's/.*\///' | sed 's/\.[^.]*$//'
}
