#!/bin/bash

# produce rst files for the modules
sphinx-apidoc -e -f -o . ../../guibot || die "No rst files could be generated"

# move all rst files to source directory to integrate with RTD
mv README.rst README.rst.bak
rm -fr source README.rst
mkdir source || die "No source directory to move rst files to"
mv *.rst source

# produce HTML documentation from the rst files
make html

# use README as index page for RTD (needs MD-RST compatibility)
# pandoc ../../README.md --from markdown --to rst -s -o README.rst
mv README.rst.bak README.rst
