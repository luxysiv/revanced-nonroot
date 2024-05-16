#!/usr/bin/perl
use strict;
use warnings;

# Get the package name from the command line argument
my $package = shift or die "Usage: $0 <package_name>\n";

# Counter for the number of matches
my $i = 0;

# Read input line by line
while (<>) {
    # Pattern match to extract the URL containing the package name
    if (/.*href="(.*\/APK\/$package[^"]*)".*/ && ++$i == 1) {
        my $url = $1;
        print "$url\n";
    }
}
