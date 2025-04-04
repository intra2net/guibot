#!/bin/bash
set -e

readonly distro="${DISTRO:-fedora}"
readonly distro_version="${VERSION:-30}"
readonly distro_root="${ROOT:-$HOME}"

dnf -y update
echo "------------- python3 -------------"
dnf -y install python3 python3-coverage python3-devel
echo "------------- python-imaging -------------"
dnf -y install python3-pillow
echo "-------------  pip dependencies (for dependencies not available as RPM) -------------"
dnf -y install gcc libX11-devel libXtst-devel python3-devel libpng-devel python3-pip redhat-rpm-config
echo "------------- upgrade pip  -------------"
pip3 install --upgrade pip

echo "------------- contour, template, feature, and cascade matching -------------"
dnf -y install python3-numpy python3-opencv

echo "------------- text matching -------------"
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
pip3 install pytesseract==0.3.13 tesserocr==2.7.1

echo "------------- deep learning -------------"
dnf -y install python3-torch python3-torch-devel
# TODO: python3-torchvision version available is broken (no module found)
pip3 install torchvision==0.17.0

echo "------------- display controlling -------------"
if [[ -n "$DISABLE_AUTOPY" && "$DISABLE_AUTOPY" == "1" && $distro_version -gt 32 ]]; then
    export DISABLE_AUTOPY=1
else
    pip3 install autopy
fi
pip3 install vncdotool==0.12.0
dnf -y install xdotool xwd ImageMagick
# NOTE: No need for installing tkinter here because it's a dependency from torch (it is installed with it)
dnf -y install gnome-screenshot
pip3 install pyautogui==0.9.54
dnf -y install x11vnc

echo "------ rpm packaging and installing of current guibot source ------"
dnf -y install rpm-build
NAME=$(sed -n 's/^Name:[ \t]*//p' "$distro_root/guibot/packaging/guibot.spec")
VERSION=$(sed -n 's/^Version:[ \t]*//p' "$distro_root/guibot/packaging/guibot.spec")
cp -r "$distro_root/guibot" "$distro_root/$NAME-$VERSION"
mkdir -p ~/rpmbuild/SOURCES
tar czvf ~/rpmbuild/SOURCES/$NAME-$VERSION.tar.gz -C "$distro_root/" --exclude=.* --exclude=*.pyc $NAME-$VERSION
rpmbuild -ba "$distro_root/$NAME-$VERSION/packaging/guibot.spec" --with opencv
cp ~/rpmbuild/RPMS/x86_64/python3-$NAME-$VERSION*.rpm "$distro_root/guibot"
dnf -y install "$distro_root/guibot/python3-"$NAME-$VERSION*.rpm

echo "------------- virtual display -------------"
dnf install -y xorg-x11-server-Xvfb vim-common
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
touch /root/.Xauthority
xauth add ${HOST}:99 . $(xxd -l 16 -p /dev/urandom)
sleep 3  # give xvfb some time to start

echo " -------- set tesseract data environment variable -------- "
export TESSDATA_PREFIX="/usr/share/tesseract/tessdata/"
echo "Tesseract data prefix: $TESSDATA_PREFIX"

echo "------------ dump for environment variables and python path ------------"
printenv
python3 -c "import sys; print(sys.prefix)"

echo "------------- unit tests -------------"
dnf install -y python3-PyQt6
cd /lib/python3*/site-packages/guibot/tests
if (( distro_version <= 30 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh coverage_analysis.sh

exit 0
