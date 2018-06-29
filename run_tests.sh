#!/bin/sh

python-coverage run --source=guibot -m unittest discover -s tests -v
python-coverage report -m
