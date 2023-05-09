% allmon3-cmd-client(1) allmon3-cmd-client @HEAD-DEVELOP@@
% Jason McCormick
% May 2023

# NAME
allmon3-cmd-client - Connect to an ASL Asterisk server and issue commands

# SYNOPSIS
usage: allmon3-cmd-client [-h] host port passwd cmd

Simple client to asl-cmdlink

positional arguments:
  host        FQDN or IP address of the asl-cmdlink to test
  port        TCP port of asl-cmdlink to test
  passwd      ASL/AMI manager password
  cmd         Command to execute enclosed in double quotes

optional arguments:
  -h, \-\-help  show this help message and exit

# DESCRIPTION
**allmon3-cmd-client** executes an AMI command 
via an allmon3 port and returns
the information. This script is only useful for
AllStarLink Asterisk.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.


