# Audio Player & Scheduler

## Setup and scope

Install the optional **allmon3-announcements-manager** package. Plain Allmon3
has no audio UI, worker, ffmpeg dependency, or timeout-recovery dependency.
The add-in registers through `/etc/allmon3/addons.d/announcements.ini`; the
core provides generic add-in loading, an asset manifest and per-node UI slots.
Only the optional package contains the announcements endpoints, assets and timer.

The add-in controls **local Asterisk nodes sharing Allmon3's filesystem**.
An authenticated user sees only local nodes allowed by existing restrictions.
The optional `local_nodes` list in `/etc/allmon3/announcements.ini` restricts
local nodes; it cannot turn a remote Asterisk host into a local filesystem.
Open Announcements from the selected node or the announcements panel.

```sh
sudo apt install allmon3-announcements-manager
```

This installs ffmpeg and **asl3-tts**, including its packaged Piper executable
and default Amy voice. There is no manual Python venv or package-script download.
The add-in invokes the packaged `/usr/bin/piper` in generation-only mode, not the
root/asterisk-only `asl-tts` playback wrapper. This permits unprivileged synthesis,
180ms sentence pauses and the queue's existing playback/timeout guards. Review
ASL3/Piper and individual voice model licenses before distributing extra models.

Settings live in root-owned INI files:

- `/etc/allmon3/announcements.ini`: upload/duration limits, segment/gap lengths,
  system or explicit IANA timezone, Friday publication cutoff, local-node filter,
  persistent configuration and cache directories.
- `/etc/allmon3/speech.ini`: `voice`, `model_dir`, `piper_bin`, `backend`, and bounded
  speech pace/volume/pause/gain/limiter settings.
  Default `backend=asl3` uses packaged Piper's CLI. `backend=python` supports an
  already-installed Python Piper runtime, but is not required by the package.

An existing `announcements.ini` must contain exactly `[announcements]`, without
`[DEFAULT]` or unrelated sections; invalid settings fail startup instead of
silently expanding the local-node filter or using default limits. Only an absent
file uses built-in defaults. `local_nodes` accepts positive node numbers.

To select Ryan after installing its model and matching JSON in `model_dir`, change
just `voice = en_US-ryan-medium`. Do not rename or overwrite stock voice files.
Validate with `sudo -u allmon3 python3 -m asl_allmon.speech`, then restart Allmon3
at audio idle. Never restart Asterisk for a voice change. Environment overrides
and hand-written service drop-ins from earlier PR previews should be migrated to
these INI files. Existing shared weather integrations can read the same profile;
the optional weather companion is not shipped by this PR.

The audio profile is frozen on first synthesis until restart. Model/JSON content
hashes and synthesis settings participate in both speech cache keys; different
voices never reuse old cached announcements. In-place model replacement requires
an idle restart too. A changed model cannot be rendered under its former cache key.
Missing dependencies fail before playback. Native Asterisk prompts and CW IDs,
uploaded media and downloaded recordings are not replaced by the voice selector.

AMI permissions must allow `rpt playback`, `rpt stats`, and `rpt cmd`. Asterisk
needs read/traverse access to `/var/cache/allmon3/audio` (directories 0755, audio
0644). Saved settings/schedules/originals live under `/etc/allmon3/audio`; only
this dedicated child directory is service-writable. Native settings are untouched.
The optional recovery timer is `allmon3-announcements-manager.timer`. Recovery
runs at add-in startup and through the independent timer; the base service has
no Requires/After dependency or ExecStartPre/ExecStopPost recovery commands.
Install/remove/upgrade the optional package only at audio idle. Removing it
restarts Allmon3, leaves saved configuration/media intact, and removes the add-in
UI/worker. A retained registration conffile for an absent package is ignored.

## Backups, restores and earlier preview versions

Debian provisions `/etc/allmon3/audio` as `allmon3:allmon3`, mode 0750. For a
manual installation, create it with:

```sh
sudo install -d -m 0750 -o allmon3 -g allmon3 /etc/allmon3/audio
```

`audio.sqlite3` (mode 0640) contains schedules, the master setting, library
metadata and job history; `audio-originals/` contains the source media needed by
saved stacks. These are runtime-created, not packaged conffiles. Back up the
**whole `/etc/allmon3` tree recursively**, including this directory and media.
Original uploads can be large; check backup capacity and do not exclude them.
Stop Allmon3 at idle before copying SQLite and originals, and keep it stopped
while restoring. Restore ownership to `allmon3:allmon3` on the audio subtree,
with directories 0750 and files 0640; do not make all of `/etc/allmon3` writable.
Review restored schedules, pending jobs and master enable before restarting:
normal scheduling/late-start rules still apply, so a restored enabled schedule
can transmit when due. Do not restore old timeout-ownership journals onto a
running or different radio; use the existing recovery procedure on the original
host before stopping/replacing it.

`/var/cache/allmon3` is disposable. Playback segments are rebuilt from saved
originals when first needed, preserving asset IDs referenced by schedules;
speech is regenerated by Piper. Missing originals cause a visible job failure
before playback, not silent omission. Restoring configuration does not install
ffmpeg/Piper or models; those setup requirements still apply.

Earlier unreleased versions of this PR used `/var/lib/allmon3/audio.sqlite3`
and `/var/lib/allmon3/audio-originals/`. They are **not automatically moved**.
At idle, stop Allmon3 and back up both the old and new directories. Before
restarting the updated version, copy the database and originals together into
`/etc/allmon3/audio/`, preserving their names and permissions. Do this only when
neither destination exists; if either exists, stop and reconcile the two data
sets rather than overwrite or merge them. Leave old files intact until the UI
library, schedules and master setting are verified. Do not move the sibling
`audio-tot/` recovery journal: both recovery entry points continue using its
original path. Existing converted caches can remain in place.

