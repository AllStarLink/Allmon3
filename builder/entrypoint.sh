#!/bin/bash
set -e

#get DPKG_BUILDOPTS from env var or use default
OPTS=${DPKG_BUILDOPTS:-"-b -uc -us"}

if [ -f /etc/os-release ] ; then
  OS_CODENAME=$(cat /etc/os-release | grep "^VERSION_CODENAME=" | sed 's/VERSION_CODENAME=\(.*\)/\1/g')
elif [ command -v lsb_release ] ; then
  OS_CODENAME=$(lsb_release -a 2>/dev/null | grep "^Codename:" | sed 's/^Codename:\s*\(.*\)/\1/g')
elif [ command -v hostnamectl ] ; then
  OS_CODENAME=$(hostnamectl | grep "Operating System: " | sed 's/.*Operating System: [^(]*(\([^)]*\))/\1/g')
else
  OS_CODENAME=unknown
fi

set

for t in $BUILD_TARGETS; do
  echo "$t"
  cd /src/$t
  pwd
  BASENAME=$(head -1 debian/changelog | sed 's/^\([^ ]*\) (\([0-9]*:\)\?\([^)]*\)).*/\1_\3/g')
  cd ..
  mkdir -p build/$BASENAME
  mv *.deb build/$BASENAME
  mv *.build build/$BASENAME
  mv *.buildinfo build/$BASENAME
  mv *.changes build/$BASENAME
done
if [ "$(id -u)" -ne 0 ]; then chown -R user /src/*; fi
