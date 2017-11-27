# Get python "site-lib" path by executing small python script
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
# Build with OpenCV support - default is 0 and needs to be activated with
# "--with opencv" command line switch.
%bcond_with opencv

Name:           guibot
Version:        0.11
Release:        3
Summary:        GUI testing tool

Group:          Development/Tools
License:        LGPLv3+
URL:            http://developer.intra2net.com
# TODO: source location?
Source0:        http://developer.intra2net.com/%{name}-%{version}.tar.gz

Requires:       python = 2.7
Requires:       python-pillow
%if %{with opencv}
Requires:       opencv >= 3.1
Requires:       opencv-python
%endif

%description
A tool to use for GUI testing using OpenCV and PyTorch.

#Patch1:        first_fix.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       anaconda-runtime >= 11.4.1.5, yum => 3.2.19, repoview, createrepo >= 0.4.11
BuildRequires:  python-devel

BuildArch:      noarch

# don't generate debug informaiton
%global debug_package %{nil}


%prep
%setup -q

#%patch1 -p1


%build


%install
rm -rf %{buildroot}
%{__install} -d %{buildroot}%{python_sitelib}/guibot/guibot
%{__install} -d %{buildroot}%{python_sitelib}/guibot/tests/images
%{__install} -d %{buildroot}%{python_sitelib}/guibot/examples/images
%{__install} -d %{buildroot}%{python_sitelib}/guibot/misc/tessdata
%{__cp} -a guibot/* %{buildroot}%{python_sitelib}/guibot/guibot
%{__cp} -a tests/* %{buildroot}%{python_sitelib}/guibot/tests
%{__cp} -a examples/* %{buildroot}%{python_sitelib}/guibot/examples
%{__cp} -a misc/* %{buildroot}%{python_sitelib}/guibot/misc
%{__install} -t %{buildroot}%{python_sitelib}/guibot/ __init__.py run_tests.sh


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE doc/api doc/tutorials
#%config guibot.cfg
#%ghost guibot.log
#%if 0%{?fedora} >= 9 || 0%{?rhel} >= 6
#  %{python_sitelib}/%{name}-%{version}-py?.?.egg-info
#%endif
# top level dir
%dir %{python_sitelib}/guibot
%{python_sitelib}/guibot/__init__.py
%exclude %{python_sitelib}/guibot/__init__.pyc
%exclude %{python_sitelib}/guibot/__init__.pyo
%{python_sitelib}/guibot/guibot
%exclude %{python_sitelib}/guibot/guibot/*.pyc
%exclude %{python_sitelib}/guibot/guibot/*.pyo
%{python_sitelib}/guibot/tests
%exclude %{python_sitelib}/guibot/tests/*.pyc
%exclude %{python_sitelib}/guibot/tests/*.pyo
%{python_sitelib}/guibot/examples
%exclude %{python_sitelib}/guibot/examples/*.pyc
%exclude %{python_sitelib}/guibot/examples/*.pyo
%{python_sitelib}/guibot/misc
%exclude %{python_sitelib}/guibot/misc/*.pyc
%exclude %{python_sitelib}/guibot/misc/*.pyo
%{python_sitelib}/guibot/run_tests.sh


%changelog
* Mon May 22 2017 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.11-2
- Update from OpenCV 2.4 to OpenCV 3.1
- Addition of CV backends like OCR (tesseract), CNN (PyTorch)
- Multiple target types beyond images

* Sat Apr 13 2013 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.10-1
- Initial spec file