## Workflow

Expand **Audio Player & Scheduler**. The top panel contains node selection,
**Stack name / Announcement Text**, Queue, Pause/Resume, Stop, and current status.
The master checkbox is visible beside the expanded heading. The stack builder
and scheduler come next, followed by the library, bulletin sources, and history.

Upload MP3, WAV, FLAC, OGG, Opus, M4A, or AAC (at most 100 MB / 60 minutes).
Browser preview does not transmit. Queueing or a scheduled start **can transmit
on the selected radio and connected links**. Add files or current bulletin
sources to the ordered stack, then move/remove items as needed. An empty stack
cannot be saved: the selection field is flagged and focused.

Stack names are spoken as entered at the start and end of a successfully
completed job, not before every item. The default speech profile uses
`length_scale=1.25`, volume 0.8, 180ms sentence silence, and 4/3 gain followed by a 0.95 peak limiter.
Speech is converted to 8 kHz mono mu-law. Opening speech precedes **TOT disabled**;
closing speech precedes **TOT enabled**. Cancellation does not add a closing
announcement. Acronym/callsign pronunciation is determined by the entered text.

Each content file is split into segments of at most 150 seconds, with a configurable 15-second default
gap between dispatches. Pause interrupts the segment; Resume restarts that segment
(up to 150 seconds), not the entire stack. Stop cancels the selected node's current
and pending jobs, leaving future schedules intact. app_rpt COP 24 stops local
telemetry and may also interrupt other node announcements. Recovery failures
remain visible and block further playback until Stop/recovery succeeds.

## Scheduling and master enable

- **Once:** the server timezone shown beside the date/time field. API callers may
  also supply an explicit UTC offset. Nonexistent DST wall times are rejected.
- **Daily/weekly:** the same advertised server timezone. The default reads the
  system IANA timezone (UTC fallback); an explicit IANA name can be set in INI.
  Missing spring-forward times are skipped; fall-back times run once. New next-run
  calculations re-read the system zone. Restart and review schedules after an OS
  timezone change; an already-stored next timestamp remains an absolute instant.

Schedules and queued jobs persist. Starts more than five minutes late are marked
**missed** instead of replaying after downtime. This check also applies to jobs
already queued before restart. Removing a schedule prevents future starts; it
does not cancel an already queued or active job (use Stop/remove queued job).

The shared master **Enable audio playback** setting persists and starts enabled
on upgrade to preserve operation. Changing it requires access to every local
audio node. Turning it off **lets the current job finish and blocks new playback**:
pending jobs are cancelled, new queue requests and Resume are rejected, and
scheduled starts while off are skipped without catch-up. Saved schedules remain
and advance to their next run; the library and schedule editor remain usable.
Pause and Stop remain available. Re-enabling does not replay cancelled/missed jobs.

## News sources

Amateur Radio Newsline and ARRL Audio News are collected Friday after the configured cutoff (default 13:00 in the server timezone),
or on demand with Refresh. Publisher edition dates are checked. A source item
uses the latest verified expected edition at playback time; a dated library item
pins that exact file. If the current edition is unavailable, Piper says
**“Q S T. No new file is available this week.”** and the job continues as
**substituted**, recording the cause. Stale cached bulletins are not silently aired.

## Timeout recovery and limits

Playback temporarily disables the local app_rpt timeout with COP 8 after opening
speech and restores its previous enabled state with COP 7 after completion or
failure. A timer already disabled by the operator is left disabled. This does not
alter the configured timeout duration or any remote repeater timeout. These
commands may produce app_rpt TOTDIS/TOTENA announcements.

A durable, locked journal is written before protection is disabled. Each segment
has a finite lease (expected duration plus 30 seconds); an independent timer checks
expired leases every 15 seconds. The add-in recovers owned overrides at startup; graceful cancellation restores
them, and the independent timer handles expired leases after crashes. Recovery needs reachable Asterisk/AMI; failures retain the journal and
block new playback. A changed app_rpt system state delays recovery until the
original state returns, rather than altering another state's protection.

**Done** means command dispatch and elapsed calculated duration, not verified RF
reception or a confirmed Asterisk telemetry queue drain. Confirm actual unkeying,
linked audio, ID behavior, and remote timeout behavior before unattended use.
There is no automatic audio retention/purge policy; monitor available disk space.

## Regression tests

Tests use temporary stores and fake playback/AMI callbacks. They do not transmit.
With `aiohttp`, `websockets`, ffmpeg and ffprobe available:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --check web/addons/announcements/audio.js
```

The actual Piper synthesis test skips when the configured runtime/model is absent.
Select a different installed runtime/model through `/etc/allmon3/speech.ini`.

For the isolated browser checks:

```sh
npm install
npx playwright install chromium
npm run test:audio-ui
```

Optionally set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed Chromium binary.
All API routes are simulated; checks cover desktop/mobile layout, empty-stack
validation, Daily payloads, master control, Pause/Resume/Stop, and node selection.

## Existing ASL bulletin tool: integration question still open

`asl-play-arn` (also used for AAN) already downloads/converts/plays bulletins, but
its inspected CLI has no download-only/export mode. Calling it for Refresh or
browser preview would transmit; calling it inside this queue would bypass
segment control, cancellation and owned timeout recovery. The current add-in
therefore retains generation-only collection and freshness validation. This is
not presented as a resolved maintainer request: a reusable fetch-only helper/API
in ASL3, or agreement to reduce this add-in's bulletin scope, is still needed.
Do not invoke the transmitting tool as a fetch probe. Native speech unification
is likewise deferred to a separate design discussion.
