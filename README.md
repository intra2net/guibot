# guibot [![Build Status](https://travis-ci.org/intra2net/guibot.svg?branch=master)](https://travis-ci.org/intra2net/guibot) [![Documentation Status](https://readthedocs.org/projects/guibot/badge/?version=latest)](http://guibot.readthedocs.io/en/latest/?badge=latest) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/intra2net/guibot.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/intra2net/guibot/context:python) [![codecov](https://codecov.io/gh/intra2net/guibot/branch/master/graph/badge.svg)](https://codecov.io/gh/intra2net/guibot)

A tool for GUI automation using a variety of computer vision and display control backends.

## Introduction

In order to do GUI automation you usually need to solve two problems: first, you need to have a way to control and interact with the interface and platform you are automating and second, you need to be able to locate the objects you are interested in on the screen. Guibot helps you do both.

To interact with GUIs, Guibot provides the [`controller`](https://github.com/intra2net/guibot/blob/master/guibot/controller.py) module which contains a common interface for different display backends, with methods to move the mouse, take screenshots, type characters and so on. The backend to use will depend on how your interface is accessible, but the ones currently supported are listed below.

To locate an element on the screen, you will need an image representing the screen, a [`target`](https://github.com/intra2net/guibot/blob/master/guibot/target.py) and a [`finder`](https://github.com/intra2net/guibot/blob/master/guibot/finder.py) - the finder looks for the target on the image, and returns the coordinates to the region where that target appears. Finders, like display controllers, are wrappers around different backends that Guibot supports (see below), while targets are a representation of the object you are looking for, such as images, text, or patterns.

Finally, to bridge the gap between controlling the GUI and finding elements, the [`region`](https://github.com/intra2net/guibot/blob/master/guibot/region.py) module is provided. It represents a subregion of a screen, and contains methods to locate targets in this region and interact with the graphical interface using the chosen backends.

## Supported backends

Supported Computer Vision (CV) backends are based on

- [OpenCV](https://github.com/opencv/opencv)
    - Template matching
    - Contour matching
    - Feature matching
    - Haar cascade matching
    - Template-feature and mixed matching
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
    - Text matching through pytesseract, tesserocr, or OpenCV's bindings
- [PyTorch](https://github.com/pytorch/pytorch)
    - R-CNN matching through Faster R-CNN or Mask R-CNN
- [autopy](https://github.com/msanders/autopy)
    - AutoPy matching

Supported Display Controller (DC) backends are based on

- [AutoPy](https://github.com/msanders/autopy)
- [PyAutoGUI](https://github.com/asweigart/pyautogui)
- [VNCDoTool](https://github.com/sibson/vncdotool)
- [XDoTool](https://www.semicomplete.com/projects/xdotool)

## Resources

Homepage: http://guibot.org

Documentation: http://guibot.readthedocs.io

Installation: https://github.com/intra2net/guibot/wiki/Packaging

Issue tracking: https://github.com/intra2net/guibot/issues

Project wiki: https://github.com/intra2net/guibot/wiki
