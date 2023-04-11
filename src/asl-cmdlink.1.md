% asl-cmdlink(1) asl-cmdlink @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
asl-cmdlink - Connect to an ASL Asterisk server and issue commands

# SYNOPSIS
usage: asl-cmdlink [-h] [--debug] [--version] node config

Connect to an ASL Asterisk server and issue commands

positional arguments:
  node        Node ID
  config      path to INI configuration for the node

optional arguments:
  -h, --help  show this help message and exit
  --debug     enable debug-level logging output
  --version   get the version of the software

# DESCRIPTION
**asl-cmdlink** takes input commands on its ZMQ message
bus port, executes them on an Asterisk instance 
via AMI, and returns the output of the command.
This script is only useful for AllStarLink Asterisk.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.


