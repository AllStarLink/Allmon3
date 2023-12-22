#!/bin/bash

set -e

while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--check-changelog)
      CHECK_CHANGELOG=YES
      shift
      ;;
    -a|--architectures)
      ARCHS="$2"
      shift
      shift
      ;;
    -t|--targets)
      TARGETS="$2"
      shift
      shift
      ;;
    -r|--commit-versioning)
      COMMIT_VERSIONING=YES
      shift
      ;;
    -o|--operating-systems)
      OPERATING_SYSTEMS="$2"
      shift
      shift
      ;;
    -*|--*|*)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

if [ -z "$ARCHS" ]
then
  ARCHS="amd64 armhf arm64"
fi

if [ -z "$TARGETS" ]
then
  TARGETS="Allmon3"
fi

if [ -z "$OPERATING_SYSTEMS" ]
then
  OPERATING_SYSTEMS="buster"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ $BRANCH == "develop" ]; then
  REPO_ENV="-devel"
elif [ $BRANCH = "testing"]; then
  REPO_ENV="-testing"
else
  REPO_ENV=""
fi

echo "Architectures: $ARCHS"
echo "Targets: $TARGETS"
echo "Operating Systems: $OPERATING_SYSTEMS"
echo "PWD: $(pwd)"
echo `find . -print -maxdepth 1`

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "DIR: ${DIR}"
PDIR=$(dirname $DIR)
echo "PDIR: ${PDIR}"

exit 

#get the build targets
cd $PDIR
BUILD_TARGETS=""
ANYCOUNT=0
for t in $TARGETS; do
  if [ -z "$CHECK_CHANGELOG" ] || git diff --name-only HEAD HEAD~1 | grep -q $t/debian/changelog; then
    BUILD_TARGETS+="$t "
    c=$(grep "^Architecture:" $t/debian/control | egrep -v "^Architecture: ?all" | wc -l)
    ANYCOUNT=$((c+ANYCOUNT))
  fi
done
BUILD_TARGETS=$(echo "$BUILD_TARGETS" | xargs)


#if 'any' = 0, only run for one arch (there are no arch specific packages)
if [ "$ANYCOUNT" -eq "0" ] ; then
  set -- $ARCHS
  ARCHS=$1
fi

#run --build=any for following arch's after the first to prevent re-creating 'all' packages
DPKG_BUILDOPTS="-b -uc -us"
for A in $ARCHS; do
  if [ "$A" == "armhf" ]; then
    DA="arm32v7"
  elif [ "$A" == "arm64" ]; then
    DA="arm64v8"
  else
    DA="$A"
  fi
  for O in $OPERATING_SYSTEMS; do
       docker build -f $DIR/Dockerfile -t allmon3_builder.$O.$A$REPO_ENV --build-arg ARCH="$DA" --build-arg OS="$O" --build-arg ASL_REPO="asl_builds${REPO_ENV}" --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) $DIR
       docker run -v $PDIR:/src -e DPKG_BUILDOPTS="$DPKG_BUILDOPTS" -e BUILD_TARGETS="$BUILD_TARGETS" -e COMMIT_VERSIONING="$COMMIT_VERSIONING" allmon3_builder.$O.$A$REPO_ENV
       docker image rm --force allmon3_builder.$O.$A$REPO_ENV
       DPKG_BUILDOPTS="--build=any -uc -us"
  done
done
