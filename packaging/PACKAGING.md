# Installation

There are three main ways to deploy guibot on your platform: a platform-independent way
through PyPI as well as platform-specific ways through a RPM or Debian package. As a
platform specific approach for Windows, you just need to find the required executables
for the backends dependencies most of which are fully available as well.

In order to build an RPM/Debian package, you have to clone the repository

```
git clone --depth 1 https://github.com/intra2net/guibot
```

or to download the most recent release tarball. All following commands assume you are
running from within the guibot folder.

# PyPI

To install all backend dependencies run the following within the guibot folder

```
pip install -r packaging/pip_requirements.txt
```

Currently only Python 2.7 is supported. A PyPI package should also be available later on.

# RPM package

You can build an RPM package with

```
bash packaging/packager_rpm.sh
```

or simply view the contents for RPM requirements for running as well as building split
into the respective stages.

# Debian package

You can build a Debian package with

```
bash packaging/packager_deb.sh
```

or use it in the same way as the RPM packager script.
