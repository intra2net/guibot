#!/bin/sh

set -e

readonly libpath="${LIBPATH:-../guibot}"
readonly coverage="${COVERAGE:-coverage3}"

$coverage run --source="$libpath" -m unittest discover -v -s ../tests/
# use -i to ignore errors from pythong cache files and other traced dependencies
$coverage report -m -i
