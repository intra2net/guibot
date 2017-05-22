#!/bin/sh

# produce rst files for the modules
sphinx-apidoc -e -f -o . ../../guibender
# produce HTML documentation from the rst files
make html
