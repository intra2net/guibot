#!/bin/sh

python3-coverage run --source=guibot -m unittest discover -s tests -v
python3-coverage report -m
