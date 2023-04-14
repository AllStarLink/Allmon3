% asl-votermon(1) asl-votermon @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
asl-votermon - Monitor ASL Asterisk server for  voter info

# SYNOPSIS
usage: asl-votermon [-h] [--debug] [--version] [--config] node

Connect to an ASL Asterisk server and print voter info

positional arguments:
  node        Node ID

optional arguments:
  -h, --help  show this help message and exit
  --debug     enable debug-level logging output
  --version   get the version of the software
  --config      path to INI configuration for the node - default /etc/allmon3/voter.ini

# DESCRIPTION
**asl-votermon** is a polling damon against an Asterisk 
instance on the AMI port and returns status information
about voter functions on its ZMQ port as a publication
message. This script is only useful for AllStarLink Asterisk.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.
