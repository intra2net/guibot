#!/bin/bash
# Run this script when producing new documentation to submit to RTD.

set -e

# produce rst files for the modules
sphinx-apidoc -e -f -o . ../../guibot || die "No rst files could be generated"

# move all rst files to source directory to integrate with RTD
rm -fr source index.rst
mkdir source || die "No source directory to move rst files to"
mv *.rst source

# produce HTML documentation from the rst files
make html

# use README as index page for RTD (needs MD-RST compatibility)
pandoc ../../README.md --from markdown --to rst -s -o index.rst
