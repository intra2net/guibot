#!/bin/bash
set -e

readonly distro="${DISTRO:-ubuntu}"
readonly version="${VERSION:-xenial}"

# dep dependencies
apt-get update
# python3
apt-get -y install python3 python3-coverage
# python-imaging
apt-get -y install python3-pil
# contour, template, feature, cascade, text matching
apt-get -y install python3-numpy python3-opencv
# text matching
apt-get -y install tesseract-ocr
# desktop control
apt-get -y install xdotool x11-apps imagemagick
apt-get -y install tightvncserver

# pip dependencies (not available as DEB)
apt-get -y install gcc libx11-dev libxtst-dev python3-dev libpng-dev python3-pip
pip3 install autopy==1.1.1
pip3 install torch==0.4.1 torchvision==0.2.1
pip3 install vncdotool==0.12.0

# deb packaging
apt-get -y install dh-make dh-python debhelper python3-all devscripts
ROOT=""
NAME=$(sed -n 's/^Package:[ \t]*//p' "$ROOT/guibot/packaging/debian/control")
CHANGELOG_REVS=($(sed -n -e 's/^guibot[ \t]*(\([0-9]*.[0-9]*\)-[0-9]*).*/\1/p' "$ROOT/guibot/packaging/debian/changelog"))
VERSION=${CHANGELOG_REVS[0]}
cp -r "$ROOT/guibot" "$ROOT/$NAME-$VERSION"
cd "$ROOT/$NAME-$VERSION/packaging"
debuild --no-tgz-check --no-lintian -i -us -uc -b
cp ../${NAME}_${VERSION}*.deb "$ROOT/guibot"
apt-get -y install "$ROOT/guibot/"${NAME}_${VERSION}*.deb
rm -fr "$ROOT/$NAME-$VERSION"

# virtual display
apt-get -y install xvfb
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
sleep 3  # give xvfb some time to start

# unit tests
apt-get install -y python3-pyqt5
cd /usr/lib/python3/dist-packages/guibot/tests
LIBPATH=".." COVERAGE="python3-coverage" sh run_tests.sh

exit 0
