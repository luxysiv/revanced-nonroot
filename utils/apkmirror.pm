#!/usr/bin/perl
package apkmirror;

use strict;
use warnings;
use JSON;
use Env;
use Exporter 'import';
use LWP::UserAgent;
use HTTP::Request;
use HTTP::Headers;
use POSIX qw(strftime);

our @EXPORT_OK = qw(apkmirror);

sub req {
    my ($url, $output) = @_;
    $output ||= '-';

    my $ua = LWP::UserAgent->new(
        agent => 'Mozilla/5.0 (Android 13; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0',
        timeout => 30,
    );

    my $headers = HTTP::Headers->new(
        'Content-Type' => 'application/octet-stream',
        'Accept-Language' => 'en-US,en;q=0.9',
        'Connection' => 'keep-alive',
        'Upgrade-Insecure-Requests' => '1',
        'Cache-Control' => 'max-age=0',
        'Accept' => 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
    );

    my $request = HTTP::Request->new(GET => $url, $headers);
    my $response = $ua->request($request);

    my $timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime);
    if ($response->is_success) {
        my $size = length($response->decoded_content);
        if ($output ne '-') {
            open(my $fh, '>', $output) or die "Could not open file '$output' $!";
            print $fh $response->decoded_content;
            close($fh);
            print "$timestamp URL:$url [$size] -> \"$output\" \n";
        } else {
            print "$timestamp URL:$url [$size] -> \"-\" \n";
        }
        return $response->decoded_content;
    } else {
        die "HTTP GET error: " . $response->status_line;
    }
}

sub filter_lines {
    my ($pattern, $buffer_ref) = @_;
    my @result_buffer = ();
    my $last_target_index = -1;
    my $index = 0;
    my $collecting = 0;
    my @temp_buffer = ();

    for my $line (@$buffer_ref) {
        if ($line =~ /<a\s+class="accent_color"/) {
            $last_target_index = $index;
            $collecting = 1;
            @temp_buffer = ();
        }

        if ($collecting) {
            push(@temp_buffer, $line);
        }

        if ($line =~ /$pattern/) {
            if ($last_target_index != -1 && $collecting) {
                push @result_buffer, @temp_buffer;
                $collecting = 0;
            }
        }

        $index++;
    }

    @$buffer_ref = @result_buffer;
}

sub get_supported_version {
    my $pkg_name = shift;
    return unless defined $pkg_name;
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
    my $version = (sort { $b cmp $a } keys %versions)[0];
    return $version;
}

sub apkmirror {
    my ($org, $name, $package, $arch, $dpi) = @_;
    $dpi ||= 'nodpi';

    my $version = $ENV{VERSION};

    if (!$version) {
        if (my $supported_version = get_supported_version($package)) {
            $version = $supported_version;
            $ENV{VERSION} = $version;
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
            $ENV{VERSION} = $version;
        }
    }

    my $url = "https://www.apkmirror.com/apk/$org/$name/$name-" . (join '-', split /\./, $version) . "-release";
    my $apk_page_content = req($url);

    my @lines = split /\n/, $apk_page_content;

    if (defined $dpi) {
        filter_lines(qr/>\s*$dpi\s*</, \@lines);
    }
    if (defined $arch) {
        filter_lines(qr/>\s*$arch\s*</, \@lines);
    }
    filter_lines(qr/>\s*APK\s*</, \@lines);

    my $download_page_url;
    for my $line (@lines) {
        if ($line =~ /.*href="(.*[^"]*\/)"/) {
            $download_page_url = $1;
            unless ($download_page_url =~ /^https:\/\/www\.apkmirror\.com/) {
                $download_page_url = "https://www.apkmirror.com$1";
            }
            last;
        }
    }

    my $download_page_content = req($download_page_url);

    @lines = split /\n/, $download_page_content;

    my $dl_apk_url;
    for my $line (@lines) {
        if ($line =~ /href="(.*key=[^"]*)"/) {
            $dl_apk_url = $1;
            unless ($dl_apk_url =~ /^https:\/\/www\.apkmirror\.com/) {
                $dl_apk_url = "https://www.apkmirror.com$1";
            }
            last;
        }
    }

    my $dl_apk_content = req($dl_apk_url);

    @lines = split /\n/, $dl_apk_content;

    my $final_url;
    for my $line (@lines) {
        if ($line =~ /href="(.*key=[^"]*)"/) {
            $final_url = $1;
            unless ($final_url =~ /^https:\/\/www\.apkmirror\.com/) {
                $final_url = "https://www.apkmirror.com$1";
            }
            $final_url =~ s/amp;//g;
            unless ($final_url =~ /&forcebaseapk=true$/) {
                $final_url .= '&forcebaseapk=true';
            }
            last;
        }
    }

    my $apk_filename = "$name-v$version.apk";
    req($final_url, $apk_filename);
}

1;
