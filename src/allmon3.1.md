% allmon3(1) allmon3 0.11.6
% Jason McCormick
% May 2023

# NAME
allmon3 - Monitor and communicate with AllStarLink Asterisk node

# SYNOPSIS
usage: allmon3 [-h] [\-\-nodes NODES] [\-\-config CONFIG]
 [\-\-webconfig WEBCONFIG] [\-\-menuconfig MENUCONFIG] [\-\-debug] [\-\-version]

Connect to an ASL Asterisk server and print rpt stats

positional arguments:
  node        Node ID

optional arguments:
  -h, \-\-help  show this help message and exit

  \-\-nodes NODES         Only start the node(s) listed as \-\-node NODE[,NODE,...]

  \-\-config CONFIG       path to INI configuration allmon3 nodes (default /etc/allmon3/allmon3.ini)

  \-\-webconfig WEBCONFIG path to INI configuration for web services (default /etc/allmon3/web.ini

  \-\-menuconfig MENUCONFIG path to INI configuration for menus (default /etc/allmon3/menu.ini

  \-\-version   get the version of the software


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
