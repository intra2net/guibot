#!/bin/bash
set -e

# rpm dependencies
# python2.7
dnf -y install python
# python-imaging
dnf -y install python-pillow
# contour, template, feature, cascade, text matching
dnf -y install python2-numpy opencv-python
# text matching
dnf -y install tesseract

exit 0
