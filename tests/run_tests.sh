#!/bin/sh

set -e

readonly libpath="${LIBPATH:-../guibot}"
readonly coverage="${COVERAGE:-coverage3}"

$coverage run --source="$libpath" -m unittest discover -v -s ../tests/
$coverage report -m
