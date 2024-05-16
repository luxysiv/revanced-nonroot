#!/usr/bin/perl
use strict;
use warnings;
use version;

# Subroutine to compare two versions
sub compare_versions {
    my ($a, $b) = @_;
    return version->parse($a) <=> version->parse($b);
}

# Hash to keep track of seen versions
my %seen;
# Variable to keep track of the largest version
my $max_version;

# Read from STDIN
while (<>) {
    # Extract version-like patterns
    while (/\b(\d+(\.\d+)+(?:\-\w+)?(?:\.\d+)?(?:\.\w+)?)\b/gi) {
        my $version = $1;
        next if $seen{$version}++;
        $max_version = $version if not defined $max_version or compare_versions($version, $max_version) > 0;
    }
}

# Print the largest version if found
if ($max_version) {
    print "$max_version\n";
}
