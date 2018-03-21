# Dependencies

Here is a hierarchical list of dependencies depending on your choice of computer vision and desktop
control backends. In addition it includes problems you can encounter and ways to solve them. For
windows, you just need to find the required packages most of which are fully available as well.

- python2.7
    - usually preinstalled on Linux systems
- python-imaging
    - usually preinstalled on Linux systems - python-pillow on Fedora/CentOS, pyton-pil on Ubuntu
- computer vision backends
    - autopy (autopy.org)
        - no other dependencies besides installing autopy
            - steps:
                git clone git://github.com/msanders/autopy.git
                cd autopy
                python setup.py build
                python setup.py install
            - notes:
                - on Fedora and CentOS this should suffice
                - on Ubuntu there is an error with the alert module import
                    - solution is to comment it in the __init__ module since we don't need it anyway
    - contour, template, feature, cascade matching
        - numpy, opencv, opencv-python (python-numpy, python-opencv on ubuntu)
    - text matching (OCR)
        - numpy, opencv, opencv-python (same as above)
        - tesseract
            - steps:
                - install tesseract packages
                    - on Ubuntu: tesseract-ocr, libtesseract-dev libleptonica-dev
                    - on CentOS: tesseract tesseract-devel leptonica leptonica-devel
                - you need a custom build of OpenCV together with the opencv-contrib repo in order to
                  properly detect tesseract and use ERStat regions
                    git clone https://github.com/opencv/opencv.git
                    cd opencv
                    git checkout 3.1.0  # or 3.2.0 for ERStat
                    cd ..
                    git clone https://github.com/Itseez/opencv_contrib.git
                    cd opencv_contrib
                    git checkout 3.1.0  # or 3.2.0 for ERStat
                    cd ../opencv
                    mkdir build
                    cd build
                    cmake .. -DOPENCV_EXTRA_MODULES_PATH=../../opencv_contrib/modules/ -DBUILD_OPENCV_PYTHON2=ON -DCMAKE_BUILD_TYPE=RELEASE -DCMAKE_INSTALL_PREFIX=/usr/local -DINSTALL_C_EXAMPLES=OFF -DINSTALL_PYTHON_EXAMPLES=ON -DBUILD_EXAMPLES=ON
                    make
                    sudo make install
                    sudo ldconfig
            - notes:
                - this custom build of OpenCV is not necessary if you can use the somewhat inferior
                  Hidden Markov Model OCR and contour-based text detection
    - deep learning based matching
        - pyTorch
            - steps:
                pip install http://download.pytorch.org/whl/cu75/torch-0.1.11.post5-cp27-none-linux_x86_64.whl
                pip install torchvision
            - notes:
                - on Fedora and CentOS this should suffice
                - on Ubuntu, torchvision encounters a PyPI incompatibility issue
                    - this package is secondary and adds datasets and some parts necessary only for
                      training and/or testing nets
- desktop control backends
    - AutoPy (autopy.org)
        - no other dependencies besides installing autopy (on windows)
        - xdotool (on linux)
    - Qemu
        - qemu, virt-test
        - having these simply pass the qemu monitor as parameter
    - VNCDoTool
        - vncdotool
        - python setup.py install (in vncdotool folder)
