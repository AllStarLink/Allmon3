% allmon3(1) allmon3 @@HEAD-DEVELOP@@
% Jason McCormick
% May 2023

# NAME
allmon3 - Monitor and communicate with AllStarLink Asterisk node

# SYNOPSIS
usage: allmon3 [-h] [\-\-nodes NODES] [\-\-config CONFIG]
 [\-\-webconfig WEBCONFIG] [\-\-menuconfig MENUCONFIG] [\-\-favoritesconfig FAVORITESCONFIG]
 [\-\-debug] [\-\-version]

Connect to an ASL Asterisk server and print rpt stats

positional arguments:
  node        Node ID

optional arguments:
  -h, \-\-help  show this help message and exit

  \-\-nodes NODES         Only start the node(s) listed as \-\-node NODE[,NODE,...]

  \-\-config CONFIG       path to INI configuration allmon3 nodes (default /etc/allmon3/allmon3.ini)

  \-\-webconfig WEBCONFIG path to INI configuration for web services (default /etc/allmon3/web.ini

  \-\-menuconfig MENUCONFIG path to INI configuration for menus (default /etc/allmon3/menu.ini

  \-\-favoritesconfig FAVORITESCONFIG path to writable JSON storage for link favorites (default `/etc/allmon3/favorites/favorites.json`)

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
Copyright (C) 2023 Jason McCormick and AllStarLink
under the terms of the AGPL v3.

# FAVORITES SYNCHRONIZATION

Favorites are stored under `/etc/allmon3/favorites`. A recursive backup of
`/etc/allmon3` includes them; merely storing them under `/etc` does not add them
to a backup tool's explicit include list. For `asl-backup-menu` or WebUI, check
`/var/asl-backups/asl-backup-files` and add `/etc/allmon3/favorites` if neither it
nor its parent is listed. Preserve other include-list entries and back up
`/etc/allmon3/web.ini` for the group configuration. Stop Allmon3 while backing
up/restoring, install the package before restoring its writable directory, and
verify the restored favorites before restarting.
The service account needs write access only to `/etc/allmon3/favorites` for the
lock file and atomic JSON replacement, not to the parent configuration directory.
The Debian package provisions this subdirectory with owner `allmon3:allmon3` and
mode `0750`. Manual installations must provision it for their service account.
Custom `--favoritesconfig` paths must be included separately in backups.

The optional `[favorites-groups]` section of `web.ini` maps group names to
comma-separated managed node IDs, for example `station = 1999,2000`.
Each node may belong to one group. After restarting Allmon3, additions,
edits and deletions on any member propagate atomically to every member.
Ungrouped nodes remain independent; separate Allmon3 servers are not replicated.
Users require access to every group member for favorites reads and writes.
Existing entries merge on startup; conflicting names stop startup without
modifying storage. Resolve conflicts before enabling a group. Removing a group
retains the last synchronized copies. No radio command is dispatched.
