#!/bin/bash

set -e

while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--check-changelog)
      CHECK_CHANGELOG=YES
      shift
      ;;
    -a|--architecture)
      ARCH="$2"
      shift
      shift
      ;;
    -t|--targets)
      TARGETS="$2"
      shift
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

if [ -z "$ARCH" ]
then
  ARCH="all"
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

echo "Architectures: $ARCH"
echo "Targets: $TARGETS"
echo "Operating Systems: $OPERATING_SYSTEMS"
echo "PWD: $(pwd)"
echo `find . -print -maxdepth 1`

echo "BS: ${BASH_SOURCE[0]}"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "DIR: ${DIR}"
PDIR=$(dirname $DIR)
echo "PDIR: ${PDIR}"

DPKG_BUILDOPTS="-b -uc -us"
D_TAG="allmon3_builder.${OPERATING_SYSTEMS}.${ARCH}${REPO_ENV}"

docker build -f $DIR/Dockerfile -t $D_TAG \
	--build-arg ARCH="$ARCH" \
	--build-arg OS="$OPERATING_SYSTEMS" \
	--build-arg ASL_REPO="asl_builds${REPO_ENV}" \ 
	--build-arg USER_ID=$(id -u) \
	--build-arg GROUP_ID=$(id -g) \
	$DIR

docker run -v $PDIR:/src \
	-e DPKG_BUILDOPTS="$DPKG_BUILDOPTS" \
	-e BUILD_TARGETS="$BUILD_TARGETS" \
	$D_TAG

docker image rm --force $D_TAG
