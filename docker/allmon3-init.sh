#!/usr/bin/bash

export DEBIAN_FRONTEND=noninteractive

# install the repo
apt update
apt upgrade -y
apt install -y wget
wget https://repo.allstarlink.org/public/asl-apt-repos.deb13_all.deb
dpkg -i asl-apt-repos.deb13_all.deb
apt update

# install
apt install -y allmon3