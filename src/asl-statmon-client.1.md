% asl-statmon-client(1) asl-client-statmon @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
asl-statmon-client - monitor the output of an asl-statmon ZMQ port

# SYNOPSIS
usage: asl-statmon-client [-h] [--topic TOPIC] host port

Simple client to see that an asl-statmon instance. Dumps 0MQ messages from the
specified port

positional arguments:
  host           FQDN or IP address of the asl-statmon to test
  port           TCP port of asl-statmon to test

optional arguments:
  -h, --help     show this help message and exit
  --topic TOPIC  Topic to subscribe to
_
# DESCRIPTION
**asl-statmon-client** simply listens to an asl-statmon(1)
ZMQ port and prints all output. Terminate with ^c.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.

