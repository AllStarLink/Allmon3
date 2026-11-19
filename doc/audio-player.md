# Audio Player & Scheduler

## Setup and scope

This feature controls **local Asterisk nodes that share Allmon3's filesystem**.
It does not copy audio to remote nodes. Authenticated users see only local nodes
allowed by their existing node restrictions. Set `AUDIO_LOCAL_NODES=1999,2000`
in the `[web]` section of `/etc/allmon3/web.ini` only when automatic detection
misses nodes on this same host (for example, an AMI connection using a LAN IP).
An explicit entry is an operator assertion of shared storage, not file delivery.
Restart Allmon3 after changing it.

Requirements: Python 3.11+, ffmpeg/ffprobe, and local Piper TTS. AMI credentials
must permit the CLI commands used by `rpt playback`, `rpt stats`, and `rpt cmd`.
Asterisk needs read/traverse access to `/var/cache/allmon3/audio/`; converted
files are mode 0644 under directories mode 0755. Source uploads, SQLite state,
and timeout-recovery journals live under `/var/lib/allmon3/`.

The Debian package installs ffmpeg and the recovery units, but **does not download
speech models or install Python packages from the network during installation**.
Install Piper separately before queueing any stack. One tested setup is:

```sh
sudo apt install python3-venv
sudo python3 -m venv /opt/allmon3-piper
sudo /opt/allmon3-piper/bin/pip install 'piper-tts==1.8.0'
sudo install -d -m 0755 /opt/allmon3-piper/voices
cd /opt/allmon3-piper/voices
sudo /opt/allmon3-piper/bin/python -m piper.download_voices en_US-lessac-medium
```

Review [Piper's installation documentation](https://github.com/OHF-Voice/piper1-gpl)
and the [Lessac model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD).
Piper is GPL-licensed; voice models have their own licensing. No runtime/model
binaries are bundled in this repository. Ensure the service account can execute
Piper and read both the `.onnx` and matching `.onnx.json` files.

For a different installation location or voice, create a systemd drop-in using
`systemctl edit allmon3`:

```ini
[Service]
Environment=ALLMON3_PIPER_BIN=/opt/allmon3-piper/bin/piper
Environment=ALLMON3_PIPER_MODEL=/opt/allmon3-piper/voices/en_US-lessac-medium.onnx
```

Then reload systemd and restart Allmon3 while playback is idle. Manual source
installations can export the same environment variables. Voice paths participate
in the speech cache identity; if replacing a model in place, clear the generated
speech cache at idle or use a new model path. No cloud TTS or eSpeak fallback is
used. Missing speech dependencies fail the job before any audio is dispatched.

Source installations also need both `allmon3-audio-tot-recovery.*` units from
`debian/` installed under the system's systemd unit directory and the timer
started. The packaged Allmon3 unit requires this timer and runs recovery before
startup and after shutdown. Preserve these hooks when customizing the service.

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
completed job, not before every item. The medium-slow Lessac profile uses
`length_scale=1.25`, Piper volume 0.8, and 4/3 gain followed by a 0.95 peak limiter.
Speech is converted to 8 kHz mono mu-law. Opening speech precedes **TOT disabled**;
closing speech precedes **TOT enabled**. Cancellation does not add a closing
announcement. Acronym/callsign pronunciation is determined by the entered text.

Each content file is split into segments of at most 150 seconds, with a five-second
gap between dispatches. Pause interrupts the segment; Resume restarts that segment
(up to 150 seconds), not the entire stack. Stop cancels the selected node's current
and pending jobs, leaving future schedules intact. app_rpt COP 24 stops local
telemetry and may also interrupt other node announcements. Recovery failures
remain visible and block further playback until Stop/recovery succeeds.

## Scheduling and master enable

- **Once:** browser-local date/time, sent to the server with a UTC offset.
- **Daily:** a Pacific (`America/Los_Angeles`) wall-clock time each day. The missing
  spring-forward time is skipped; the repeated fall-back time runs once.
- **Weekly:** weekday and time in Pacific time.

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

Amateur Radio Newsline and ARRL Audio News are collected Friday after 1 PM Pacific,
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
expired leases every 15 seconds. Startup and shutdown hooks also recover owned
overrides. Recovery needs reachable Asterisk/AMI; failures retain the journal and
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
python3 -m unittest discover -s tests -v
node --check web/js/audio.js
```

The actual Piper synthesis test skips when the configured runtime/model is absent.
Set `ALLMON3_PIPER_BIN` and `ALLMON3_PIPER_MODEL` to test a different installation.

For the isolated browser checks:

```sh
npm install
npx playwright install chromium
npm run test:audio-ui
```

Optionally set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to an installed Chromium binary.
All API routes are simulated; checks cover desktop/mobile layout, empty-stack
validation, Daily payloads, master control, Pause/Resume/Stop, and node selection.
