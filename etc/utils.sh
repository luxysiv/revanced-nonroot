#!/bin/bash
api="https://api.revanced.app/v2/patches/latest"

req() {
    wget -nv -O "$1" "$2" \
    --header="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                          AppleWebKit/537.36 (HTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36" \
    --header="Authorization: Basic YXBpLWFwa3VwZGF0ZXI6cm01cmNmcnVVakt5MDRzTXB5TVBKWFc4" \
    --header="Content-Type: application/json"
}

get_latest_version() {
    grep -Evi 'alpha|beta' | grep -oPi '\b\d+(\.\d+)+(?:\-\w+)?(?:\.\d+)?(?:\.\w+)?\b' | sort -ur | sed -n '1p'
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

get_apkmirror_version() {
    grep 'fontBlack' | sed -n 's/.*>\(.*\)<\/a> <\/h5>.*/\1/p' | sed 20q
}

# Best but sometimes not work because APKmirror protection 
apkmirror() {
    org="$1" name="$2" package="$3" arch="$4" 
    local regexp='.*APK\(.*\)'$arch'\(.*\)nodpi<\/div>[^@]*@\([^<]*\)'
    version=$(req - 2>/dev/null $api | get_supported_version "$package")
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
    version=$(req - 2>/dev/null $api | get_supported_version "$package")
    url="https://$name.en.uptodown.com/android/versions"
    version="${version:-$(req - 2>/dev/null "$url" | sed -n 's/.*class="version">\([^<]*\)<.*/\1/p' | get_latest_version)}"
    url=$(req - $url | tr '\n' ' ' \
                     | sed -n 's/.*data-url="\([^"]*\)".*'$version'<\/span>[^@]*@\([^<]*\).*/\1/p' \
                     | sed 's#/download/#/post-download/#g')
    url="https://dw.uptodown.com/dwn/$(req - $url | sed -n 's/.*class="post-download".*data-url="\([^"]*\)".*/\1/p')"
    req $name-v$version.apk $url
}

# Tiktok not work because not available version supported 
apkpure() {
    name=$1 package=$2
    version=$(req - 2>/dev/null $api | get_supported_version "$package")
    url="https://apkpure.net/$name/$package/versions"
    version="${version:-$(req - $url | sed -n 's/.*data-dt-version="\([^"]*\)".*/\1/p' | sed 10q | get_latest_version)}"
    url="https://apkpure.net/$name/$package/download/$version"
    url=$(req - $url | sed -n 's/.*href="\(.*\/APK\/'$package'[^"]*\).*/\1/p' | uniq)
    req $name-v$version.apk $url
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
    apkFilePath=$(find . -type f -name "$name-revanced*.apk")
    apkFileName=$(basename "$apkFilePath")
    patchver=$(ls -1 revanced-patches*.jar | grep -oP '\d+(\.\d+)+')
    integrationsver=$(ls -1 revanced-integrations*.apk | grep -oP '\d+(\.\d+)+')
    cliver=$(ls -1 revanced-cli*.jar | grep -oP '\d+(\.\d+)+')
    tagName="v$patchver"

    # Only release with APK file
    if [ ! -f "$apkFilePath" ]; then
        exit
    fi

    # Check if the release with the same tag already exists
    existingRelease=$( \
        wget -qO- \
        --header="Authorization: token $accessToken" \
        "https://api.github.com/repos/$repoOwner/$repoName/releases/tags/$tagName" \
    )

    if [ -n "$existingRelease" ]; then
        existingReleaseId=$(echo "$existingRelease" | jq -r ".id")

        uploadUrlApk="https://uploads.github.com/repos/$repoOwner/$repoName/releases/$existingReleaseId/assets?name=$apkFileName"
    else
        # Create a new release
        body="# Build Tools:"
        body+="\n - **ReVanced Patches:** *v$patchver*"
        body+="\n - **ReVanced Integrations:** *v$integrationsver*"
        body+="\n - **ReVanced CLI:** *v$cliver*"
        body+="\n\n# Note:"
        body+="\n**ReVancedGms** is **necessary** to work"
        body+="\n - Click [HERE](https://github.com/revanced/gmscore/releases/latest) to **download**"
        local releaseData='{
            "tag_name": "'$tagName'",
            "target_commitish": "main",
            "name": "Revanced '$tagName'",
            "body": "'$body'"
        }'
            
        newRelease=$( \
            wget -qO- \
            --post-data="$releaseData" \
            --header="Authorization: token $accessToken" \
            --header="Content-Type: application/json" \
            "https://api.github.com/repos/$repoOwner/$repoName/releases" \
        )
        releaseId=$(echo "$newRelease" | jq -r ".id")

        uploadUrlApk="https://uploads.github.com/repos/$repoOwner/$repoName/releases/$releaseId/assets?name=$apkFileName"
    fi

    # Upload APK file
    wget -q \
        --header="Authorization: token $accessToken" \
        --header="Content-Type: application/zip" \
        --post-file="$apkFilePath" \
        -O /dev/null "$uploadUrlApk"
}
