#!/usr/bin/perl
use strict;
use warnings;
use lib;

use apkpure qw(apkpure);
use uptodown qw(uptodown);
use apkmirror qw(apkmirror);
use apply_patches qw(apply_patches);
use github_release qw(github_release);
use github_downloader qw(download_resources);


# Main

# Download Github releases assets 
download_resources();

# Patch YouTube
apkmirror(
    "google-inc", 
    "youtube", 
    "com.google.android.youtube"
);
apply_patches("youtube");
github_release("youtube");

# Patch YouTube Music 
apkmirror(
    "google-inc", 
    "youtube-music", 
    "com.google.android.apps.youtube.music", 
    "arm64-v8a"
);
apply_patches("youtube-music");
github_release("youtube-music");

# You can add other apps here
