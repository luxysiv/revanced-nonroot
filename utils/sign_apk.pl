#!/usr/bin/perl
use strict;
use warnings;
use File::Find;
use Cwd;
use File::Spec;

sub sign_patched_apk {
    my ($name, $version) = @_;

    # Locate the latest 'apksigner' tool in the Android SDK build-tools directory
    my $android_sdk_root = $ENV{'ANDROID_SDK_ROOT'};
    die "ANDROID_SDK_ROOT is not set" unless $android_sdk_root;
    
    my $apksigner;
    find(sub {
        if ($_ eq 'apksigner' && -f $_) {
            $apksigner = $File::Find::name;
        }
    }, File::Spec->catdir($android_sdk_root, 'build-tools'));

    die "apksigner not found" unless $apksigner;
    
    # Execute the apksigner command
    my $input_apk = "patched-$name-v$version.apk";
    my $output_apk = "$name-revanced-v$version.apk";
    
    my $cmd = "$apksigner sign --verbose "
            . "--ks ./etc/public.jks "
            . "--ks-key-alias public "
            . "--ks-pass pass:public "
            . "--key-pass pass:public "
            . "--in $input_apk "
            . "--out $output_apk";

    system($cmd) == 0 or die "Failed to sign APK: $!";
    
    # Remove the original patched APK file
    unlink $input_apk or warn "Could not unlink $input_apk: $!";
}

# Call the function with arguments
my ($name, $version) = @ARGV;
die "Usage: $0 name version\n" unless $name && $version;
sign_patched_apk($name, $version);
