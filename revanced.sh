#!/bin/bash
source ./etc/utils.sh

# Main script 
accessToken=$GITHUB_TOKEN
repoName=$GITHUB_REPOSITORY_NAME
repoOwner=$GITHUB_REPOSITORY_OWNER

# I prefer APKmirror but some time It's failure. So I use Uptodown. APKmirror scraper still works fine

# Perform download_repository_assets
download_resources

# Patch YouTube 
uptodown "youtube" \
         "com.google.android.youtube"
apply_patches "youtube"
sign_patched_apk "youtube"
create_github_release "youtube"

# Patch YouTube Music 
uptodown "youtube-music" \
         "com.google.android.apps.youtube.music" 
apply_patches "youtube-music"
sign_patched_apk "youtube-music"
create_github_release "youtube-music"

# You can add other apps here 
