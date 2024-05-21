#!/usr/bin/perl
package github_downloader;

use strict;
use warnings;
use JSON;
use Exporter 'import';

our @EXPORT_OK = qw(download_resources);

sub req {
    my ($url, $output) = @_;
    $output ||= '-';
    
    my $command = "wget -nv -O $output \"$url\"";
    my $content = `$command`;
    die "Failed to execute $command: $?" if $? != 0;
    return $content;
}

sub download_resources {
    my @repos = qw(revanced-patches revanced-cli revanced-integrations);

    foreach my $repo (@repos) {
        my $github_api_url = "https://api.github.com/repos/revanced/$repo/releases/latest";

        my $content = req($github_api_url);
        my $release_data = decode_json($content);
        
        for my $asset (@{$release_data->{assets}}) {
            my $asset_name = $asset->{name};
            
            # Skip files with .asc extension
            next if $asset_name =~ /\.asc$/;

            my $download_url = $asset->{browser_download_url};
            req($download_url, $asset_name);
        }
    }
}

1;
