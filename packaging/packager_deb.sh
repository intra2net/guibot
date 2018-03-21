#!/bin/bash
set -e

# dep dependencies
apt-get update
# python2.7
# in some cases another repo has to be added
#apt-get -y install software-properties-common
#add-apt-repository ppa:fkrull/deadsnakes-python2.7
apt-get -y install python2.7
# python-imaging
apt-get -y install python-pil
# contour, template, feature, cascade, text matching
apt-get -y install python-numpy python-opencv
# text matching
apt-get -y install tesseract-ocr

exit 0
