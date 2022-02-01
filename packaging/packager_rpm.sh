#!/bin/bash
set -e

readonly distro="${DISTRO:-fedora}"
readonly distro_version="${VERSION:-30}"
readonly distro_root="${ROOT:-$HOME}"

# rpm dependencies
# python3
dnf -y install python3 python3-coverage
# python-imaging
dnf -y install python3-pillow
# pip dependencies (for dependencies not available as RPM)
dnf -y install gcc libX11-devel libXtst-devel python3-devel libpng-devel python3-pip redhat-rpm-config
pip3 install --upgrade pip
# contour, template, feature, cascade, text matching
dnf -y install python3-numpy python3-opencv
# text matching
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
pip3 install pytesseract==0.3.4 tesserocr==2.5.1
# deep learning
pip3 install torch==1.8.1 torchvision==0.9.1
# screen controlling
if (( distro_version <= 32 )); then
    pip3 install autopy==4.0.0
else
    export DISABLE_AUTOPY=1
fi
pip3 install vncdotool==0.12.0
dnf -y install xdotool xwd ImageMagick
# TODO: PyAutoGUI's scrot dependencies are broken on Fedora 33-, currently provided offline
dnf -y install python3-tkinter #scrot
pip3 install pyautogui==0.9.53
dnf -y install x11vnc

# rpm packaging and installing of current guibot source
dnf -y install rpm-build
NAME=$(sed -n 's/^Name:[ \t]*//p' "$distro_root/guibot/packaging/guibot.spec")
VERSION=$(sed -n 's/^Version:[ \t]*//p' "$distro_root/guibot/packaging/guibot.spec")
cp -r "$distro_root/guibot" "$distro_root/$NAME-$VERSION"
mkdir -p ~/rpmbuild/SOURCES
tar czvf ~/rpmbuild/SOURCES/$NAME-$VERSION.tar.gz -C "$distro_root/" --exclude=.* --exclude=*.pyc $NAME-$VERSION
rpmbuild -ba "$distro_root/$NAME-$VERSION/packaging/guibot.spec" --with opencv
cp ~/rpmbuild/RPMS/x86_64/python3-$NAME-$VERSION*.rpm "$distro_root/guibot"
dnf -y install "$distro_root/guibot/python3-"$NAME-$VERSION*.rpm
rm -fr "$distro_root/$NAME-$VERSION"

# virtual display
dnf install -y xorg-x11-server-Xvfb vim-common
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
touch /root/.Xauthority
xauth add ${HOST}:99 . $(xxd -l 16 -p /dev/urandom)
sleep 3  # give xvfb some time to start

# unit tests
dnf install -y python3-PyQt5
cd /lib/python3*/site-packages/guibot/tests
if (( distro_version <= 30 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh coverage_analysis.sh

exit 0
