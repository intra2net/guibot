#!/usr/bin/python

from setuptools import setup
from os import path

p = path.abspath(path.dirname(__file__))
with open(path.join(p, '../README.md')) as f:
    README = f.read()

setup(
    name='guibot',
    version='0.20.1',
    description='GUI automation tool',
    long_description=README,
    long_description_content_type='text/markdown',

    install_requires=[
        "Pillow",
        'numpy',
        'opencv-contrib-python',
    ],
    tests_require=[
        'PyQt4',
    ],

    url='http://guibot.org',
    maintainer='Intra2net',
    maintainer_email='opensource@intra2net.com',
    download_url='',

    packages=['guibot'],
    package_dir={'guibot': '../guibot'},

    classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
          'Topic :: Desktop Environment',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
          'Topic :: Software Development :: Testing',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
