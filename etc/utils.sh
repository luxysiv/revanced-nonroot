#!/bin/bash
# Script make by Mạnh Dương

# Make requests to Github API
gh_req() {
    wget -qO- --header="Authorization: token $GITHUB_TOKEN" "$@"
}

# Make fake requests with User-Agent and Authorization 
req() {
    wget -nv -O "$@" \
    --header="User-Agent: Mozilla/5.0 (Linux; Android 10; K) \
                          AppleWebKit/537.36 (KHTML, like Gecko) \
                          Chrome/126.0.0.0 Mobile Safari/537.36 EdgA/126.0.0.0" \
    --header="Authorization: Basic YXBpLWFwa3VwZGF0ZXI6cm01cmNmcnVVakt5MDRzTXB5TVBKWFc4" \
    --header="Content-Type: application/json"
}

# Get highest version (Just compatible with my way of getting versions code)
get_latest_version() {
    grep -Evi 'alpha|beta' | grep -oPi '\b\d+(\.\d+)+(?:\-\w+)?(?:\.\d+)?(?:\.\w+)?\b' | sort -ur | sed -n '1p'
}

# Read highest supported versions from Revanced 
get_supported_version() {
    pkg_name="$1"
    jq -r '.. | objects | select(.name == "'$pkg_name'" and .versions != null) | .versions[-1]' patches.json | uniq
}

# Download necessary resources to patch from Github latest release 
download_resources() {
    for repo in revanced-patches revanced-cli revanced-integrations; do
        githubApiUrl="https://api.github.com/repos/revanced/$repo/releases/latest"
        page=$(req - 2>/dev/null $githubApiUrl)
        assetUrls=$(echo $page | jq -r '.assets[] | select(.name | endswith(".asc") | not) | "\(.browser_download_url) \(.name)"')
        while read -r downloadUrl assetName; do
            req "$assetName" "$downloadUrl" 
        done <<< "$assetUrls"
    done
}

# Get 20 versions of application on APKmirror pages 
get_apkmirror_version() {
    grep 'fontBlack' | sed -n 's/.*>\(.*\)<\/a> <\/h5>.*/\1/p' | sed 20q
}

# Best but sometimes not work because APKmirror protection 
apkmirror() {
    org="$1" name="$2" package="$3" arch="$4" 
    local regexp='.*APK\(.*\)'$arch'\(.*\)nodpi<\/div>[^@]*@\([^<]*\)'
    version="${version:-$(get_supported_version "$package")}"
    url="https://www.apkmirror.com/uploads/?appcategory=$name"
    version="${version:-$(req - $url | get_apkmirror_version | get_latest_version)}"
    url="https://www.apkmirror.com/apk/$org/$name/$name-${version//./-}-release"
    url="https://www.apkmirror.com$(req - $url | tr '\n' ' ' | sed -n 's#.*href="\(.*apk/[^"]*\)">'$regexp'.*#\1#p')"
    url="https://www.apkmirror.com$(req - $url | tr '\n' ' ' | sed -n 's#.*href="\(.*key=[^"]*\)">.*#\1#p')"
    url="https://www.apkmirror.com$(req - $url | tr '\n' ' ' | sed -n 's#.*href="\(.*key=[^"]*\)">.*#\1#g;s#amp;##g;p')"
    req $name-v$version.apk $url
}

# X not work (maybe more)
uptodown() {
    name=$1 package=$2
    version="${version:-$(get_supported_version "$package")}"
    url="https://$name.en.uptodown.com/android/versions"
    version="${version:-$(req - 2>/dev/null $url | sed -n 's/.*class="version">\([^<]*\)<.*/\1/p' | get_latest_version)}"
    url=$(req - $url | tr '\n' ' ' \
                     | sed -n 's/.*data-url="\([^"]*\)".*'$version'<\/span>[^@]*@\([^<]*\).*/\1/p' \
                     | sed 's#/download/#/post-download/#g')
    url="https://dw.uptodown.com/dwn/$(req - $url | sed -n 's/.*class="post-download".*data-url="\([^"]*\)".*/\1/p')"
    req $name-v$version.apk $url
}

# Tiktok not work because not available version supported 
apkpure() {
    name=$1 package=$2
    version="${version:-$(get_supported_version "$package")}"
    url="https://apkpure.net/$name/$package/versions"
    version="${version:-$(req - $url | sed -n 's/.*data-dt-version="\([^"]*\)".*/\1/p' | sed 10q | get_latest_version)}"
    url="https://apkpure.net/$name/$package/download/$version"
    url=$(req - $url | sed -n 's/.*href="\(.*\/APK\/'$package'[^"]*\).*/\1/p' | uniq)
    req $name-v$version.apk $url
}

# Apply patches with Include and Exclude Patches
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

# Sign APK with FOSS keystore(https://github.com/tytydraco/public-keystore)
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

# Make body Release 
create_body_release() {
    body=$(cat <<EOF
# Release Notes

## Build Tools:
- **ReVanced Patches:** v$patchver
- **ReVanced Integrations:** v$integrationsver
- **ReVanced CLI:** v$cliver

## Note:
**ReVancedGms** is **necessary** to work. 
- Please **download** it from [HERE](https://github.com/revanced/gmscore/releases/latest).
EOF
)

    releaseData=$(jq -n \
      --arg tag_name "$tagName" \
      --arg target_commitish "main" \
      --arg name "Revanced $tagName" \
      --arg body "$body" \
      '{ tag_name: $tag_name, target_commitish: $target_commitish, name: $name, body: $body }')
}

# Release Revanced APK
create_github_release() {
    name="$1"
    apiReleases="https://api.github.com/repos/$GITHUB_REPOSITORY/releases"
    uploadRelease="https://uploads.github.com/repos/$GITHUB_REPOSITORY/releases"
    apkFilePath=$(find . -type f -name "$name-revanced*.apk")
    apkFileName=$(basename "$apkFilePath")
    patchver=$(ls -1 revanced-patches*.jar | grep -oP '\d+(\.\d+)+')
    integrationsver=$(ls -1 revanced-integrations*.apk | grep -oP '\d+(\.\d+)+')
    cliver=$(ls -1 revanced-cli*.jar | grep -oP '\d+(\.\d+)+')
    tagName="v$patchver"

    # Make sure release with APK
    if [ ! -f "$apkFilePath" ]; then
        exit
    fi

    existingRelease=$(gh_req "$apiReleases/tags/$tagName")

    # Add more assets release with same tag name
    if [ -n "$existingRelease" ]; then
        existingReleaseId=$(echo "$existingRelease" | jq -r ".id")
        uploadUrlApk="$uploadRelease/$existingReleaseId/assets?name=$apkFileName"

        # Delete assest release if same name upload 
        for existingAsset in $(echo "$existingRelease" | jq -r '.assets[].name'); do
            [ "$existingAsset" == "$apkFileName" ] && \
                assetId=$(echo "$existingRelease" | jq -r '.assets[] | select(.name == "'"$apkFileName"'") | .id') && \
                gh_req --method=DELETE "$apiReleases/assets/$assetId"
        done
    else
        # Make tag name
        create_body_release 
        newRelease=$(gh_req --post-data="$releaseData" --header="Content-Type: application/json" "$apiReleases")
        releaseId=$(echo "$newRelease" | jq -r ".id")
        uploadUrlApk="$uploadRelease/$releaseId/assets?name=$apkFileName"
    fi

    # Upload file to Release 
    gh_req &>/dev/null --header="Content-Type: application/zip" --post-file="$apkFilePath" "$uploadUrlApk"
}
