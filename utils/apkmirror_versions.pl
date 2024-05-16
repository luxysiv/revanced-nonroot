#!/usr/bin/perl
use strict;
use warnings;

# Initialize the count variable
my $count = 0;

# Process each line of input
while (<>) {
    # Check if the line matches the pattern for version strings
    if (/fontBlack(.*?)>(.*?)<\/a>/) {
        $count++;
        # Print the version string if the count is <= 20 and it is not an alpha or beta version
        print "$2\n" if $count <= 20 && $_ !~ /alpha|beta/i;
    }
}
