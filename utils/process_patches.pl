#!/usr/bin/perl

use strict;
use warnings;

# Function to process patches
sub process_patches {
    my ($name) = @_;
    
    my $filename = "./etc/${name}-patches.txt";
    
    # Read patches from the file
    open(my $fh, '<', $filename) or die "Cannot open file '$filename': $!";
    
    my @lines = <$fh>;
    close $fh;
    
    chomp @lines;
    
    # Initialize includePatches and excludePatches arrays
    my @includePatches;
    my @excludePatches;
    
    # Process patches
    foreach my $line (@lines) {
        next unless $line =~ /^[+\-]/;  # Skip lines that don't start with + or -
        
        # Remove the + or - sign and surrounding whitespace to get the patch name
        my $patch_name = $line;
        $patch_name =~ s/^[+\-]\s*//;
        
        # Add patch name to the corresponding array
        if ($line =~ /^\+/) {
            push @includePatches, $patch_name;
        } elsif ($line =~ /^-/) {
            push @excludePatches, $patch_name;
        }
    }
    
    return (\@includePatches, \@excludePatches);
}

# Get the argument from the command line
my $name = shift @ARGV or die "Please provide the file name (excluding '-patches.txt') as a command line argument.\n";

# Call process_patches function with the command line argument
my ($include_ref, $exclude_ref) = process_patches($name);

# Access the arrays to use the results
my @includePatches = @{$include_ref};
my @excludePatches = @{$exclude_ref};

# Print the patches to be included and excluded
foreach my $patch (@includePatches) {
    print "--include \"$patch\"\n";
}
foreach my $patch (@excludePatches) {
    print "--exclude \"$patch\"\n";
}
