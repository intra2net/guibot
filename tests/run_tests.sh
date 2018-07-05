#!/bin/sh

readonly libpath="${LIBPATH:-../guibot}"
readonly coverage="${COVERAGE:-coverage3}"

$coverage run --source="$libpath" -m unittest discover -v
$coverage report -m
