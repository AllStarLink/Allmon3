% allmon3-voter-client(1) allmon3-voter-client @HEAD-DEVELOP@@
% Jason McCormick
% May 2023

# NAME
allmon3-voter-client - Connect to an ASL Asterisk server and issue commands

# SYNOPSIS
usage: allmon3-voter-client [-h] host port passwd 

Simple client to asl-voterlink

positional arguments:
  host        FQDN or IP address of the asl-voterlink to test
  port        TCP port of asl-voterlink to test
  passwd      ASL/AMI manager password

optional arguments:
  -h, --help  show this help message and exit

# DESCRIPTION
**allmon3-voter-client** executes polls the
AMI port for voter status and returns the
information. This script is only useful for
AllStarLink Asterisk.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.


