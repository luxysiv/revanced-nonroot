#!/usr/bin/perl
use strict;
use warnings;

while (<>) {
    if (/class="version">(.*?)<\/div>/) {
        my $version = $1;
        print $version;
    }
}
