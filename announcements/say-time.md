# Local time announcements with the shared Piper voice

`allmon3-say-time` uses `/etc/allmon3/speech.ini`, just like weather and
announcement speech. It says the host's current local time in 12-hour form,
with AM/PM, and converts it to 8 kHz mono mu-law with the shared speech filter.
No weather lookup or other network service is used. Missing/malformed settings
or a failed synthesis cause an error; there is no silent recorded-prompt fallback.

Enable only local Asterisk node numbers in `/etc/allmon3/time.ini`:

```ini
[time]
nodes = 1000
```

The default is disabled (empty node list). The node must also appear in live
`rpt localnodes` before playback. The time zone comes from the operating system,
not the browser. A synthesis that crosses a minute boundary is retried once;
if still stale it is not dispatched. Asterisk queue delays are not a clock
synchronization guarantee.

```sh
allmon3-say-time --node 1000               # text only; no playback
allmon3-say-time --node 1000 --render /tmp/time.ulaw  # synthesis only
allmon3-say-time --node 1000 --play        # local radio playback
```

**Local-only means `rpt localplay`: it may key the local transmitter but does
not send the announcement to linked nodes.** Automatic telemetry, CW IDs,
recorded prompts, and DTMF time commands are unchanged. The helper does not
modify transmitter timeouts or stop an existing announcement. One helper per
node may run at once. Time audio older than an hour is removed on later runs;
long Asterisk queue delays beyond that retention window are not supported.

## Allmon3 menu

Create a root-owned executable wrapper for each enabled node (replace 1000
consistently). Do not let web users edit executable helpers:

```sh
#!/bin/sh
cd /
exec /usr/bin/allmon3-say-time --node 1000 --play
```

Save it as `/usr/local/lib/allmon3-time/say-time-1000`, mode0755. Add this
node-scoped command to `web.ini`:

```ini
[syscmds-1000]
rpt cmd @ cmd /usr/local/lib/allmon3-time/say-time-1000 = Say Time of Day (local only)
```

To replace the stock menu entry rather than duplicate it, remove
`rpt cmd @ status 12 xxx = Say Time of Day (local only)` from `[syscmds]`.
Retain the native entry in per-node sections for remote/unconfigured nodes.
Back up `web.ini`, check active work, and restart only Allmon3 when idle.
Do not restart Asterisk. Rollback restores the original menu entry and removes
the helper's menu entry. Retain the existing voice and native prompts.

## Verification

Unit tests cover time formatting, timezone/DST boundaries, node restrictions,
text/render modes without playback, local-only command construction, stale
minute retries and dispatch failures. Render-only output must also be decoded
with FFmpeg as the Asterisk user. These checks do not prove RF audio reception.
