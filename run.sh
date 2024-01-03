#!/bin/bash

declare -A repositories=(
    ["revanced-cli"]="revanced/revanced-cli"
    ["revanced-patches"]="revanced/revanced-patches"
    ["revanced-integrations"]="revanced/revanced-integrations"
)

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

wget -nv -O "yt.apk" "$(echo $YT_URL | sed 's/&dl=0/&dl=1/')"

mapfile -t lines < ./patches.txt

for line in "${lines[@]}"; do
    if [[ -n "$line" && ( ${line:0:1} == "+" || ${line:0:1} == "-" ) ]]; then
        patch_name=$(sed -e 's/^[+|-] *//;s/ *$//' <<< "$line") 
        [[ ${line:0:1} == "+" ]] && include_patches+=("--include" "$patch_name")
        [[ ${line:0:1} == "-" ]] && exclude_patches+=("--exclude" "$patch_name")
    fi
done

java -jar revanced-cli*.jar patch \
    --merge revanced-integrations*.apk \
    --patch-bundle revanced-patches*.jar \
    "${exclude_patches[@]}" \
    "${include_patches[@]}" \
    --out patched.apk \
    yt.apk

apksigner=$(find "$ANDROID_SDK_ROOT/build-tools" -name apksigner | sort -r | head -n 1)
"$apksigner" sign --ks public.jks \
    --ks-key-alias public \
    --ks-pass pass:public \
    --key-pass pass:public \
    --in patched.apk \
    --out "youtube-revanced-v18.45.43.apk"
