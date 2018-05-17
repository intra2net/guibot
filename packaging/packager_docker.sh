#!/bin/bash

readonly install_variant="${INSTALL_VARIANT:-pip}"

if [ "$install_variant" == "rpm" ]; then
    sudo docker run \
            -v $(pwd)/..:/guibot:rw fedora:27 \
            /bin/bash /guibot/packaging/packager_rpm.sh
elif [ "$install_variant" == "deb" ]; then
    sudo docker run \
            -v $(pwd)/..:/guibot:rw ubuntu:xenial \
            /bin/bash /guibot/packaging/packager_deb.sh
fi
