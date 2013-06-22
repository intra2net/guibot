# Get python "site-lib" path by executing small python script
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           guibender
Version:        0.10
Release:        1
Summary:        GUI testing tool

Group:          Development/Tools
License:        LGPLv3+
URL:            http://developer.intra2net.com
# TODO: source location?
Source0:        http://developer.intra2net.com/%{name}-%{version}.tar.gz

Requires:       opencv >= 2.4

%description
A tool to use for GUI testing using autopy and OpenCV.

#Patch1:        first_fix.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       anaconda-runtime >= 11.4.1.5, yum => 3.2.19, repoview, createrepo >= 0.4.11
BuildRequires:  python-devel

BuildArch:      noarch


%prep
%setup -q

#%patch1 -p1


%build


%install
rm -rf %{buildroot}
%{__install} -d %{buildroot}%{python_sitelib}/guibender/guibender
%{__install} -d %{buildroot}%{python_sitelib}/guibender/tests/images
%{__install} -d %{buildroot}%{python_sitelib}/guibender/examples/images
%{__install} -d %{buildroot}%{python_sitelib}/guibender/doc
%{__install} -t %{buildroot}%{python_sitelib}/guibender/doc doc/design_ideas.txt
%{__cp} -a guibender/* %{buildroot}%{python_sitelib}/guibender/guibender
%{__cp} -a tests/* %{buildroot}%{python_sitelib}/guibender/tests
%{__cp} -a examples/* %{buildroot}%{python_sitelib}/guibender/examples
# TODO: check whether the config and spec are needed
# TODO: perhaps move the doc/design ideas to %doc
%{__install} -t %{buildroot}%{python_sitelib}/guibender/ __init__.py guibender_old.py guibender.spec run_tests.sh


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE TODO.txt doc/Image\ Logging\ Tutorial.pdf
#%config guibender.cfg
#%ghost guibender.log
#%if 0%{?fedora} >= 9 || 0%{?rhel} >= 6
#  %{python_sitelib}/%{name}-%{version}-py?.?.egg-info
#%endif
# top level dir
%dir %{python_sitelib}/guibender
%{python_sitelib}/guibender/__init__.py
%{python_sitelib}/guibender/__init__.pyc
%{python_sitelib}/guibender/__init__.pyo
%{python_sitelib}/guibender/guibender.spec
%{python_sitelib}/guibender/guibender_old.py
%{python_sitelib}/guibender/guibender_old.pyc
%{python_sitelib}/guibender/guibender_old.pyo
%{python_sitelib}/guibender/run_tests.sh
%{python_sitelib}/guibender/guibender
%{python_sitelib}/guibender/tests
%{python_sitelib}/guibender/examples
%{python_sitelib}/guibender/doc

%changelog
* Mon Apr 13 2013 Plamen Dimitrov <pdimitrov@pevogam.com> - 0.10-1
- Initial spec file
