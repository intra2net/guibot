#!/bin/sh

set -e

readonly libpath="${LIBPATH:-../guibot}"
readonly coverage="${COVERAGE:-coverage3}"
readonly submit="${SUBMIT:-0}"

$coverage run --source="$libpath" -m unittest discover -v -s ../tests/
# use -i to ignore errors from pythong cache files and other traced dependencies
$coverage report -m -i
# codecov is poorly documented and even in verbose mode and various directory changes
# won't tell us where it runs the xml command and why it ends up not finding it
$coverage xml -i
if [[ $submit == 1 ]]; then codecov; fi
