#!/bin/bash
set -e

# This is an explicit script for PyPI installations reusing the current Travis
# CI configuration in the format of our platform-specific packager scripts.

readonly distro="${DISTRO:-centos}"
readonly distro_version="${VERSION:-8}"
readonly distro_root="${ROOT:-$HOME}"
readonly python_version="${PYTHON_VERSION:-3.8}"
readonly release_tag="${RELEASE_TAG:-}"

# environment dependencies not provided by pip
echo "------------- python3 packages -------------"
if [[ $python_version == '3.10.8' ]]; then dnf -y install python3.10 python3.10-devel; fi
if [[ $python_version == '3.11' ]]; then dnf -y install python3.11 python3.11-devel; fi
if [[ $python_version == '3.12' ]]; then dnf -y install python3.12 python3.12-devel; fi
if [[ $python_version == '3.13' ]]; then dnf -y install python3.13 python3.13-devel; fi
alternatives --install /usr/bin/python3 python3 /usr/bin/python${python_version} 60 \
             --slave /usr/bin/pip3 pip3 /usr/bin/pip${python_version}
alternatives --set python3 /usr/bin/python${python_version}
echo "-------------  pip3 dependencies (for dependencies not available as RPM) -------------"
dnf -y install gcc libX11-devel libXtst-devel libpng-devel redhat-rpm-config
echo "------------- text matching -------------"
dnf -y install tesseract tesseract-devel
dnf -y install gcc-c++
echo "------------- display controlling -------------"
dnf -y install xdotool xwd ImageMagick
dnf -y install x11vnc
echo "------------- upgrade pip3 and install dependencies from pip -------------"
pip3 install --upgrade pip
pip3 install -r "guibot/packaging/pip_requirements.txt"
echo "------------- pip3 packaging and installing of current guibot source -------------"
pip3 install wheel twine
cd "$distro_root/guibot/packaging"
python3 setup.py sdist bdist_wheel
pip3 install dist/guibot*.whl

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
# We need xcb lib utils to run the pyqt6 app
dnf install -y xcb-util*
pip install PyQt6
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/local/lib/python"$python_version"/site-packages/PyQt6/Qt6/plugins/platforms
# the tests and misc data are not included in the PIP package
cp -r "$distro_root/guibot/tests" /usr/local/lib/python"$python_version"/site-packages/guibot/
cp -r "$distro_root/guibot/misc" /usr/local/lib/python"$python_version"/site-packages/guibot/
cd /usr/local/lib/python"$python_version"/site-packages/guibot/tests/

COVERAGE="coverage"
LIBPATH=".." COVERAGE="$COVERAGE" sh coverage_analysis.sh
# TODO: need supported git provider (e.g. GH actions web hooks) for codecov submissions
#mv "$distro_root/guibot/.git" /usr/local/lib/python3*/site-packages/guibot/
#LIBPATH=".." COVERAGE="$COVERAGE" SUBMIT=1 sh coverage_analysis.sh

if [[ -n "$release_tag" ]]; then
    echo "------------- releasing version ${release_tag} to PyPI -------------"
    cd "$distro_root/guibot/packaging"
    if [[ -z $USER ]]; then echo "No username provided as an environment variable" && exit 1; fi
    if [[ -z $PASS ]]; then echo "No password provided as an environment variable" && exit 1; fi
    git_tag="$(git describe)"
    if [[ "$release_tag" != "$git_tag" ]]; then
        echo "Selected release version ${release_tag} does not match tag ${git_tag}"
        exit 1
    fi
    twine upload --repository pypi --user "$USER" --password "$PASS" dist/*
fi

exit 0
