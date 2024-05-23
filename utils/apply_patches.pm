#!/usr/bin/perl
package apply_patches;

use strict;
use warnings;
use File::Glob ':glob';
use File::Find;
use Cwd;
use Env;
use File::Spec;
use Exporter 'import';

our @EXPORT_OK = qw(apply_patches);

# Subroutine to get environment variables
sub get_env_var {
    my ($var) = @_;
    my $value = $ENV{$var} or die "$var not set in environment";
    return $value;
}

# Subroutine to process patches
sub process_patches {
    my ($name) = @_;

    # Get the name of the file containing patches
    my $filename = "./etc/${name}-patches.txt";

    # Check if the file exists and is readable
    unless (-e $filename && -r $filename) {
        return ();
    }

    # Read patches from the file
    open(my $fh, '<', $filename) or die "Cannot open file: $filename";

    my @lines = <$fh>;
    close $fh;

    chomp @lines;

    # Initialize includePatches and excludePatches arrays
    my @includePatches;
    my @excludePatches;

    # Process patches
    foreach my $line (@lines) {
        next unless $line =~ /^[+\-]/;  # Skip lines that don't start with + or -

        # Remove the + or - sign and surrounding whitespace to get the patch name
        my $patch_name = $line;
        $patch_name =~ s/^[+\-]\s*//;

        # Add patch name to the corresponding array
        if ($line =~ /^\+/) {
            push @includePatches, $patch_name;
        } elsif ($line =~ /^-/) {
            push @excludePatches, $patch_name;
        }
    }

    my @allPatches;
    foreach my $patch (@includePatches) {
        push @allPatches, "--include \"$patch\"";
    }
    foreach my $patch (@excludePatches) {
        push @allPatches, "--exclude \"$patch\"";
    }

    return @allPatches;
}

# Subroutine to find files using wildcard patterns
sub find_files {
    my ($pattern) = @_;
    my ($file) = bsd_glob($pattern);
    return $file;
}

# Subroutine to construct and execute a command
sub execute_cmd {
    my ($cmd) = @_;
    system($cmd) == 0 or die "Failed to execute: $cmd";
}

# Subroutine to find apksigner
sub find_apksigner {
    my $android_sdk_root = shift;
    my $apksigner;
    find(sub {
        if ($_ eq 'apksigner' && -f $_) {
            $apksigner = $File::Find::name;
        }
    }, File::Spec->catdir($android_sdk_root, 'build-tools'));
    die "apksigner not found" unless $apksigner;
    return $apksigner;
}

# Subroutine to remove x86 and x86_64 libraries from the APK using the zip command
sub remove_architecture_libs {
    my ($apk) = @_;
    my $zip_cmd = "zip --delete $apk 'lib/x86/*' 'lib/x86_64/*' > /dev/null 2>&1";
    system($zip_cmd);

    unless ($? == 0) {}
}

# Main logic
sub apply_patches {
    # Get command-line arguments
    my ($name) = @_;

    # Get environment variables
    my $version = get_env_var('VERSION');
    my $android_sdk_root = get_env_var('ANDROID_SDK_ROOT');

    # Process patches
    my @allPatches = process_patches($name);

    # Find necessary files
    my $cli = find_files("revanced-cli*.jar");
    my $integrations = find_files("revanced-integrations*.apk");
    my $patches = find_files("revanced-patches*.jar");

    # Construct the APK filename
    my $apk = "$name-v$version.apk";

    # Remove x86 and x86_64 libraries from the APK
    remove_architecture_libs($apk);

    # Construct and execute patch command
    my $patch_cmd = "java -jar $cli patch "
                  . "--merge $integrations "
                  . "--patch-bundle $patches "
                  . "--out patched-$name-v$version.apk "
                  . join(" ", @allPatches) . " "
                  . $apk;
    execute_cmd($patch_cmd);

    # Remove the original APK
    unlink $apk or warn "Could not unlink $apk: $!";

    # Find apksigner tool
    my $apksigner = find_apksigner($android_sdk_root);

    # Construct and execute sign command
    my $input_apk = "patched-$name-v$version.apk";
    my $output_apk = "$name-revanced-v$version.apk";
    my $sign_cmd = "$apksigner sign --verbose "
                 . "--ks ./etc/public.jks "
                 . "--ks-key-alias public "
                 . "--ks-pass pass:public "
                 . "--key-pass pass:public "
                 . "--in $input_apk "
                 . "--out $output_apk";
    execute_cmd($sign_cmd);

    # Remove the patched APK file
    unlink $input_apk or warn "Could not unlink $input_apk: $!";

    # Remove environment version
    undef $ENV{VERSION};
}

1;
