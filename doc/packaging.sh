#!/bin/sh

DEVPATH=/g8diff/0.projects
DEVFOLDER=3T2.3.guibender
VERSION=0.10
RPMBUILD=~/rpmbuild
RPMDEST=/tmp

# In order to produce new rpm please do the following:
# 1) rename the main folder to guibender-0.10-1 using the version you would like
#    -> it also has to be inserted in the SPEC file
# 2) tar czvf ~/rpmbuild/SOURCES/guibender-0.10.tar.gz guibender-0.10 --exclude=.git --exclude=packages --exclude=*.pyc
#    -> exclude any extra unwanted packages
#    -> this assumes ~/rpmbuild/SOURCES exists - if you use a different rpmbuild configuration correct it
#    -> you have to be at path-to-guibender/..
# 3) rename the main folder back to whatever it was
# 4) rpmbuild -ba path-to-guibender/guibender.spec
# This script does this for you just in case but you still have to set the variables right and set the version in the SPEC file.

mv $DEVPATH/$DEVFOLDER $DEVPATH/guibender-$VERSION
tar czvf $RPMBUILD/SOURCES/guibender-$VERSION.tar.gz -C $DEVPATH/ guibender-$VERSION --exclude=.git --exclude=packages --exclude=*.pyc
mv $DEVPATH/guibender-$VERSION $DEVPATH/$DEVFOLDER
rpmbuild -ba $DEVPATH/$DEVFOLDER/guibender.spec
cp $RPMBUILD/RPMS/x86_64/guibender-* $RPMDEST

# NOTE: Please don't use this script to test an rpmbuild or similar. The use case in mind is only if you make changes to some of the
# guibender files and wish to have them immediately put in an RPM (version change is not expected to break the rpmbuild).