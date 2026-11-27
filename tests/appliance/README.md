# Disposable optional-package lifecycle validation

## Recorded result (2026-11-27)

All seven phases in `lifecycle.sh` passed on a disposable amd64 Debian 13.8 VM
with the official `asl3-appliance` 3.0.3-1.deb13 package and real apt/dpkg/systemd.
ASL3 Asterisk was installed, but a systemd condition prevented it from starting;
there were no AMI nodes, radio devices or live station credentials.

The pre-cleanup source was `d650cef4b13e0f49ceed9ed7a0d30fc611a8a701`, built
as `1.11-1~pr340baseline` (only the changelog version was adjusted for ordering).
The follow-up packages were built as `1.11-1`. The executable change is removal
of unused `DEFAULT_AUDIO_CONFIG`; storage remains driven by `AnnouncementConfig`.
The accompanying regression follows an actual INI override through the add-in
constructor to `AudioService`, database/media directories and persisted settings.
These scripts and this report are test-only files, not installed package payload.

| Phase | Observed result |
| --- | --- |
| Base only | Allmon3 active; empty add-in manifest; audio API 404; no optional module/UI files; base dependency metadata excludes ffmpeg/asl3-tts |
| Fresh optional install | Add-in manifest present; protected audio API 403; timer enabled/active; dedicated state directory permissions correct; base unit has no recovery dependency/hooks |
| Upgrade version-locked pair | Edited announcements/speech/registration files and node config preserved; fixture database rows and original-media hashes identical |
| Restart | Custom INI state/cache paths still used; fixture rows/media unchanged |
| Remove optional package | Base service active; manifest empty and audio API 404; timer inactive; retained registration/INI and runtime data harmless |
| Reinstall | Optional routes/UI/timer return; configuration and saved fixture rows/media unchanged |
| Remove/purge | Base service active; optional config removed; runtime data retained; `dpkg --audit` empty |

The fixture includes a silent upload, future audio schedule and disabled audio
and command switches. It uses real ffmpeg conversion and packaged Piper synthesis
(`asl3-tts` 2.0-1.deb13), but no playback worker/AMI dispatch. The render produced
21,664 bytes of 8 kHz mu-law audio. ffmpeg was 7:7.1.5-0+deb13u1.

The final run ended `ALL_LIFECYCLE_PHASES_PASSED`. Each post-upgrade/restart/reinstall
JSON snapshot exactly matched the pre-upgrade snapshot. Asterisk reported
`MainPID=0`, `ActiveState=inactive`, `ConditionResult=no` throughout checks.

## Reproduction (disposable VM only)

Do **not** run this on an operating station: the script deliberately replaces
node configuration and installs/downgrades/removes packages. It requires root,
`ALLMON3_DISPOSABLE_TEST=1`, hostname `pr340-test`, and the no-radio guard below.
Use a fresh Debian 13 amd64 VM, username `tester`, official ASL3 apt repository,
and `asl3-appliance`. No real configuration, credentials or USB hardware is needed.

Before installing the appliance, prevent Asterisk starts without masking the unit
(the appliance postinst needs to enable it):

```sh
sudo touch /etc/pr340-no-radio
sudo mkdir -p /etc/systemd/system/asterisk.service.d
printf '[Unit]\nConditionPathExists=!/etc/pr340-no-radio\n' |
  sudo tee /etc/systemd/system/asterisk.service.d/disposable-no-radio.conf
sudo systemctl daemon-reload
sudo apt-get install asl3-appliance
```

Build both packages from each source with the repository's normal Debian binary
build (`dpkg-buildpackage -b -us -uc`, with build dependencies installed). Set only
the baseline build's first changelog version to `1.11-1~pr340baseline` in a separate
checkout. Copy the four resulting `.deb` files into `/home/tester/packages/`:

- `allmon3_1.11-1~pr340baseline_all.deb`
- `allmon3-announcements-manager_1.11-1~pr340baseline_all.deb`
- `allmon3_1.11-1_all.deb`
- `allmon3-announcements-manager_1.11-1_all.deb`

Copy `fixture.py` and `lifecycle.sh` beside that directory, then run:

```sh
sudo env ALLMON3_DISPOSABLE_TEST=1 bash /home/tester/lifecycle.sh
```

Results are written under `/home/tester/lifecycle-results-final`. The test copies
its fixture to a service-readable path before using `runuser`. It explicitly sets
UTC and `release_hour=23` to keep Friday automatic bulletin collection outside
the recorded test window. Run before 23:00 UTC (or use a non-Friday guest date),
otherwise legitimate downloaded bulletins can change the snapshot. Use a fresh
VM/test directory for another run; retained state is intentionally not deleted.

## Scope and limits

This closes the previous build/staging-only **idle lifecycle** evidence gap for
Debian 13 amd64. It does not verify live RF, active-job removal, crash recovery
against a real Asterisk instance, Pi/ARM installation or arbitrary old preview
schema migrations. The previous installed-version backport is not used as proof.
The ARN fetch-only/reuse design is still a maintainer decision, not resolved by
these package tests. No additional review request was issued.

## Tested binary SHA-256

- `allmon3_1.11-1_all.deb`: `8fe7239df8f85476100aaf1c50779c8432459080adb5eb002105b77501241add`
- `allmon3-announcements-manager_1.11-1_all.deb`: `09f70e414ee3bbb7dd101a07f6086b8c2a67c8ce0ce4d845ada39c20bb7f13d5`
