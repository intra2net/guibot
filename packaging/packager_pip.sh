#!/bin/bash
set -e

# This is an explicit script for PyPI installations reusing the current Travis
# CI configuration in the format of our platform-specifric packager scripts.

readonly distro="${DISTRO:-centos}"
readonly distro_version="${VERSION:-8}"
readonly distro_root="${ROOT:-$HOME}"

# environment dependencies not provided by pip
# python3
dnf -y install python3 python3-coverage
# pip dependencies in order to build some PyPI packages
dnf -y install gcc libX11-devel libXtst-devel python3-devel libpng-devel python3-pip redhat-rpm-config
pip3 install --upgrade pip
# text matching
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
# screen controlling
dnf -y install xdotool xwd ImageMagick
# TODO: PyAutoGUI's scrot dependencies are broken on Fedora
export DISABLE_PYAUTOGUI=1
#dnf -y install python3-tkinter scrot
#pip3 install pyautogui==0.9.52
dnf -y install x11vnc

# dependencies that could be installed using pip
pip3 install -r "$distro_root/guibot/packaging/pip_requirements.txt"

# pip packaging and installing of current guibot source
pip3 install wheel
cd "$distro_root/guibot/packaging"
python3 setup.py sdist bdist_wheel
# done for potential future deployment
cp dist/guibot*.whl "$distro_root/guibot"
cp dist/guibot*.tar.gz "$distro_root/guibot"
pip3 install "$distro_root"/guibot/guibot*.whl

# virtual display
dnf install -y xorg-x11-server-Xvfb
export DISPLAY=:99.0
Xvfb :99 -screen 0 1024x768x24 &> /tmp/xvfb.log  &
sleep 3  # give xvfb some time to start

# unit tests
dnf install -y python3-PyQt5
# the tests and misc data are not included in the PIP package
cp -r "$distro_root/guibot/tests" /usr/local/lib/python3*/site-packages/guibot/
cp -r "$distro_root/guibot/misc" /usr/local/lib/python3*/site-packages/guibot/
cd /usr/local/lib/python3*/site-packages/guibot/tests
if (( distro_version <= 7 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh run_tests.sh

exit 0
