# guibot ![CI status](https://travis-ci.org/intra2net/guibot.svg?branch=master) [![Documentation Status](https://readthedocs.org/projects/guibot/badge/?version=latest)](http://guibot.readthedocs.io/en/latest/?badge=latest) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/intra2net/guibot.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/intra2net/guibot/context:python) [![codecov](https://codecov.io/gh/intra2net/guibot/branch/master/graph/badge.svg)](https://codecov.io/gh/intra2net/guibot)

A tool for GUI automation using a variety of computer vision and desktop control backends.

## Supported backends

Supported CV backends are based on

- [OpenCV](https://github.com/opencv/opencv)
    - Template matching
    - Contour matching
    - Feature matching
    - Haar cascade matching
    - Template-feature and mixed matching
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
    - Text matching
- [PyTorch](https://github.com/pytorch/pytorch)
    - CNN matching
- [autopy](https://github.com/msanders/autopy)
    - AutoPy matching

Supported DC backends are based on

- [autopy](https://github.com/msanders/autopy)
- [vncdotool](https://github.com/sibson/vncdotool)
- [qemu](https://github.com/qemu/qemu)

## Resources

Homepage: http://guibot.org

Documentation: http://guibot.readthedocs.io

Installation: https://github.com/intra2net/guibot/wiki/Packaging

Issue tracking: https://github.com/intra2net/guibot/issues
