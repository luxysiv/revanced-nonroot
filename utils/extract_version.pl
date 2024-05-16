#!/usr/bin/perl
use strict;
use warnings;

my $pattern = shift or die "Usage: $0 'filename_pattern'\n";

my @files = glob($pattern);
die "No files matched the pattern '$pattern'\n" unless @files;

my $file = $files[0];

while ($file =~ /(\d+(\.\d+)+)/g) {
    print "$1\n";
}
