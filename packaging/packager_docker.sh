#!/bin/bash

readonly install_variant="${INSTALL_VARIANT:-pip}"
readonly packager=$(echo $install_variant | cut -d '.' -f 1)
readonly distro=$(echo $install_variant | cut -d '.' -f 2)
readonly version=$(echo $install_variant | cut -d '.' -f 3)

if [ "$packager" == "rpm" ]; then
    sudo docker run \
            -e DISTRO="$distro" -e VERSION="$version" \
            -v $(pwd)/..:/guibot:rw $distro:$version \
            /bin/bash /guibot/packaging/packager_rpm.sh
elif [ "$packager" == "deb" ]; then
    sudo docker run \
            -e DISTRO="$distro" -e VERSION="$version" \
            -v $(pwd)/..:/guibot:rw $distro:$version \
            /bin/bash /guibot/packaging/packager_deb.sh
fi
