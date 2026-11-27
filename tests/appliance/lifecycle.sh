#!/bin/bash
# Run only in the disposable VM provisioned for this task; destroys test config.
set -euo pipefail
[ "${ALLMON3_DISPOSABLE_TEST:-}" = 1 ]
[ "$(id -u)" = 0 ]
[ "$(hostname)" = pr340-test ]
export DEBIAN_FRONTEND=noninteractive
cd /home/tester/packages
result=/home/tester/lifecycle-results-final
mkdir -p "$result"
install -d -m 0755 /opt/pr340-test
install -m 0644 /home/tester/fixture.py /opt/pr340-test/fixture.py
# Never start Asterisk or attach radios. Package/service checks remain real.
test -f /etc/pr340-no-radio
systemctl cat asterisk.service | grep -qF "ConditionPathExists=!/etc/pr340-no-radio"
! systemctl is-active --quiet asterisk.service
wait_base() {
    for attempt in $(seq 1 30); do
        if systemctl is-active --quiet allmon3 && curl -fsS http://127.0.0.1:16080/addons > "$result/manifest.json"; then
            return 0
        fi
        sleep 1
    done
    journalctl -u allmon3 -n 40 --no-pager
    return 1
}
check_absent() {
    wait_base
    python3 -c 'import json; assert json.load(open("/home/tester/lifecycle-results-final/manifest.json")) == {"addons":[]}'
    [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:16080/audio/state)" = 404 ]
    [ ! -f /usr/lib/python3/dist-packages/asl_allmon/announcements/__init__.py ]
    [ ! -d /usr/share/allmon3/addons/announcements ]
}
check_present() {
    wait_base
    python3 -c 'import json; a=json.load(open("/home/tester/lifecycle-results-final/manifest.json"))["addons"]; assert len(a)==1 and a[0]["id"]=="announcements"'
    [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:16080/audio/state)" = 403 ]
    systemctl is-active --quiet allmon3-announcements-manager.timer
    systemctl is-enabled --quiet allmon3-announcements-manager.timer
    [ -f /usr/share/allmon3/addons/announcements/audio.js ]
    [ "$(stat -c '%a:%U:%G' /etc/allmon3/audio)" = '750:allmon3:allmon3' ]
    [ "$(stat -c '%a:%U:%G' /var/lib/allmon3/audio-tot)" = '750:allmon3:allmon3' ]
    ! systemctl show allmon3 -p Requires -p After -p ExecStartPre -p ExecStopPost | grep -Eq 'announcements-manager|audio_tot|audio-tot'
}
snapshot() { runuser -u allmon3 -- python3 /opt/pr340-test/fixture.py snapshot; }
# Empty node list avoids even attempted AMI connections; fixture uses only a
# directly constructed service with a callback that raises on dispatch.
systemctl stop allmon3 || true
printf '; Disposable package test: no AMI nodes\n' > /etc/allmon3/allmon3.ini
sha256sum /etc/allmon3/allmon3.ini > "$result/node-config.sha256"
printf 'PHASE 1: base package only\n'
apt-get install -y --allow-downgrades -o Dpkg::Options::=--force-confold ./allmon3_1.11-1~pr340baseline_all.deb
check_absent
dpkg-query -W -f='${Package}: ${Depends}\n' allmon3 > "$result/base-dependencies.txt"
! grep -Eq 'ffmpeg|asl3-tts' "$result/base-dependencies.txt"
printf 'PHASE 2: fresh optional install\n'
apt-get install -y ./allmon3-announcements-manager_1.11-1~pr340baseline_all.deb
check_present
systemctl stop allmon3
install -d -m 0750 -o allmon3 -g allmon3 /var/lib/pr340-state-final
install -d -m 0755 -o allmon3 -g allmon3 /var/cache/pr340-cache-final
cat > /etc/allmon3/announcements.ini <<'EOF'
[announcements]
state_dir = /var/lib/pr340-state-final
cache_dir = /var/cache/pr340-cache-final
timezone = UTC
gap_seconds = 9
release_hour = 23
EOF
sha256sum /etc/allmon3/announcements.ini /etc/allmon3/speech.ini /etc/allmon3/addons.d/announcements.ini > "$result/conffiles.sha256"
runuser -u allmon3 -- python3 /opt/pr340-test/fixture.py seed > "$result/before.json"
systemctl start allmon3
check_present
test -s /var/lib/pr340-state-final/audio.sqlite3
printf 'PHASE 3: upgrade both version-locked packages\n'
apt-get install -y -o Dpkg::Options::=--force-confold ./allmon3_1.11-1_all.deb ./allmon3-announcements-manager_1.11-1_all.deb
check_present
sha256sum -c "$result/conffiles.sha256"
sha256sum -c "$result/node-config.sha256"
snapshot > "$result/after-upgrade.json"
cmp "$result/before.json" "$result/after-upgrade.json"
printf 'PHASE 4: restart with overridden storage\n'
systemctl restart allmon3
check_present
snapshot > "$result/after-restart.json"
cmp "$result/before.json" "$result/after-restart.json"
printf 'PHASE 5: remove optional package; retained registration is harmless\n'
apt-get remove -y allmon3-announcements-manager
check_absent
! systemctl is-active --quiet allmon3-announcements-manager.timer
sha256sum -c "$result/conffiles.sha256"
test -s /var/lib/pr340-state-final/audio.sqlite3
printf 'PHASE 6: reinstall; data preserved\n'
apt-get install -y ./allmon3-announcements-manager_1.11-1_all.deb
check_present
snapshot > "$result/after-reinstall.json"
cmp "$result/before.json" "$result/after-reinstall.json"
sha256sum -c "$result/conffiles.sha256"
printf 'PHASE 7: remove/purge optional package\n'
apt-get purge -y allmon3-announcements-manager
check_absent
! systemctl is-active --quiet allmon3-announcements-manager.timer
test ! -e /etc/allmon3/addons.d/announcements.ini
test ! -e /etc/allmon3/announcements.ini
test ! -e /etc/allmon3/speech.ini
test -s /var/lib/pr340-state-final/audio.sqlite3
sha256sum -c "$result/node-config.sha256"
test -f /etc/pr340-no-radio
systemctl cat asterisk.service | grep -qF "ConditionPathExists=!/etc/pr340-no-radio"
! systemctl is-active --quiet asterisk.service
dpkg --audit > "$result/dpkg-audit.txt"
test ! -s "$result/dpkg-audit.txt"
dpkg-query -W -f='${Package} ${Version} ${db:Status-Status}\n' allmon3 asl3-appliance asl3-tts ffmpeg > "$result/versions.txt"
printf 'ALL_LIFECYCLE_PHASES_PASSED\n'
