# Get python "site-lib" path by executing small python script
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           guibender
Version:        0.11
Release:        3
Summary:        GUI testing tool

Group:          Development/Tools
License:        LGPLv3+
URL:            http://developer.intra2net.com
# TODO: source location?
Source0:        http://developer.intra2net.com/%{name}-%{version}.tar.gz

# There are some conditional dependencies that we will require upon use,
# in particular one of autopy/vncdotool/qemu-kvm for the desktop control
# backend.
# for autopy: download or find modules -> copy to /usr/lib/python2.7/site-packages/autopy/
# for vncdotool: download -> python setup.py install (in vncdotool folder)
# for qemu: need to have autotest with virt-test installed then simply pass the qemu monitor as parameter
# TODO: opencv must be turned into conditional dependency only if we use
# particular computer vision backends.
Requires:       opencv >= 3.1
Requires:       opencv-python

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
%{__install} -d %{buildroot}%{python_sitelib}/guibender/guibender
%{__install} -d %{buildroot}%{python_sitelib}/guibender/tests/images
%{__install} -d %{buildroot}%{python_sitelib}/guibender/examples/images
%{__install} -d %{buildroot}%{python_sitelib}/guibender/misc/tessdata
%{__cp} -a guibender/* %{buildroot}%{python_sitelib}/guibender/guibender
%{__cp} -a tests/* %{buildroot}%{python_sitelib}/guibender/tests
%{__cp} -a examples/* %{buildroot}%{python_sitelib}/guibender/examples
%{__cp} -a misc/* %{buildroot}%{python_sitelib}/guibender/misc
%{__install} -t %{buildroot}%{python_sitelib}/guibender/ __init__.py run_tests.sh


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE doc/api doc/tutorials
#%config guibender.cfg
#%ghost guibender.log
#%if 0%{?fedora} >= 9 || 0%{?rhel} >= 6
#  %{python_sitelib}/%{name}-%{version}-py?.?.egg-info
#%endif
# top level dir
%dir %{python_sitelib}/guibender
%{python_sitelib}/guibender/__init__.py
%exclude %{python_sitelib}/guibender/__init__.pyc
%exclude %{python_sitelib}/guibender/__init__.pyo
%{python_sitelib}/guibender/guibender
%exclude %{python_sitelib}/guibender/guibender/*.pyc
%exclude %{python_sitelib}/guibender/guibender/*.pyo
%{python_sitelib}/guibender/tests
%exclude %{python_sitelib}/guibender/tests/*.pyc
%exclude %{python_sitelib}/guibender/tests/*.pyo
%{python_sitelib}/guibender/examples
%exclude %{python_sitelib}/guibender/examples/*.pyc
%exclude %{python_sitelib}/guibender/examples/*.pyo
%{python_sitelib}/guibender/misc
%exclude %{python_sitelib}/guibender/misc/*.pyc
%exclude %{python_sitelib}/guibender/misc/*.pyo
%{python_sitelib}/guibender/run_tests.sh


%changelog
* Mon May 22 2017 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.11-2
- Update from OpenCV 2.4 to OpenCV 3.1
- Addition of CV backends like OCR (tesseract), CNN (PyTorch)
- Multiple target types beyond images

* Sat Apr 13 2013 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.10-1
- Initial spec file
