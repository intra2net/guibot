# Build with OpenCV support - default is 0 and needs to be activated with
# "--with opencv" command line switch.
%bcond_with opencv

Name:           guibot
Version:        0.40
Release:        1%{?dist}
Summary:        GUI automation tool

Group:          Development/Tools
License:        LGPLv3+
URL:            http://guibot.org
# TODO: the package has a different name in GitHub, namely %{version}.tar.gz but in a
# kind of stubborn way the setup macro would use the basename below so use a local tarball
Source0:        https://github.com/intra2net/guibot/archive/%{name}-%{version}.tar.gz

Requires:       python3-pillow
%if %{with opencv}
Requires:       opencv >= 3.1
Requires:       python3-opencv
%endif

%description
A tool for GUI automation using a variety of computer vision and desktop control backends.
Supported CV backends are based on OpenCV, PyTorch, and autopy, and supported DC backends
on autopy, vncdotool, and qemu.

%package -n python3-guibot
Summary:        GUI automation tool
Group:          Development/Tools
%description -n python3-guibot
A tool for GUI automation using a variety of computer vision and desktop control backends.
Supported CV backends are based on OpenCV, PyTorch, and autopy, and supported DC backends
on autopy, vncdotool, and qemu.

#Patch1:        first_fix.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       anaconda-runtime >= 11.4.1.5, yum => 3.2.19, repoview, createrepo >= 0.4.11
BuildRequires:  python3-devel

BuildArch:      noarch

# don't generate debug informaiton
%global debug_package %{nil}


%prep
%setup -q

#%patch1 -p1


%build
pushd packaging
%{__python3} setup.py build
popd


%install
pushd packaging
%{__python3} setup.py install --root %{buildroot}
popd
%{__install} -d %{buildroot}%{python3_sitelib}/guibot/tests/images
%{__install} -d %{buildroot}%{python3_sitelib}/guibot/misc/tessdata
%{__cp} -a tests/* %{buildroot}%{python3_sitelib}/guibot/tests
%{__cp} -a misc/* %{buildroot}%{python3_sitelib}/guibot/misc


%clean
rm -rf %{buildroot}


%check
# TODO: add unit tests here


%files -n python3-guibot
%defattr(-,root,root,-)
%license LICENSE
%doc docs/api docs/tutorials docs/examples
#%config guibot.cfg
#%ghost guibot.log
%{python3_sitelib}/*


%changelog
* Mon Mar 30 2020 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.40-1
- Update to more recent versions for all backends
- Overall bug fixes and code linting

* Mon Mar 18 2019 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.31-1
- Add support for Python 3.7
- Update all backends to ones supporting Python 3.7

* Sat Jun 30 2018 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.30-1
- Switch support to Python 3
- API version updates for AutoPy, PyTorch, VNCDoTool

* Fri Jun 29 2018 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.21-1
- XDoTool desktop control backend and password support for VNCDoTool
- Improved form filling region methods

* Fri Mar 23 2018 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.20-1
- Fallback chains functionality
- Multiple OCR fixes

* Mon May 22 2017 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.11-2
- Update from OpenCV 2.4 to OpenCV 3.1
- Addition of CV backends like OCR (tesseract), CNN (PyTorch)
- Multiple target types beyond images

* Sat Apr 13 2013 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.10-1
- Initial spec file
