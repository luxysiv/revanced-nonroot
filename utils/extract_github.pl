#!/usr/bin/perl
use strict;
use warnings;
use JSON;

# Read the JSON data from standard input
my $json_text = do { local $/; <STDIN> };

# Decode the JSON data
my $data = decode_json($json_text);

# Extract download links and assets name
foreach my $asset (@{$data->{assets}}) {
    my $name = $asset->{name};
    if ($name !~ /\.asc$/) {
        my $url = $asset->{browser_download_url};
        print "$url $name\n";
    }
}
