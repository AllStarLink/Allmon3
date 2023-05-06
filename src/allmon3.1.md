% allmon3(1) allmon3 @@HEAD-DEVELOP@@
% Jason McCormick
% May 2023

# NAME
allmon3 - Monitor and communicate with AllStarLink Asterisk node

# SYNOPSIS
usage: allmon3 [-h] [--debug] [--version] [--config FILE] node 

Connect to an ASL Asterisk server and print rpt stats

positional arguments:
  node        Node ID

optional arguments:
  -h, --help  show this help message and exit
  --debug     enable debug-level logging output
  --version   get the version of the software
  --config    path to INI configuration for the node


# DESCRIPTION
**allmon3** polls against the AMI port of an Asterisk
node running app_rpt for AllStarLink and provides
a websocket connection for node status and voter
status. It also supports a command websocket to execute
commands on the AMI port.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.
