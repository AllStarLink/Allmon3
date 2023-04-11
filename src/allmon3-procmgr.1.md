% allmon3-procmgr(1) allmon3-procmgr @-DEVELOP@@
% Jason McCormick
% April 2023

# NAME
allmon3-procmgr - Manage the users table for Allmon3

# SYNOPSIS
usage: allmon3-procmgr [-h] [--config CONFIG] [--debug] [--version] command

Managed all systemd services in one block

positional arguments:
  command          command to execute: start, stop, restart, enable, disable,
                   purge

optional arguments:
  -h, --help       show this help message and exit
  --config CONFIG  path to INI configuration for the node(s); default
                   /etc/allmon3/allmon3.ini
  --debug          enable debug-level logging output
  --version        get the version of the software

# COMMANDS
**start** - Start the asl-statmon(1) and asl-cmdlink(1) processes for all
nodes in `/etc/allmon3/allmon3.ini` or `--file FILE`

**stop** - Same a start but in reverse

**restart** - Issues a stop then start as detailed above

**enable** - Enable the unit @instance files for asl-statmon(1) and 
asl-cmdlink(1) for all nodes in `/etc/allmon3/allmon3.ini` or `--file FILE`
but does not start them.

**disable** - The opposite of enable

**purge** - Forcible stop, nuke, and unregister all unit files matching
the pattern of asl-\* regardless of any configuration file

# DESCRIPTION
**allmon3-procmgr**  manages the systemc instance units
for asl-statmon(1) and asl-cmdlink(1)

# BUGS
Report bugs to https://github.com/AllStarLink/Allmon3/issues

# COPYRIGHT
Copyright (C) 2023 Jason McCormick and AllStarLinux
under the terms of the AGPL v3.




