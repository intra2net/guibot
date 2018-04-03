#!/bin/bash
set -e

# dep dependencies
apt-get update
# python2.7
# in some cases another repo has to be added
#apt-get -y install software-properties-common
#add-apt-repository ppa:fkrull/deadsnakes-python2.7
apt-get -y install python2.7 python-coverage
# python-imaging
apt-get -y install python-pil
# contour, template, feature, cascade, text matching
apt-get -y install python-numpy python-opencv
# TODO: unbelievably, ubuntu still relies on OpenCV 2.X but we
# won't add a custom installation from pip which we already do in
# another variant. Instead, we will disable incompatible tests.
export LEGACY_OPENCV=1
# text matching
apt-get -y install tesseract-ocr
# desktop control
apt-get -y install xdotool x11-apps imagemagick
apt-get -y install tightvncserver

# pip dependencies (not available as DEB)
apt-get -y install gcc libx11-dev libxtst-dev python-dev libpng12-dev python-pip
pip install autopy
pip install http://download.pytorch.org/whl/cu75/torch-0.1.11.post5-cp27-none-linux_x86_64.whl
pip install torchvision
pip install vncdotool

# deb packaging
apt-get -y install dh-make devscripts
CHANGELOG_REVS=($(sed -n -e 's/^guibot[ \t]*(\([0-9]*.[0-9]*\)-[0-9]*).*/\1/p' /guibot/packaging/debian/changelog))
VERSION=${CHANGELOG_REVS[0]}
cp -r /guibot /guibot-$VERSION
cd /guibot-$VERSION/packaging
debuild --no-tgz-check --no-lintian -i -us -uc -b
cp ../guibot_$VERSION*.deb /guibot
apt-get -y install /guibot/guibot_*.deb

# virtual display
apt-get -y install xvfb
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> xvfb.log  &
sleep 3  # give xvfb some time to start

# unit tests
apt-get install -y python-qt4
cd /usr/lib/python2.7/dist-packages/guibot/
sh run_tests.sh

exit 0
