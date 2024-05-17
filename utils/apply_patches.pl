#!/usr/bin/perl
use strict;
use warnings;
use File::Glob ':glob';

# Get the arguments
my ($name, $version) = @ARGV;

# Process patches and store in an array
my @optionsPatches = `perl utils/process_patches.pl $name`;
chomp @optionsPatches;

# Find the necessary files using wildcard
my ($cli_jar) = bsd_glob("revanced-cli*.jar");
my ($integrations_apk) = bsd_glob("revanced-integrations*.apk");
my ($patches_jar) = bsd_glob("revanced-patches*.jar");

# Construct the command
my $cmd = "java -jar $cli_jar patch "
        . "--merge $integrations_apk "
        . "--patch-bundle $patches_jar "
        . "--out patched-$name-v$version.apk "
        . "@optionsPatches "
        . "$name-v$version.apk";

# Execute the command
system($cmd) == 0 or die "Failed to execute: $cmd";

# Remove the original APK
unlink "$name-v$version.apk" or warn "Could not unlink $name-v$version.apk: $!";

# Unset the optionsPatches array
undef @optionsPatches;

# Sign patched APK
system("perl utils/sign_apk.pl $name $version") == 0 or die "Failed to execute sign_apk.pl";
