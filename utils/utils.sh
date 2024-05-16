#!/bin/bash
# Script make by Mạnh Dương

# Make requests like send from Firefox Android 
req() {
    wget --header="User-Agent: Mozilla/5.0 (Android 13; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0" \
         --header="Content-Type: application/octet-stream" \
         --header="Accept-Language: en-US,en;q=0.9" \
         --header="Connection: keep-alive" \
         --header="Upgrade-Insecure-Requests: 1" \
         --header="Cache-Control: max-age=0" \
         --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8" \
         --keep-session-cookies --timeout=30 -nv -O "$@"
}

# Download necessary resources to patch from Github latest release 
download_resources() {
    for repo in revanced-patches revanced-cli revanced-integrations; do
        githubApiUrl="https://api.github.com/repos/revanced/$repo/releases/latest"
        assetUrls=$(req - 2>/dev/null $githubApiUrl | perl utils/extract_github.pl)
        while read -r downloadUrl assetName; do
            req "$assetName" "$downloadUrl" 
        done <<< "$assetUrls"
    done
}

# Best but sometimes not work because APKmirror protection 
apkmirror() {
    org="$1" name="$2" package="$3" arch="${4:-universal}" dpi="${5:-nodpi}"
    version="${version:-$(cat patches.json | perl utils/extract_supported_version.pl "$package")}"
    url="https://www.apkmirror.com/uploads/?appcategory=$name"
    version="${version:-$(req - $url | perl utils/apkmirror_versions.pl | perl utils/largest_version.pl)}"
    url="https://www.apkmirror.com/apk/$org/$name/$name-${version//./-}-release"
    url=$(req - $url | perl utils/apkmirror_dl_page.pl $dpi $arch)
    url=$(req - $url | perl utils/apkmirror_dl_link.pl)
    url=$(req - $url | perl utils/apkmirror_final_link.pl)
    req $name-v$version.apk $url
}

# X not work (maybe more)
uptodown() {  
    name=$1 package=$2
    version="${version:-$(cat patches.json | perl utils/extract_supported_version.pl "$package")}"
    url="https://$name.en.uptodown.com/android/versions"
    version="${version:-$(req - 2>/dev/null $url | perl utils/uptodown_latest_version.pl)}"
    url=$(req - $url | perl utils/uptodown_dl_page.pl $version)
    url=$(req - $url | perl utils/uptodown_final_link.pl)
    req $name-v$version.apk $url
}

# Tiktok not work because not available version supported 
apkpure() {   
    name=$1 package=$2
    url="https://apkpure.net/$name/$package/versions"
    version="${version:-$(cat patches.json | perl utils/extract_supported_version.pl "$package")}"
    version="${version:-$(req - $url | perl utils/apkpure_latest_version.pl)}"
    url="https://apkpure.net/$name/$package/download/$version"
    url=$(req - $url | perl utils/apkpure_dl_link.pl $package)
    req $name-v$version.apk $url
}

# Apply patches with Include and Exclude Patches
apply_patches() {
    name="$1"    
    perl utils/apply_patches.pl "$name" "$version"
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
**ReVanced GmsCore** is **necessary** to work. 
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
github_release() {
    name="$1"
    authorization="Authorization: token $GITHUB_TOKEN" 
    apiReleases="https://api.github.com/repos/$GITHUB_REPOSITORY/releases"
    uploadRelease="https://uploads.github.com/repos/$GITHUB_REPOSITORY/releases"
    apkFilePath=$(find . -type f -name "$name-revanced*.apk")
    apkFileName=$(basename "$apkFilePath")
    patchver=$(perl utils/extract_version.pl "revanced-patches*.jar")
    integrationsver=$(perl utils/extract_version.pl "revanced-integrations*.apk")
    cliver=$(perl utils/extract_version.pl "revanced-cli*.jar")
    tagName="v$patchver"

    # Make sure release with APK
    if [ ! -f "$apkFilePath" ]; then
        exit
    fi

    existingRelease=$(req - --header="$authorization" "$apiReleases/tags/$tagName" 2>/dev/null)

    # Add more assets release with same tag name
    if [ -n "$existingRelease" ]; then
        existingReleaseId=$(echo "$existingRelease" | jq -r ".id")
        uploadUrlApk="$uploadRelease/$existingReleaseId/assets?name=$apkFileName"

        # Delete assest release if same name upload 
        for existingAsset in $(echo "$existingRelease" | jq -r '.assets[].name'); do
            [ "$existingAsset" == "$apkFileName" ] && \
                assetId=$(echo "$existingRelease" | jq -r '.assets[] | select(.name == "'"$apkFileName"'") | .id') && \
                req - --header="$authorization" --method=DELETE "$apiReleases/assets/$assetId" 2>/dev/null
        done
    else
        # Make tag name
        create_body_release 
        newRelease=$(req - --header="$authorization" --post-data="$releaseData" "$apiReleases")
        releaseId=$(echo "$newRelease" | jq -r ".id")
        uploadUrlApk="$uploadRelease/$releaseId/assets?name=$apkFileName"
    fi

    # Upload file to Release 
    req - &>/dev/null --header="$authorization" --post-file="$apkFilePath" "$uploadUrlApk"
}
