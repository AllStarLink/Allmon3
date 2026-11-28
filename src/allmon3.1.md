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

  \-\-favoritesconfig FAVORITESCONFIG path to writable JSON storage for link favorites (default `/etc/allmon3/favorites.json`)

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

Favorites are stored in `/etc/allmon3/favorites.json`. A recursive backup of
`/etc/allmon3` includes the file; merely storing it under `/etc` does not add it
to a backup tool's explicit include list. For `asl-backup-menu` or WebUI, check
`/var/asl-backups/asl-backup-files` and add `/etc/allmon3/favorites.json` if neither
it nor its parent is listed. Preserve other entries and back up
`/etc/allmon3/web.ini` for group configuration. Stop Allmon3 during backup/restore
and verify restored favorites before restarting.

Atomic saves need directory write access for the lock and temporary files.
The package provisions `/etc/allmon3` as `root:allmon3`, mode `1775`. The sticky
bit protects root-owned entries against service rename/deletion; existing file
permissions are not broadened recursively. Restore the JSON (and lock, if
included) with owner `allmon3:allmon3`, mode `0640`, and reapply the directory
ownership/mode before restarting. Manual installations need the same setup.
Custom `--favoritesconfig` paths remain supported and need separate backup coverage.

Earlier PR paths `/etc/allmon3/favorites/favorites.json` and
`/var/lib/allmon3/favorites.json` are not automatically migrated. Stop the service,
back up the old file and copy it only when the new destination does not exist;
retain the original until verified. See the README for the guarded copy command.
Never overwrite a newer destination or silently merge conflicting copies.

The optional `[favorites-groups]` section of `web.ini` maps group names to
comma-separated managed node IDs, for example `station = 1999,2000`.
Each node may belong to one group. After restarting Allmon3, additions,
edits and deletions on any member propagate atomically to every member.
Ungrouped nodes remain independent; separate Allmon3 servers are not replicated.
Users require access to every group member for favorites reads and writes.
Existing entries merge on startup; conflicting names stop startup without
modifying storage. Resolve conflicts before enabling a group. Removing a group
retains the last synchronized copies. No radio command is dispatched.
