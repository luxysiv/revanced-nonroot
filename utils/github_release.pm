#!/usr/bin/perl
package github_release;

use strict;
use warnings;
use JSON;
use File::Basename;
use File::Glob ':glob';

use Exporter 'import';

our @EXPORT_OK = qw(github_release);

# Function to make HTTP requests
sub req {
    my ($url, $method, $data, $is_file) = @_;
    my $token = $ENV{'GITHUB_TOKEN'};

    my $cmd = "curl -s -H 'Authorization: token $token' -H 'Content-Type: application/json'";
    $cmd .= " -X $method" if $method;
    if ($method eq 'POST' && defined $data) {
        if ($is_file) {
            $cmd .= " --data-binary \@$data";
        } else {
            $cmd .= " --data '\@$data'";
        }
    }
    $cmd .= " $url";

    my $response = `$cmd`;
    return $response;
}


# Function to create the body of the release
sub create_body_release {
    my ($patchver, $integrationsver, $cliver) = @_;
    my $body = <<"EOF";
# Release Notes

## Build Tools:
- **ReVanced Patches:** v$patchver
- **ReVanced Integrations:** v$integrationsver
- **ReVanced CLI:** v$cliver

## Note:
**ReVanced GmsCore** is **necessary** to work. 
- Please **download** it from [HERE](https://github.com/revanced/gmscore/releases/latest).
EOF

    my %release_data = (
        tag_name         => "v$patchver",
        target_commitish => "main",
        name             => "Revanced v$patchver",
        body             => $body
    );

    my $json_release_data = encode_json(\%release_data);
    return $json_release_data;
}

# Function to find a file matching a pattern
sub find_file {
    my ($pattern) = @_;
    my @files = bsd_glob($pattern);

    return @files ? $files[0] : undef;
}

# Function to extract version from filename
sub extract_version {
    my ($pattern) = @_;
    my $file = find_file($pattern);
    if ($file) {
        if ($file =~ /(\d+\.\d+\.\d+)/) {
            return $1;
        }
    }
    return undef;
}

# Function to create or update a GitHub release and upload the APK
sub github_release {
    my ($name) = @_;
    my $repo = $ENV{'GITHUB_REPOSITORY'};
    my $api_releases = "https://api.github.com/repos/$repo/releases";
    my $upload_releases = "https://uploads.github.com/repos/$repo/releases";
    
    # Find the APK file and determine versions
    my $pattern = "./$name-revanced*.apk";
    my $apk_file_path = find_file($pattern);
    
    if (!$apk_file_path) {
        exit;
    }

    my $apk_file_name = basename($apk_file_path);
    my $patchver = extract_version("revanced-patches*.jar");
    my $integrationsver = extract_version("revanced-integrations*.apk");
    my $cliver = extract_version("revanced-cli*.jar");
    my $tag_name = "v$patchver";

    # Check if a release with the tag already exists
    my $existing_release = req("$api_releases/tags/$tag_name", 'GET');
    my $existing_release_json = decode_json($existing_release) if $existing_release;

    my $upload_url_apk;

    if ($existing_release && $existing_release_json->{id}) {
        my $existing_release_id = $existing_release_json->{id};
        $upload_url_apk = "$upload_releases/$existing_release_id/assets?name=$apk_file_name";

        # Delete existing assets with the same name
        foreach my $existing_asset (@{$existing_release_json->{assets}}) {
            if ($existing_asset->{name} eq $apk_file_name) {
                my $asset_id = $existing_asset->{id};
                req("$api_releases/assets/$asset_id", 'DELETE');
            }
        }
    } else {
        # Create a new release if it doesn't exist
        my $release_data = create_body_release($patchver, $integrationsver, $cliver);
        open my $fh, '>', 'release_data.json' or die $!;
        print $fh $release_data;
        close $fh;
        my $new_release = req($api_releases, 'POST', 'release_data.json');
        my $new_release_json = decode_json($new_release);
        my $release_id = $new_release_json->{id};
        $upload_url_apk = "$upload_releases/$release_id/assets?name=$apk_file_name";
    }

    # Upload the APK file
    my $upload_response = req($upload_url_apk, 'POST', $apk_file_path);
}

1;
