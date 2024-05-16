#!/usr/bin/perl
use strict;
use warnings;

# Ensure version is provided
my $version = shift  or die "Usage: $0 <version>\n";

# Read all input into an array
my @lines = <STDIN>;

# Buffer to store relevant lines
my @buffer;

# Function to filter lines based on pattern and buffer size
sub filter_lines {
    my ($pattern, $size, $buffer_ref) = @_;
    my @temp_buffer;
    for my $line (@$buffer_ref) {
        push @temp_buffer, $line;
        if ($line =~ /$pattern/) {
            @$buffer_ref = @temp_buffer[-$size..-1] if @temp_buffer > $size;
            return;
        }
    }
}

# Filter by version
filter_lines(qr/>\s*$version\s*<\/span>/, 5, \@lines);

# Extract the URL
my $url;
my $i = 0;
for my $line (@lines) {
    if ($line =~ /.*data-url="(.*[^"]*)".*/ && ++$i == 1) {
        $url = "$1";
        $url =~ s/\/download\//\/post-download\//g;
        last;
    }
}

print "$url\n" if $url;
