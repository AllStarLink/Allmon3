% asl-statmon(1) asl-statmon @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
asl-statmon - Monitor ASL Asterisk server for events

# SYNOPSIS
usage: asl-statmon [-h] [--debug] [--version] node config

Connect to an ASL Asterisk server and print rpt stats

positional arguments:
  node        Node ID
  config      path to INI configuration for the node

optional arguments:
  -h, --help  show this help message and exit
  --debug     enable debug-level logging output
  --version   get the version of the software

# DESCRIPTION
**asl-statmon** is a polling damon against an Asterisk 
instance on the AMI port and returns status information
about app_rpt functions on its ZMQ port as a publication
message. This script is only useful for AllStarLink Asterisk.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.
