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

for t in $BUILD_TARGETS; do
  echo "$t"
  cd /src/$t
  pwd
  COMMIT_VERSION=""
  if [ "${COMMIT_VERSIONING^^}" == "YES" ] ; then
    COMMIT_VERSION=$(git show --date=format:'%Y%m%dT%H%M%S' --pretty=format:"+git%cd.%h" --no-patch)
  fi
  if [ "$t" == "asterisk" ]; then
    make clean
    ./bootstrap.sh && ./configure
  fi
  #temporarily add OS_CODENAME to the package version
  mv debian/changelog debian/changelog.bkp
  cat debian/changelog.bkp | sed "s/^\([^ ]* (\)\([^)]*\)\().*\)$/\1\2~${OS_CODENAME}${COMMIT_VERSION}\3/g" > debian/changelog
  debuild $OPTS
  mv debian/changelog.bkp debian/changelog
  BASENAME=$(head -1 debian/changelog | sed 's/^\([^ ]*\) (\([0-9]*:\)\?\([^)]*\)).*/\1_\3/g')
  cd ..
  mkdir -p build/$BASENAME
  mv *.deb build/$BASENAME
  mv *.build build/$BASENAME
  mv *.buildinfo build/$BASENAME
  mv *.changes build/$BASENAME
done
if [ "$(id -u)" -ne 0 ]; then chown -R user /src/*; fi
