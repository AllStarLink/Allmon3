% allmon3-gen-voterconf(1) allmon3-gen-voterconf @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
allmon3-gen-voterconf - Generate Apache configs for the voter WebSockets

# SYNOPSIS
usage: allmon3-gen-voterconf [-h] [--config CONFIG] [--debug] [--version]

Generate apache configuration for the voter websockets

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  path to INI configuration for the node
  --debug          enable debug-level logging output
  --version        get the version of the software

# DESCRIPTION
This outputs an Apache 2.4-compatible set of configuration directives
to configure Apache for all defined voters in voter.ini. Insert
these into Apache's configuration and restart the server.

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.




