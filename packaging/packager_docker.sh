#!/bin/bash

readonly install_variant="${INSTALL_VARIANT:-pip}"

if [ "$install_variant" == "rpm" ]; then
    sudo docker run \
            -v $(pwd)/..:/guibot:rw fedora:28 \
            /bin/bash /guibot/packaging/packager_rpm.sh
elif [ "$install_variant" == "deb" ]; then
    sudo docker run \
            -v $(pwd)/..:/guibot:rw ubuntu:bionic \
            /bin/bash /guibot/packaging/packager_deb.sh
fi
