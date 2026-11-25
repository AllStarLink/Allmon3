# Logs & Connection Logging

The logged-in sidebar opens a collapsible log panel. This feature is independent of
Audio Player & Scheduler and named Favorites.

## Available views

- **Connection history (`/var/log/asterisk/connectlog`)**: selected local node's
  records, with independent enable/disable recording switches for configured nodes.
- **Asterisk messages (`/var/log/asterisk/messages.log`)**: shared diagnostics.
  Viewing this requires permission on **every local node configured in Allmon3**.
  It is not a per-node log; connection switches do not turn off Asterisk messages.

Choose the recent-line count (100–1,000), refresh, optionally auto-refresh every five
seconds while the panel is open and the page visible, search displayed lines, or
save the shown lines as plain text. Reads are limited to the latest 256 KiB of the
current file. Rotated archives are not included in this first version.

Connection records contain an ISO timestamp/UTC offset, event, local node and
remote node. No audio is recorded. These hooks do not identify individual RF users,
do not capture every failed attempt, and may omit shutdown disconnects. The message
log can contain available retry/failure notices but is not a complete connection audit.

## Local-node setup (opt-in)

This feature only reads this server's files. Remote nodes are never made local by
an override. The package does not edit Asterisk radio configuration, install hooks
into `rpt.conf`, or restart Asterisk. Register a node for controls only after its
hooks are configured. Defaults expose no connection switches.

1. Back up your Asterisk configuration. For each **local** node to log, add these
   settings to its existing `rpt.conf` stanza (not a new duplicate section):

   ```ini
   connpgm = /usr/lib/allmon3/connection-log CONNECT
   discpgm = /usr/lib/allmon3/connection-log DISCONNECT
   ```

   If these hooks already run your own programs, preserve/chain that behavior
   intentionally instead of replacing it. AllStar app_rpt supplies the local and
   remote node arguments after the event argument. Apply the configuration using
   your installation's supported reload procedure; do not interrupt active links
   merely to test logging.

2. Create the metadata log, preserving any existing history:

   ```sh
   sudo install -d -o asterisk -g asterisk -m 0775 /var/log/asterisk
   sudo touch /var/log/asterisk/connectlog
   sudo chown asterisk:asterisk /var/log/asterisk/connectlog
   sudo chmod 0640 /var/log/asterisk/connectlog
   ```

3. Declare the local nodes with installed hooks in `/etc/allmon3/logging-nodes.json`:

   ```json
   {"nodes": ["1999", "2000"]}
   ```

   Replace these examples with your actual node numbers. The manifest is intersected
   with locally hosted nodes in Allmon3 configuration; listing a remote node does
   not enable it. Restart **Allmon3**, then refresh the browser and log in.

4. Ensure exactly one logrotate policy covers `connectlog`. A sample is installed
   at `/usr/share/doc/allmon3/allmon3-connectlog.logrotate`. If no existing policy
   covers it, install this example under `/etc/logrotate.d/` and validate it with
   `logrotate --debug`. It rotates weekly, retains 52 archives and compresses old
   logs. The sample is opt-in because Allmon3 may run on a host without Asterisk.

Recording switches take effect on the next hook invocation, with no Asterisk restart
or reload. Turning recording off preserves existing history but future events while
disabled are not reconstructed. Flags persist across Allmon3 restarts. The hook
uses enabled as its fallback if the optional settings are missing/corrupt, avoiding
silent loss of history; malformed settings are reported as an error by the UI.

## Permissions and installation details

- Existing authenticated sessions and node restrictions protect all endpoints.
  Connection read/toggle permission is per node, not tied to Favorites groups.
- Browser changes use same-origin JSON. Server-side validation restricts identifiers,
  boolean settings and read sizes. Log contents use text rendering, never HTML.
- The packaged `/usr/lib/allmon3/log-reader` reads only the two fixed log paths.
  It rejects symlinks/non-regular files and reads a bounded tail. It accepts no
  arbitrary paths or commands. Sudoers permits Allmon3 to run this reader as
  **asterisk**, never root; Allmon3 is not added to the asterisk group.
- Preferences: `/etc/allmon3/logging/nodes.json`, mode0644 in a mode0755 directory
  owned by allmon3. This holds only boolean flags, no credentials. Writes use a
  stable lock, atomic replacement and fsync. The hook account has read-only access.
- Debian installs the module, JS, helpers, sudoers rule and empty manifest; postinst
  creates the flag directory and validates sudoers. It does not download anything.
- For a non-Debian `make install`, the administrator must provision the allmon3 and
  asterisk accounts as appropriate, create the flag directory with the ownership
  above, install/validate sudo, and configure the hooks explicitly. Asterisk may
  be absent on remote-monitor-only hosts; do not activate local logging there.

The viewer does not clear/delete logs, execute link commands, queue audio or transmit.
Access to the host-wide messages log intentionally grants visibility of all messages
in that file, including lines with no identifiable local node.

## Configuration backups and earlier preview versions

Recording preferences now live alongside the node configuration, so recursive
backups of `/etc/allmon3` preserve the switches and `logging-nodes.json` manifest.
The JSON is runtime-created, not a packaged conffile. Log history itself remains
in `/var/log/asterisk`; back it up separately if needed. Only the dedicated
`/etc/allmon3/logging` directory is service-writable. For manual installations:

```sh
sudo install -d -m 0755 -o allmon3 -g allmon3 /etc/allmon3/logging
```

Keep `/etc/allmon3` traversable by the Asterisk hook (normally 0755), without
making it writable by the hook or Allmon3. Preferences are 0644 and contain only
boolean flags; credential-file permissions are unchanged. Stop Allmon3 while
backing up/restoring preferences, restore their `allmon3:allmon3` ownership and
permissions, then restart. The hook reads the file on each event; during a
missing-file restore interval it defaults to recording, so coordinate restores
at idle if precise logging gates are required. No Asterisk restart is needed.

Earlier unreleased versions used `/var/lib/allmon3-log-settings/nodes.json`.
There is no automatic migration. Stop Allmon3, back up both locations, provision
the new directory, then copy the old file only if the new one does not exist:

```sh
sudo sh -ec 'test ! -e /etc/allmon3/logging/nodes.json &&
    test ! -L /etc/allmon3/logging/nodes.json &&
    install -m 0644 -o allmon3 -g allmon3 /var/lib/allmon3-log-settings/nodes.json /etc/allmon3/logging/nodes.json'
```

Keep the old file until the switches and hook behavior are verified. If both
files already exist, review them instead of overwriting. Update the installed
connection hook together with the server; both must read the same new path.

## Tests

From the repository root, using a disposable virtual environment:

```sh
python3 -m venv /tmp/allmon3-log-tests
/tmp/allmon3-log-tests/bin/pip install -r tests/requirements-logs.txt
/tmp/allmon3-log-tests/bin/python -m pytest -q tests/test_logs.py
/tmp/allmon3-log-tests/bin/python tests/check_browser.py
```

The browser test uses a local Chromium if available (or `CHROMIUM_PATH`), otherwise
install Playwright's Chromium in the test environment with `playwright install chromium`.
It serves a synthetic panel/API and does not connect to a radio or production node.
Unit tests use temporary files and fake sessions, including HTTP permission-denial cases.
