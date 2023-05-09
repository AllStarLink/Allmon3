% allmon3-status-client(1) asl-client-statmon @HEAD-DEVELOP@@
% Jason McCormick
% Mary 2023

# NAME
allmon3-status-client - monitor the output of an asl-statmon ZMQ port

# SYNOPSIS
usage: allmon3-status-client [-h] [\-\-node NODE] host port

Simple client to see that an asl-statmon instance. Dumps 0MQ messages from the
specified port

positional arguments:
  host           FQDN or IP address of the asl-statmon to test
  port           TCP port of asl-statmon to test

optional arguments:
  -h, \-\-help     show this help message and exit
  \-\-node NODE  Topic to subscribe to
_
# DESCRIPTION
**allmon3-status-client** simply listens to an allmon3
on the status broadcast websocket port and prints
all output, moderated by \-\-node if specified.
Terminate with ^c.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.

