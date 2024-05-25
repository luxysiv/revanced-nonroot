#!/usr/bin/perl
package uptodown;

use strict;
use warnings;
use JSON;
use Env;
use LWP::UserAgent;
use HTTP::Request;
use HTTP::Headers;
use POSIX qw(strftime);
use Exporter 'import';

our @EXPORT_OK = qw(uptodown);

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
        my $final_url = $response->base; # Lấy URL phản hồi cuối cùng
        if ($output ne '-') {
            open(my $fh, '>', $output) or die "Could not open file '$output' $!";
            print $fh $response->decoded_content;
            close($fh);
            print "$timestamp URL:$final_url [$size/$size] -> \"$output\" [1]\n";
        } else {
            print "$timestamp URL:$final_url [$size/$size] -> \"-\" [1]\n";
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
        if ($line =~ /<div\s+data-url/) {
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
    my $version = (sort {$b cmp $a} keys %versions)[0];
    return $version;
}

sub uptodown {
    my ($name, $package) = @_;

    my $version = $ENV{VERSION};

    if (!$version) {
        if (my $supported_version = get_supported_version($package)) {
            $version = $supported_version;
            $ENV{VERSION} = $version;
        } else {
            my $page = "https://$name.en.uptodown.com/android/versions";
            my $page_content = req($page);

            my @lines = split /\n/, $page_content;

            for my $line (@lines) {
                if ($line =~ /.*class="version">(.*?)<\/div>/) {
                    $version = "$1";
                    last;
                }
            }
            $ENV{VERSION} = $version;
        }
    }

    my $url = "https://$name.en.uptodown.com/android/versions";
    my $download_page_content = req($url);

    my @lines = split /\n/, $download_page_content;

    filter_lines(qr/>\s*$version\s*<\/span>/, \@lines);
    
    my $download_page_url;
    for my $line (@lines) {
        if ($line =~ /.*data-url="(.*[^"]*)"/) {
            $download_page_url = "$1";
            $download_page_url =~ s/\/download\//\/post-download\//g;
            last;
        }
    }

    my $final_page_content = req($download_page_url);
    
    @lines = split /\n/, $final_page_content;
    
    my $final_url;
    for my $line (@lines) {
        if ($line =~ /.*"post-download" data-url="([^"]*)"/) {
            $final_url = "https://dw.uptodown.com/dwn/$1";
            last;
        }
    }
    
    my $apk_filename = "$name-v$version.apk";
    req($final_url, $apk_filename);
}

1;
