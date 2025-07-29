#!/bin/bash
set -e

readonly distro="${DISTRO:-ubuntu}"
readonly distro_version="${VERSION:-xenial}"
readonly distro_root="${ROOT:-$HOME}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
echo "------------- python3 -------------"
apt-get -y install python3 python3-venv
echo "----- pip dependencies (for dependencies not available as DEB) -----"
apt-get -y install gcc libx11-dev libxtst-dev python3-dev libpng-dev python3-pip
echo "----- create a venv to use that as the python env (needed for python 3.12 compatibility specific to Ubuntu) -----"
python3 -m venv docker_venv --system-site-packages
source docker_venv/bin/activate
echo "------------- upgrade pip -------------"
pip3 install --upgrade pip
echo "------------ install coverage ------------"
pip3 install coverage

echo "------------- python-imaging -------------"
apt-get -y install python3-pil

echo "------------- contour, template, feature, and cascade matching -------------"
apt-get -y install python3-numpy
if [[ $distro_version == "xenial" ]]; then
    export DISABLE_OPENCV=1
else
    apt-get -y install python3-opencv
fi

echo "------------- text matching -------------"
if [[ $distro_version == "xenial" ]]; then
    export DISABLE_OCR=1
else
    apt-get -y install tesseract-ocr libtesseract-dev
    apt-get -y install g++ pkg-config
    pip3 install pytesseract==0.3.13 tesserocr==2.7.1
fi

echo "------------- deep learning -------------"
pip3 install torch==2.2.0 torchvision==0.17.0

echo "------------- display controlling -------------"
if [[ -n "$DISABLE_AUTOPY" && "$DISABLE_AUTOPY" == "1" ]]; then
    export DISABLE_AUTOPY=1
else
    pip3 install autopy
fi
pip3 install vncdotool==0.12.0
apt-get -y install xdotool x11-apps imagemagick
# NOTE: Must install tkinter here to use MouseInfo
apt-get -y install python3-tk
apt-get -y install gnome-screenshot
pip3 install pyautogui==0.9.54
apt-get -y install x11vnc

echo "------------- deb packaging and installing of current guibot source -------------"
apt-get -y install dh-make dh-python debhelper python3-all devscripts
NAME=$(sed -n 's/^Package:[ \t]*//p' "$distro_root/guibot/packaging/debian/control")
CHANGELOG_REVS=($(sed -n -e 's/^guibot[ \t]*(\([0-9]*.[0-9]*\)-[0-9]*).*/\1/p' "$distro_root/guibot/packaging/debian/changelog"))
VERSION=${CHANGELOG_REVS[0]}
cp -r "$distro_root/guibot" "$distro_root/$NAME-$VERSION"
cd "$distro_root/$NAME-$VERSION/packaging"
debuild --no-tgz-check --no-lintian -i -us -uc -b
cp ../${NAME}_${VERSION}*.deb "$distro_root/guibot"
apt-get -y install "$distro_root/guibot/"${NAME}_${VERSION}*.deb

echo "------------- virtual display -------------"
apt-get -y install xvfb vim-common
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
touch /root/.Xauthority
xauth add ${HOST}:99 . $(xxd -l 16 -p /dev/urandom)
sleep 3  # give xvfb some time to start

echo " -------- set tesseract data environment -------- "
export TESSDATA_PREFIX="/usr/share/tesseract-ocr/5/tessdata"
echo "Tesseract data prefix: $TESSDATA_PREFIX"

echo "------------ dump for environment variables and python path ------------"
printenv
python3 -c "import sys; print(sys.prefix)"

echo "------------- unit tests -------------"
apt-get install -y python3-pyqt6
export XDG_RUNTIME_DIR="/tmp/runtime-root"
mkdir /tmp/runtime-root
chmod 0700 /tmp/runtime-root
cd /usr/lib/python3/dist-packages/guibot/tests
LIBPATH=".." COVERAGE="coverage" sh coverage_analysis.sh

exit 0
