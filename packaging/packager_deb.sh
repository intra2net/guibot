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

# pip dependencies (not available as DEB)
apt-get -y install gcc libx11-dev libxtst-dev python-dev libpng12-dev python-pip
pip install autopy
pip install http://download.pytorch.org/whl/cu75/torch-0.1.11.post5-cp27-none-linux_x86_64.whl
pip install torchvision

# virtual display
apt-get -y install xvfb
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x16 &> xvfb.log  &
sleep 3  # give xvfb some time to start

exit 0
