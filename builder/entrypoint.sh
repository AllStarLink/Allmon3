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

echo "OS_CODENAME: ${OS_CODENAME}"
cd /build/Allmon3

case $OS_CODENAME in
	buster)
		echo 10 > debian/compat
		mv debian/control.d10 debian/control
	;;
	bullseye)
		echo 11 > debian/compat
	;;
	bookworm)
		echo 12 > debian/compat
	;;
	*)
		echo 13 > debian/compat
	;;
esac

export EMAIL="AllStarLink <autobuild@allstarlink.org>"
make docker-deb DPKG_BUILDOPTS="${OPTS}" RELPLAT=$OS_CODENAME
[ ! -d _debs ] && mkdir _debs
rm -f _debs/*
cp ../*.deb _debs/
