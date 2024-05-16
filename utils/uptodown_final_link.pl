#!/usr/bin/perl
use strict;
use warnings;

while (<>) {
    if (/.*"post-download" data-url="([^"]*)".*/) {
        my $url = $1;
        print "https://dw.uptodown.com/dwn/$url\n";
    }
}
