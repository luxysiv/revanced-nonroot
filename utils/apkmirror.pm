#!/usr/bin/perl
package apkmirror;

use strict;
use warnings;
use JSON;
use Env;
use Exporter 'import';

our @EXPORT_OK = qw(apkmirror);

sub req {
    my ($url, $output) = @_;
    $output ||= '-';
    my $headers = join(' ',
        '--header="User-Agent: Mozilla/5.0 (Android 13; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0"',
        '--header="Content-Type: application/octet-stream"',
        '--header="Accept-Language: en-US,en;q=0.9"',
        '--header="Connection: keep-alive"',
        '--header="Upgrade-Insecure-Requests: 1"',
        '--header="Cache-Control: max-age=0"',
        '--header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"'
    );

    my $command = "wget $headers --keep-session-cookies --timeout=30 -nv -O $output \"$url\"";
    my $content = `$command`;
    return $content;
}

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

sub get_supported_version {
    my $pkg_name = shift;
    my $filename = 'patches.json';
    
    open(my $fh, '<', $filename) or die "Could not open file '$filename' $!";
    local $/; 
    my $json_text = <$fh>;
    close($fh);

    my $data = decode_json($json_text);
    my %versions;

    foreach my $patch (@{$data}) {
        my $compatible_packages = $patch->{'compatiblePackages'};
    
        if ($compatible_packages && ref($compatible_packages) eq 'ARRAY') {
            foreach my $package (@$compatible_packages) {
                if (
                    $package->{'name'} eq $pkg_name &&
                    $package->{'versions'} && ref($package->{'versions'}) eq 'ARRAY' && @{$package->{'versions'}}
                ) {
                    foreach my $version (@{$package->{'versions'}}) {
                        $versions{$version} = 1;
                    }
                }
            }
        }
    }
    my $version = (sort {$b cmp $a} keys %versions)[0];
    return $version;
}

sub apkmirror {
    my ($org, $name, $package, $arch, $dpi) = @_;
    $dpi ||= 'nodpi';
    $arch ||= 'universal';

    my $version;

    if (my $supported_version = get_supported_version($package)) {
        $version = $supported_version;
    } else {
        my $page = "https://www.apkmirror.com/uploads/?appcategory=$name";
        my $page_content = req($page);

        my @lines = split /\n/, $page_content;

        my $count = 0;
        my @versions;
        for my $line (@lines) {
            if ($line =~ /fontBlack(.*?)>(.*?)<\/a>/) {
                my $version = $2;
                push @versions, $version if $count <= 20 && $line !~ /alpha|beta/i;
                $count++;
            }
        }

        @versions = map { s/^\D+//; $_ } @versions;
        @versions = sort { version->parse($b) <=> version->parse($a) } @versions;
        $version = $versions[0];
    }

    # Export version to environment
    $ENV{VERSION} = $version;

    my $url = "https://www.apkmirror.com/apk/$org/$name/$name-" . (join '-', split /\./, $version) . "-release";
    my $apk_page_content = req($url);

    my @lines = split /\n/, $apk_page_content;

    filter_lines(qr/>\s*$dpi\s*</, 16, \@lines);
    filter_lines(qr/>\s*$arch\s*</, 14, \@lines);
    filter_lines(qr/>\s*APK\s*</, 6, \@lines);

    my $download_page_url;
    for my $line (@lines) {
        if ($line =~ /.*href="(.*[^"]*\/)"/) {
            $download_page_url = "https://www.apkmirror.com$1";
            last;
        }
    }
    
    my $download_page_content = req($download_page_url);

    @lines = split /\n/, $download_page_content;

    my $dl_apk_url;
    for my $line (@lines) {
        if ($line =~ /href="(.*key=[^"]*)"/) {
            $dl_apk_url = "https://www.apkmirror.com$1";
            last;
        }
    }
    
    my $apk_content = req($dl_apk_url);

    my $final_url;
    if ($apk_content =~ /href="(.*key=[^"]*)"/) {
        $final_url = "https://www.apkmirror.com$1";
        $final_url =~ s/amp;//g;
    }

    my $apk_filename = "$name-v$version.apk";
    req($final_url, $apk_filename);
}

1;
