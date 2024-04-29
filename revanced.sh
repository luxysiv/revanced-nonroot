#!/bin/bash
source ./etc/utils.sh

# Main script 

# Perform download_repository_assets
download_resources

# Patch YouTube 
apkmirror "google-inc" \
          "youtube" \
          "com.google.android.youtube"
apply_patches "youtube"
sign_patched_apk "youtube"
create_github_release "youtube"

# Patch YouTube Music 
apkmirror "google-inc" \
          "youtube-music" \
          "com.google.android.apps.youtube.music" \
          "arm64-v8a"
apply_patches "youtube-music"
sign_patched_apk "youtube-music"
create_github_release "youtube-music"

# You can add other apps here 
