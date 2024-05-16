#!/usr/bin/perl
use strict;
use warnings;

while (<>) {
    if (/.*href="(.*key=[^"]*)".*/) {
        my $url = $1;
        print "https://www.apkmirror.com$url\n";
    }
}
