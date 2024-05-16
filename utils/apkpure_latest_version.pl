#!/usr/bin/perl
use strict;
use warnings;

my $i = 0;

while (<>) {
    if (/data-dt-version="(.*?)"/ && ++$i == 1) {
        my $version = $1;
        print $version;
    }
}
