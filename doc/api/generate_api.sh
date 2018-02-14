#!/bin/bash

# produce rst files for the modules
sphinx-apidoc -e -f -o . ../../guibot || die "No rst files could be generated"

# produce HTML documentation from the rst files
make html

# move all rst files to source directory to integrate with RTD
mkdir source || die "No source directory to move rst files to"
mv *.rst source
