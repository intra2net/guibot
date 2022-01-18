#!/bin/bash
set -e

# This is an explicit script for PyPI installations reusing the current Travis
# CI configuration in the format of our platform-specifric packager scripts.

readonly distro="${DISTRO:-centos}"
readonly distro_version="${VERSION:-8}"
readonly distro_root="${ROOT:-$HOME}"
readonly python_version="${PYTHON_VERSION:-3.8}"

# environment dependencies not provided by pip
# python3
if [[ $python_version == '3.8' ]]; then dnf -y install python38 python38-devel; fi
if [[ $python_version == '3.7' ]]; then dnf -y install python37 python37-devel; fi
if [[ $python_version == '3.6' ]]; then dnf -y install python36 python36-devel; fi
alternatives --install /usr/bin/python3 python3 /usr/bin/python${python_version} 60 \
             --slave /usr/bin/pip3 pip3 /usr/bin/pip${python_version}
alternatives --set python3 /usr/bin/python${python_version}
# pip dependencies in order to build some PyPI packages
dnf -y install gcc libX11-devel libXtst-devel libpng-devel redhat-rpm-config
# text matching
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
# screen controlling
dnf -y install xdotool xwd ImageMagick
# TODO: PyAutoGUI's scrot dependencies are broken on CentOS/Rocky
#dnf -y install scrot
export DISABLE_PYAUTOGUI=1
dnf -y install x11vnc

# dependencies that could be installed using pip
pip3 install --upgrade pip
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
# the tests and misc data are not included in the PIP package
cp -r "$distro_root/guibot/tests" /usr/local/lib/python3*/site-packages/guibot/
cp -r "$distro_root/guibot/misc" /usr/local/lib/python3*/site-packages/guibot/
cd /usr/local/lib/python3*/site-packages/guibot/tests
if (( distro_version <= 7 )); then
    COVERAGE="python3-coverage"
else
    COVERAGE="coverage-${python_version}"
fi
LIBPATH=".." COVERAGE="$COVERAGE" sh run_tests.sh

exit 0
