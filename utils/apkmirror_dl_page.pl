#!/usr/bin/perl
use strict;
use warnings;

# Ensure dpi and arch are provided
my $dpi = shift or die "Usage: $0 <dpi> <arch>\n";
my $arch = shift  or die "Usage: $0 <dpi> <arch>\n";

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

# Step 1: Filter by dpi
filter_lines(qr/>\s*$dpi\s*</, 16, \@lines);

# Step 2: Filter by arch
filter_lines(qr/>\s*$arch\s*</, 14, \@lines);

# Step 3: Filter by APK
filter_lines(qr/>\s*APK\s*</, 6, \@lines);

# Extract the URL
my $url;
my $i = 0;
for my $line (@lines) {
    if ($line =~ /.*href="(.*apk-[^"]*)".*/ && ++$i == 1) {
        $url = "https://www.apkmirror.com$1";
        last;
    }
}

print "$url\n" if $url;
