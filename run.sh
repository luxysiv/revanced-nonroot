#!/bin/bash

# Dropbox YouTube UrL
yt_url="https://www.dropbox.com/scl/fi/wqnuqe65xd0bxn3ed2ous/com.google.android.youtube_18.45.43-1541152192_minAPI26-arm64-v8a-armeabi-v7a-x86-x86_64-nodpi-_apkmirror.com.apk?rlkey=fkujhctrb1dko978htdl0r9bi&dl=0"

# Take version from Dropbox link
version=$(echo "$yt_url" | grep -oP '\d+(\.\d+)+')

# Declare repositories
declare -A repositories=(
    ["revanced-cli"]="revanced/revanced-cli"
    ["revanced-patches"]="revanced/revanced-patches"
    ["revanced-integrations"]="revanced/revanced-integrations"
)

# Download latest releases for specified repositories
for repo in "${!repositories[@]}"; do
    response=$(wget -nv -O- "https://api.github.com/repos/${repositories[$repo]}/releases/latest")

    asset_urls=($(
        echo "$response" | jq -r --arg repo_name "$repo" \
        '.assets[] | select(.name | contains($repo_name)) | "\(.browser_download_url) \(.name)"'
    ))

    for ((i = 0; i < ${#asset_urls[@]}; i += 2)); do
        wget -nv -O "${asset_urls[i+1]}" "${asset_urls[i]}"
    done
done

# Download YouTube APK
wget -nv -O "youtube-v$version.apk" "$(echo $yt_url | sed 's/0$/1/')"

# Read patches from file
mapfile -t lines < ./patches.txt

# Process patches
for line in "${lines[@]}"; do
    if [[ -n "$line" && ( ${line:0:1} == "+" || ${line:0:1} == "-" ) ]]; then
        patch_name=$(sed -e 's/^[+|-] *//;s/ *$//' <<< "$line") 
        [[ ${line:0:1} == "+" ]] && include_patches+=("--include" "$patch_name")
        [[ ${line:0:1} == "-" ]] && exclude_patches+=("--exclude" "$patch_name")
    fi
done

# Apply patches using Revanced tools
java -jar revanced-cli*.jar patch \
    --merge revanced-integrations*.apk \
    --patch-bundle revanced-patches*.jar \
    "${exclude_patches[@]}" \
    "${include_patches[@]}" \
    --out "patched-youtube-v$version.apk" \
    "youtube-v$version.apk"

# Sign the patched APK
apksigner=$(find "$ANDROID_SDK_ROOT/build-tools" -name apksigner | sort -r | head -n 1)
"$apksigner" sign --ks public.jks \
    --ks-key-alias public \
    --ks-pass pass:public \
    --key-pass pass:public \
    --in "patched-youtube-v$version.apk" \
    --out "youtube-revanced-v$version.apk"

# Obtain highest supported version information using revanced-cli
package_info=$(java -jar revanced-cli*.jar list-versions -f com.google.android.youtube revanced-patches*.jar)
highest_supported_version=$(echo "$package_info" | grep -oP '\d+(\.\d+)+' | sort -ur | sed -n '1p')

# Remove all lines containing version information
sed -i '/[0-9.]\+/d' version.txt

# Write highest supported version to version.txt
[[$highest_supported_version == $version]] && echo "Same $highest_supported_version version"
[[$highest_supported_version != $version]] && echo "Supported version is $highest_supported_version , Pls update!"

# Upload version.txt to Github 
git config --global user.email "${GITHUB_ACTOR_ID}+${GITHUB_ACTOR}@users.noreply.github.com" > /dev/null 2>&1
git config --global user.name "$(gh api /users/${GITHUB_ACTOR} | jq .name -r)" > /dev/null 2>&1
git add version.txt > /dev/null 2>&1
git commit -m "Update version" --author=. > /dev/null 2>&1
git push origin main > /dev/null 2>&1
