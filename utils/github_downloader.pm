#!/usr/bin/perl
package github_downloader;

use strict;
use warnings;
use JSON;
use File::Temp qw(tempfile);
use Exporter 'import';

our @EXPORT_OK = qw(download_resources);


sub req {
    my ($url, $output) = @_;
    
    my $command = "wget -nv -O \"$output\" \"$url\"";
    system($command) == 0
        or die "Failed to execute $command: $?";
}

sub download_resources {
    my @repos = qw(revanced-patches revanced-cli revanced-integrations);

    foreach my $repo (@repos) {
        my $github_api_url = "https://api.github.com/repos/revanced/$repo/releases/latest";
        my ($fh, $tempfile) = tempfile();

        req($github_api_url, $tempfile);

        open my $json_fh, '<', $tempfile or die "Could not open temporary file: $!";
        my $content = do { local $/; <$json_fh> };
        close $json_fh;

        my $release_data = decode_json($content);
        for my $asset (@{$release_data->{assets}}) {
            my $asset_name = $asset->{name};
            
            # Skip files with .asc extension
            next if $asset_name =~ /\.asc$/;

            my $download_url = $asset->{browser_download_url};
            req($download_url, $asset_name);
        }

        unlink $tempfile; # Remove the temporary JSON file
    }
}

1;
