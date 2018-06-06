#!/bin/sh

readonly libpath="${LIBPATH:-../guibot}"

python3-coverage run --source="$libpath" -m unittest discover -v
python3-coverage report -m
