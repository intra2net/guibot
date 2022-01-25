#!/bin/sh

set -e

readonly libpath="${LIBPATH:-../guibot}"
readonly coverage="${COVERAGE:-coverage3}"
readonly submit="${SUBMIT:-0}"

$coverage run --source="$libpath" -m unittest discover -v -s ../tests/
# use -i to ignore errors from pythong cache files and other traced dependencies
$coverage report -m -i
if [[ $submit == 1 ]]; then codecov; fi
