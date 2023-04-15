% asl-votermon-client(1) asl-client-votermon @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
asl-votermon-client - monitor the output of an asl-votermon ZMQ port

# SYNOPSIS
usage: asl-votermon-client [-h] [--topic TOPIC] host port

Simple client to see that an asl-votermon instance. Dumps 0MQ messages from the
specified port

positional arguments:
  host           FQDN or IP address of the asl-votermon to test
  port           TCP port of asl-votermon to test

optional arguments:
  -h, --help     show this help message and exit
  --topic TOPIC  Topic to subscribe to
_
# DESCRIPTION
**asl-votermon-client** simply listens to an asl-votermon(1)
ZMQ port and prints all output. Terminate with ^c.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.

