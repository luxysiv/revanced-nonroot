#!/usr/bin/perl
use strict;
use warnings;
use JSON;

# Check for the required argument
my $pkg_name = shift or die "Usage: $0 <package>\n";

# Read the JSON data from standard input
my $json_text = do { local $/; <STDIN> };

# Decode the JSON data
my $data = decode_json($json_text);

# Initialize an empty set to hold versions
my %versions;

# Iterate over each patch in the JSON data
foreach my $patch (@{$data}) {
    my $compatible_packages = $patch->{'compatiblePackages'};
    
    # Check if compatiblePackages is a non-empty list
    if ($compatible_packages && ref($compatible_packages) eq 'ARRAY') {
        # Iterate over each package in compatiblePackages
        foreach my $package (@$compatible_packages) {
            # Check if package name and versions list is not empty
            if (
                $package->{'name'} eq $pkg_name &&
                $package->{'versions'} && ref($package->{'versions'}) eq 'ARRAY' && @{$package->{'versions'}}
            ) {
                # Add versions to the set
                foreach my $version (@{$package->{'versions'}}) {
                    $versions{$version} = 1;
                }
            }
        }
    }
}

# Sort versions in reverse order and get the latest version
my $latest_version = (sort {$b cmp $a} keys %versions)[0];

# Print the latest version
if ($latest_version) {
    print "$latest_version\n";
}
