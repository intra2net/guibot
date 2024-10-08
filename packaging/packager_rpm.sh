#!/bin/bash
set -e

readonly distro="${DISTRO:-fedora}"
readonly distro_version="${VERSION:-30}"
readonly distro_root="${ROOT:-$HOME}"

echo "------------- python3 -------------"
dnf -y install python3 python3-coverage python3-devel
echo "------------- python-imaging -------------"
dnf -y install python3-pillow
echo "-------------  pip dependencies (for dependencies not available as RPM) -------------"
dnf -y install gcc libX11-devel libXtst-devel python3-devel libpng-devel python3-pip redhat-rpm-config
echo "------------- upgrade pip  -------------"
pip3 install --upgrade pip

echo "------------- contour, template, feature, cascade, text matching -------------"
dnf -y install python3-numpy python3-opencv
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
pip3 install pytesseract==0.3.13 tesserocr==2.7.1

echo "------------- deep learning -------------"
dnf -y install python3-torch python3-torch-devel
pip3 install torchvision==0.17.0
# TODO: python3-torchvision version available is broken (no module found)

echo "------------- screen controlling -------------"
echo "DISABLE_AUTOPY is set to: '$DISABLE_AUTOPY'"
if [[ -n "$DISABLE_AUTOPY" && "$DISABLE_AUTOPY" == "1" ]]; then
  echo "Autopy installation disabled."
  export DISABLE_AUTOPY=1
else
  echo "Installing autopy..."
  pip3 install autopy
fi
# TODO: vncdotool doesn't control its Twisted which doesn't control its "incremental" dependency
pip3 install vncdotool==0.12.0
dnf -y install xdotool xwd ImageMagick
# NOTE: PyAutoGUI's scrot dependencies are broken on Fedora 33- so we don't support these
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
rm -fr "$distro_root/$NAME-$VERSION"

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
dnf install -y python3-PyQt5
cd /lib/python3*/site-packages/guibot/tests
if (( distro_version <= 30 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh coverage_analysis.sh

exit 0
