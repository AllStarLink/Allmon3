"""Local-node audio library, play queue, and persistent schedules for Allmon3."""

import asyncio
import hashlib
import html as html_lib
import json
import logging
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import aiohttp

MAX_UPLOAD = 100 * 1024 * 1024
MAX_SECONDS = 3600
SEGMENT_SECONDS = 150
GAP_SECONDS = 5
PIPER_BIN = os.environ.get("ALLMON3_PIPER_BIN", "/opt/allmon3-piper/bin/piper")
PIPER_MODEL = os.environ.get("ALLMON3_PIPER_MODEL", "/opt/allmon3-piper/voices/en_US-lessac-medium.onnx")
PIPER_LENGTH_SCALE = "1.25"  # 80% normal speaking rate; 25% longer phonemes.
SPEECH_PROFILE = f"piper:{PIPER_BIN}:{PIPER_MODEL}:length1.25:volume0.8:gain4over3:limit0.95:v2"
FALLBACK_FILE = "qst-no-new-file-" + hashlib.sha256(SPEECH_PROFILE.encode()).hexdigest() + ".ulaw"
FALLBACK_TEXT = "Q S T. No new file is available this week."
PACIFIC = ZoneInfo("America/Los_Angeles")
EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac"}
NEWS = {
    "arn": {"name": "Amateur Radio Newsline", "url": "https://www.arnewsline.org/s/news.mp3",
            "page": "https://www.arnewsline.org/"},
    "aan": {"name": "ARRL Audio News", "page": "https://www.arrl.org/arrl-audio-news"},
}
log = logging.getLogger(__name__)


class AudioError(ValueError):
    pass


def expected_news_friday(now=None):
    """The newest edition expected after Friday afternoon Pacific time."""
    now = now or datetime.now(PACIFIC)
    days_since_friday = (now.weekday() - 4) % 7
    if days_since_friday == 0 and now.hour < 13:
        days_since_friday = 7
    return (now.date() - timedelta(days=days_since_friday)).isoformat()


def edition_date(source, page_html, url=""):
    """Read the publisher's edition date, not the download timestamp."""
    if source == "aan":
        match = re.search(r"AAN-(20\d\d-\d\d-\d\d)\.mp3", url, re.I)
        if match:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date().isoformat()
        text = html_lib.unescape(re.sub(r"<[^>]*>", " ", page_html))
        match = re.search(r"Download\s+([A-Za-z]+\s+\d{1,2},\s+20\d\d)", text, re.I)
        if match:
            return datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()
    elif source == "arn":
        text = html_lib.unescape(re.sub(r"<[^>]*>", " ", page_html))
        match = re.search(r"Amateur Radio Newsline Report\s+\d+\s+for Friday,\s*"
                          r"([A-Za-z]+\s+\d{1,2})(?:st|nd|rd|th)?,\s*(20\d\d)", text, re.I)
        if match:
            return datetime.strptime(match.group(1) + ", " + match.group(2),
                                     "%B %d, %Y").date().isoformat()
    raise AudioError("Could not verify the news bulletin edition date")


def weekly_next(weekday, hhmm, after=None):
    if type(weekday) is not int or not 0 <= weekday <= 6 or not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", hhmm):
        raise AudioError("Choose a weekday and time")
    hour, minute = map(int, hhmm.split(":"))
    if hour > 23:
        raise AudioError("Invalid time")
    now = datetime.fromtimestamp(after if after is not None else datetime.now().timestamp(), PACIFIC)
    for days in range(8):
        day = now.date() + timedelta(days=days)
        if day.weekday() == weekday:
            candidate = datetime.combine(day, clock_time(hour, minute), PACIFIC)
            if candidate.timestamp() > now.timestamp() + 1:
                return candidate.timestamp()
    raise AudioError("Could not calculate the next run")


def daily_next(hhmm, after=None):
    """Next Pacific wall-clock time; skip missing DST times, repeat folds once."""
    if not isinstance(hhmm, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", hhmm):
        raise AudioError("Choose a daily time")
    hour, minute = map(int, hhmm.split(":"))
    now = datetime.fromtimestamp(after if after is not None else datetime.now().timestamp(), PACIFIC)
    for days in range(3):
        day = now.date() + timedelta(days=days)
        candidate = datetime.combine(day, clock_time(hour, minute), PACIFIC)
        # A nonexistent spring-forward time round-trips to a different wall time.
        if datetime.fromtimestamp(candidate.timestamp(), PACIFIC).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            continue
        if candidate.timestamp() > now.timestamp() + 1:
            return candidate.timestamp()
    raise AudioError("Could not calculate the next daily run")


class AudioService:
    def __init__(self, state_dir, cache_dir, nodes, playback, timeout_guard=None, stop_playback=None):
        self.state = Path(state_dir)
        self.cache = Path(cache_dir)
        self.originals = self.state / "audio-originals"
        self.converted = self.cache / "audio"
        self.db_path = self.state / "audio.sqlite3"
        self.nodes = list(nodes)
        self.playback = playback
        self.timeout_guard = timeout_guard
        self.stop_playback = stop_playback
        self.controls = {}
        self.active = {}
        self.fetch_locks = {key: asyncio.Lock() for key in NEWS}
        self.collect_task = None
        self.last_collect_attempt = 0
        self.tts_lock = asyncio.Lock()

    def initialize(self):
        self.originals.mkdir(mode=0o750, parents=True, exist_ok=True)
        self.converted.mkdir(mode=0o755, parents=True, exist_ok=True)
        os.chmod(self.converted, 0o755)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO settings(key,value) VALUES ('playback_enabled','1');
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT,
                    extension TEXT NOT NULL, seconds REAL NOT NULL,
                    created_at REAL NOT NULL, sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sources (
                    source TEXT PRIMARY KEY, asset_id TEXT NOT NULL,
                    fetched_at REAL NOT NULL, sha256 TEXT NOT NULL,
                    edition_date TEXT
                );
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, node INTEGER NOT NULL,
                    items TEXT NOT NULL, recurrence TEXT NOT NULL,
                    weekday INTEGER, local_time TEXT, next_at REAL NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, node INTEGER NOT NULL,
                    items TEXT NOT NULL, status TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL, started_at REAL, finished_at REAL,
                    error TEXT
                );
            """)
            if "edition_date" not in {row[1] for row in db.execute("PRAGMA table_info(sources)")}:
                db.execute("ALTER TABLE sources ADD COLUMN edition_date TEXT")
            if "scheduled_for" not in {row[1] for row in db.execute("PRAGMA table_info(jobs)")}:
                db.execute("ALTER TABLE jobs ADD COLUMN scheduled_for REAL")
            # A command may have reached Asterisk before a daemon restart.
            db.execute("UPDATE jobs SET status='interrupted', finished_at=strftime('%s','now'), "
                       "error='Service restarted during playback; not replayed' WHERE status IN ('playing','paused','pausing','stopping','control_failed')")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _rows(cursor):
        return [dict(row) for row in cursor.fetchall()]

    def _validate_items(self, items):
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise AudioError("Add 1 to 20 items to the stack")
        with self._db() as db:
            for item in items:
                if not isinstance(item, str):
                    raise AudioError("Invalid audio item")
                if item.startswith("source:") and item[7:] in NEWS:
                    continue
                if not re.fullmatch(r"asset:[0-9a-f]{32}", item):
                    raise AudioError("Invalid audio item")
                if not db.execute("SELECT 1 FROM assets WHERE id=?", (item[6:],)).fetchone():
                    raise AudioError("An audio file in the stack is missing")
        return items

    def playback_enabled(self):
        with self._db() as db:
            return db.execute("SELECT value FROM settings WHERE key='playback_enabled'").fetchone()[0] == "1"

    def set_playback_enabled(self, enabled):
        if type(enabled) is not bool:
            raise AudioError("Choose whether audio playback is enabled")
        # Expire due starts while still disabled, before enabling; never catch up.
        if enabled and not self.playback_enabled():
            self._due_schedules()
        with self._db() as db:
            db.execute("UPDATE settings SET value=? WHERE key='playback_enabled'", ("1" if enabled else "0",))
            if not enabled:
                db.execute("UPDATE jobs SET status='cancelled',finished_at=?,error='Master playback disabled' WHERE status='pending'",
                           (datetime.now().timestamp(),))
        return enabled

    def snapshot(self, allowed_nodes):
        if not allowed_nodes:
            return {"nodes": [], "assets": [], "sources": [], "schedules": [], "jobs": [],
                    "playback_enabled": False, "can_manage_playback": False}
        placeholders = ",".join("?" for _ in allowed_nodes)
        with self._db() as db:
            assets = self._rows(db.execute("SELECT id,name,source,seconds,created_at FROM assets ORDER BY created_at DESC"))
            sources = self._rows(db.execute("SELECT source,asset_id,fetched_at,edition_date FROM sources"))
            schedules = self._rows(db.execute(
                f"SELECT * FROM schedules WHERE node IN ({placeholders}) ORDER BY next_at", allowed_nodes))
            jobs = self._rows(db.execute(
                f"SELECT * FROM jobs WHERE node IN ({placeholders}) ORDER BY CASE WHEN status IN ('playing','paused','pausing','stopping','control_failed') "
                "THEN 0 ELSE 1 END, created_at DESC LIMIT 50", allowed_nodes))
        for item in schedules + jobs:
            item["items"] = json.loads(item["items"])
        return {"nodes": allowed_nodes, "assets": assets, "sources": sources,
                "schedules": schedules, "jobs": jobs, "playback_enabled": self.playback_enabled(),
                "can_manage_playback": set(self.nodes).issubset(allowed_nodes)}

    def enqueue(self, node, name, items):
        if not self.playback_enabled():
            raise AudioError("Audio playback is disabled")
        if node not in self.nodes:
            raise AudioError("This node cannot play files stored on this host")
        self._validate_items(items)
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise AudioError("Enter a name of 1 to 80 characters")
        job_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute("INSERT INTO jobs(id,name,node,items,status,created_at) VALUES(?,?,?,?,?,?)",
                       (job_id, name.strip(), node, json.dumps(items), "pending", datetime.now().timestamp()))
        return job_id

    def create_schedule(self, node, name, items, recurrence, run_at=None, weekday=None, local_time=None):
        if node not in self.nodes:
            raise AudioError("This node cannot play files stored on this host")
        self._validate_items(items)
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise AudioError("Enter a schedule name of 1 to 80 characters")
        if recurrence == "once":
            try:
                parsed = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
                next_at = parsed.timestamp() if parsed.tzinfo else 0
            except (AttributeError, ValueError) as e:
                raise AudioError("Choose a date and time") from e
            if next_at < datetime.now().timestamp() + 10:
                raise AudioError("The scheduled time must be in the future")
            weekday = None
            local_time = None
        elif recurrence == "daily":
            weekday = None
            next_at = daily_next(local_time)
        elif recurrence == "weekly":
            next_at = weekly_next(weekday, local_time)
        else:
            raise AudioError("Choose a one-time, daily, or weekly schedule")
        schedule_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute("INSERT INTO schedules(id,name,node,items,recurrence,weekday,local_time,next_at) "
                       "VALUES(?,?,?,?,?,?,?,?)", (schedule_id, name.strip(), node, json.dumps(items),
                       recurrence, weekday, local_time, next_at))
        return schedule_id

    def delete_schedule(self, schedule_id, allowed_nodes):
        with self._db() as db:
            row = db.execute("SELECT node FROM schedules WHERE id=?", (schedule_id,)).fetchone()
            if not row or row["node"] not in allowed_nodes:
                raise AudioError("Schedule not found for your nodes")
            db.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))

    def cancel_pending(self, job_id, allowed_nodes):
        with self._db() as db:
            row = db.execute("SELECT node,status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row or row["node"] not in allowed_nodes or row["status"] != "pending":
                raise AudioError("Only a pending item can be removed from the queue")
            db.execute("UPDATE jobs SET status='cancelled',finished_at=? WHERE id=?",
                       (datetime.now().timestamp(), job_id))

    def asset_original(self, asset_id):
        if not re.fullmatch(r"[0-9a-f]{32}", asset_id):
            raise AudioError("Audio file not found")
        with self._db() as db:
            row = db.execute("SELECT extension FROM assets WHERE id=?", (asset_id,)).fetchone()
        if not row:
            raise AudioError("Audio file not found")
        return self.originals / (asset_id + row["extension"])

    async def ingest(self, temp_path, name, extension, source=None):
        extension = extension.lower()
        if extension not in EXTENSIONS:
            raise AudioError("Upload MP3, WAV, FLAC, OGG, Opus, M4A, or AAC audio")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise AudioError("Audio file needs a name")
        return await asyncio.to_thread(self._convert, Path(temp_path), name.strip(), extension, source)

    @staticmethod
    def _tool(args, timeout, input=None):
        import subprocess
        try:
            return subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout, check=True).stdout
        except subprocess.CalledProcessError as e:
            raise AudioError(f"Audio conversion failed: {(e.stderr or str(e)).strip()[:240]}") from e
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise AudioError(f"Audio conversion failed: {str(e)[:240]}") from e

    def _convert(self, incoming, name, extension, source):
        asset_id = uuid.uuid4().hex
        final_original = self.originals / (asset_id + extension)
        full = self.converted / (asset_id + ".ulaw")
        segments = []
        try:
            duration_text = self._tool(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                        "-of", "default=noprint_wrappers=1:nokey=1", str(incoming)], 45)
            duration = float(duration_text.strip())
            if not 0 < duration <= MAX_SECONDS:
                raise AudioError("Audio must be between 0 and 60 minutes")
            self._tool(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(incoming), "-map", "0:a:0", "-vn",
                        "-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000", "-ac", "1",
                        "-c:a", "pcm_mulaw", "-f", "mulaw", str(full)], 600)
            total_bytes = full.stat().st_size
            if not total_bytes:
                raise AudioError("The audio file contained no playable audio")
            with full.open("rb") as source_file:
                index = 0
                while chunk := source_file.read(8000 * SEGMENT_SECONDS):
                    segment = self.converted / f"{asset_id}_{index:03d}.ulaw"
                    segments.append(segment)
                    with segment.open("wb") as target:
                        target.write(chunk)
                    os.chmod(segment, 0o644)
                    index += 1
            with incoming.open("rb") as source_file:
                digest = hashlib.file_digest(source_file, "sha256").hexdigest()
            os.replace(incoming, final_original)
            os.chmod(final_original, 0o640)
            with self._db() as db:
                db.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?)",
                           (asset_id, name, source, extension, total_bytes / 8000,
                            datetime.now().timestamp(), digest))
            return asset_id
        except Exception:
            for file in segments:
                file.unlink(missing_ok=True)
            final_original.unlink(missing_ok=True)
            raise
        finally:
            full.unlink(missing_ok=True)

    async def fetch_source(self, source):
        if source not in NEWS:
            raise AudioError("Unknown news source")
        async with self.fetch_locks[source]:
            info = NEWS[source]
            timeout = aiohttp.ClientTimeout(total=180, sock_connect=15, sock_read=30)
            async with aiohttp.ClientSession(timeout=timeout, headers={
                    "User-Agent": "Allmon3 audio bulletin collector (https://github.com/AllStarLink/Allmon3)"}) as client:
                url = info.get("url")
                page_hosts = ({"www.arnewsline.org", "arnewsline.org"} if source == "arn"
                              else {"www.arrl.org", "arrl.org"})
                async with await self._get_allowed(client, info["page"], page_hosts) as page:
                    page.raise_for_status()
                    if page.content_length and page.content_length > 4 * 1024 * 1024:
                        raise AudioError("News page is too large")
                    page_bytes = bytearray()
                    async for chunk in page.content.iter_chunked(65536):
                        page_bytes.extend(chunk)
                        if len(page_bytes) > 4 * 1024 * 1024:
                            raise AudioError("News page is too large")
                    page_html = page_bytes.decode("utf-8", "replace")
                if source == "aan":
                    found = re.search(r'href=["\']([^"\'<>]+\.mp3(?:\?[^"\'<>]*)?)["\']', page_html, re.I)
                    if not found:
                        raise AudioError("ARRL has no MP3 link on its Audio News page")
                    url = urljoin(info["page"], html_lib.unescape(found.group(1)))
                    if urlparse(url).hostname not in {"www.arrl.org", "arrl.org", "content.blubrry.com"} or urlparse(url).scheme != "https":
                        raise AudioError("Unexpected ARRL audio host")
                published = edition_date(source, page_html, url)
                if published < expected_news_friday():
                    raise AudioError(f"{info['name']} is still dated {published}; current bulletin unavailable")
                with tempfile.NamedTemporaryFile(dir=self.originals, suffix=".mp3", delete=False) as target:
                    temp_path = Path(target.name)
                    try:
                        allowed_hosts = ({"www.arnewsline.org", "arnewsline.org", "static1.squarespace.com",
                                          "images.squarespace-cdn.com"} if source == "arn" else
                                         {"www.arrl.org", "arrl.org", "content.blubrry.com"})
                        async with await self._get_allowed(client, url, allowed_hosts) as response:
                            response.raise_for_status()
                            size = 0
                            async for chunk in response.content.iter_chunked(65536):
                                size += len(chunk)
                                if size > MAX_UPLOAD:
                                    raise AudioError("News file exceeds 100 MB")
                                target.write(chunk)
                    except Exception:
                        temp_path.unlink(missing_ok=True)
                        raise
            try:
                with temp_path.open("rb") as downloaded:
                    digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
                with self._db() as db:
                    previous = db.execute("SELECT asset_id,sha256,edition_date FROM sources WHERE source=?",
                                          (source,)).fetchone()
                if previous and digest == previous["sha256"] and previous["edition_date"] != published:
                    raise AudioError(f"{info['name']} download is unchanged from the previous edition")
                if previous and digest == previous["sha256"]:
                    asset_id = previous["asset_id"]
                else:
                    asset_id = await self.ingest(temp_path, f"{info['name']} · {published}", ".mp3", source)
                with self._db() as db:
                    db.execute("INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?)",
                               (source, asset_id, datetime.now().timestamp(), digest, published))
                return asset_id
            finally:
                temp_path.unlink(missing_ok=True)

    @staticmethod
    async def _get_allowed(client, url, allowed_hosts):
        for _ in range(5):
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
                raise AudioError("Unexpected audio source address")
            response = await client.get(url, allow_redirects=False)
            if response.status not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("Location")
            response.release()
            if not location:
                raise AudioError("Audio source redirect has no address")
            url = urljoin(url, location)
        raise AudioError("Too many audio source redirects")

    def _source_asset(self, source):
        with self._db() as db:
            row = db.execute("SELECT asset_id,fetched_at,edition_date FROM sources WHERE source=?", (source,)).fetchone()
        return row

    def _due_schedules(self):
        enabled = self.playback_enabled()
        now = datetime.now().timestamp()
        with self._db() as db:
            due = self._rows(db.execute("SELECT * FROM schedules WHERE enabled=1 AND next_at<=?", (now,)))
            for item in due:
                status = "pending" if enabled and now - item["next_at"] <= 300 else "missed"
                db.execute("INSERT INTO jobs(id,name,node,items,status,created_at,scheduled_for) VALUES(?,?,?,?,?,?,?)",
                           (uuid.uuid4().hex, item["name"], item["node"], item["items"], status, now, item["next_at"]))
                if item["recurrence"] in ("daily", "weekly"):
                    next_at = (daily_next(item["local_time"], now + 1) if item["recurrence"] == "daily"
                               else weekly_next(item["weekday"], item["local_time"], now + 1))
                    db.execute("UPDATE schedules SET next_at=? WHERE id=?", (next_at, item["id"]))
                else:
                    db.execute("UPDATE schedules SET enabled=0 WHERE id=?", (item["id"],))

    def _claim_job(self, node):
        if not self.playback_enabled() or node in self.controls:
            return None
        with self._db() as db:
            now = datetime.now().timestamp()
            db.execute("UPDATE jobs SET status='missed',finished_at=?, "
                       "error='Scheduled start is more than five minutes late' "
                       "WHERE node=? AND status='pending' AND scheduled_for IS NOT NULL AND scheduled_for<?",
                       (now, node, now - 300))
            row = db.execute("SELECT * FROM jobs WHERE node=? AND status='pending' "
                             "ORDER BY created_at,id LIMIT 1", (node,)).fetchone()
            if row:
                db.execute("UPDATE jobs SET status='playing',started_at=? WHERE id=?",
                           (datetime.now().timestamp(), row["id"]))
        return dict(row) if row else None

    def _job_update(self, job_id, status=None, position=None, error=None):
        with self._db() as db:
            if position is not None:
                db.execute("UPDATE jobs SET position=? WHERE id=?", (position, job_id))
            if status:
                db.execute("UPDATE jobs SET status=?,error=?,finished_at=? WHERE id=?",
                           (status, error, datetime.now().timestamp() if status in
                            {"done", "substituted", "failed", "interrupted", "cancelled"} else None, job_id))

    def _render_unavailable(self):
        output = self.converted / FALLBACK_FILE
        return self._render_stack_name(FALLBACK_TEXT, output)

    def _render_stack_name(self, text, output):
        # Local CPU inference, lower priority than Asterisk. Text is stdin,
        # never shell interpolation or command options. No robotic fallback.
        with tempfile.TemporaryDirectory(dir=self.cache) as temp_dir:
            wav = Path(temp_dir) / "stack-name.wav"
            raw = Path(temp_dir) / "stack-name.ulaw"
            self._tool(["nice", "-n", "10", PIPER_BIN, "--model", PIPER_MODEL,
                        "--length-scale", PIPER_LENGTH_SCALE, "--volume", "0.8",
                        "--output-file", str(wav)], 120, input=text)
            self._tool(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(wav), "-af", "aresample=8000,volume=4/3,alimiter=limit=0.95:level=false:latency=true",
                        "-ar", "8000", "-ac", "1", "-c:a", "pcm_mulaw",
                        "-f", "mulaw", str(raw)], 60)
            if not 800 <= raw.stat().st_size <= 60 * 8000:
                raise AudioError("Stack-name speech must be between 0.1 and 60 seconds")
            os.chmod(raw, 0o644)
            os.replace(raw, output)
        return output

    async def prepare_stack_name(self, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise AudioError("Enter a stack name of 1 to 80 characters")
        text = " ".join(name.split())
        digest = hashlib.sha256((SPEECH_PROFILE + ":" + text).encode()).hexdigest()
        output = self.converted / ("stack-name-" + digest + ".ulaw")
        async with self.tts_lock:
            if not output.exists():
                await asyncio.to_thread(self._render_stack_name, text, output)
        return output

    async def control_job(self, node, job_id, action):
        if action == "resume" and not self.playback_enabled():
            raise AudioError("Enable audio playback before resuming")
        if node not in self.nodes or action not in {"pause", "resume", "stop"}:
            raise AudioError("Invalid playback control")
        control = self.controls.get(node)
        if not control or control["job"]["id"] != job_id:
            raise AudioError("That job is no longer active on the selected node")
        if self.stop_playback is None:
            raise AudioError("Playback interruption is unavailable")
        async with control["lock"]:
            if self.controls.get(node) is not control:
                raise AudioError("That job has already finished")
            task = control["task"]
            if action == "resume":
                if not control["paused"] or control["blocked"]:
                    raise AudioError("Only a safely paused job can resume")
                control["paused"] = False
                control["request"] = None
                self._job_update(job_id, status="playing")
                task = asyncio.create_task(self._run_job(control["job"]))
                control["task"] = task
                self.active[node] = task
                return job_id
            if action == "pause" and (task.done() or control["paused"] or control["blocked"]):
                raise AudioError("Only a playing job can pause")
            if action == "stop":
                # A stop must not immediately launch the next queued item.
                # Future schedules remain untouched.
                with self._db() as db:
                    db.execute("UPDATE jobs SET status='cancelled',finished_at=? "
                               "WHERE node=? AND status='pending'", (datetime.now().timestamp(), node))
            control["request"] = action
            self._job_update(job_id, status="pausing" if action == "pause" else "stopping")
            if not task.done():
                task.cancel()
                await asyncio.shield(asyncio.gather(task, return_exceptions=True))
                # Resume can be cancelled before the new task's first step.
                # In that case its cancellation handler has not run at all.
                if self.controls.get(node) is control and not control["paused"] and not control["blocked"]:
                    try:
                        await self._release_playback(node, control)
                        if action == "pause":
                            control["paused"] = True
                            self._job_update(job_id, status="paused")
                        else:
                            self.controls.pop(node, None)
                            self._job_update(job_id, status="cancelled")
                    except Exception as e:
                        control["blocked"] = True
                        self._job_update(job_id, status="control_failed", error=str(e)[:240])
            else:
                try:
                    await self._release_playback(node, control)
                except Exception as e:
                    control["blocked"] = True
                    self._job_update(job_id, status="control_failed", error=str(e)[:240])
                    raise AudioError("Audio stop/recovery failed; retry Stop") from e
                self.controls.pop(node, None)
                self._job_update(job_id, status="cancelled")
            if control["blocked"]:
                raise AudioError("Audio stop/recovery failed; retry Stop")
            return job_id

    async def _release_playback(self, node, control):
        errors = []
        if control["dispatched"] and self.stop_playback:
            try:
                await self.stop_playback(node)
                control["dispatched"] = False
            except Exception as e:
                errors.append("Stop not confirmed: " + str(e))
        if self.timeout_guard:
            try:
                await self.timeout_guard.finish(node)
            except Exception as e:
                errors.append("Timeout restoration pending: " + str(e))
        if errors:
            raise AudioError("; ".join(errors))
        control["blocked"] = False

    async def _play_segment(self, node, segment, control, override_timeout=True):
        # Mark intent first: a cancelled/ambiguous AMI command may have reached
        # Asterisk. Cancellation must flush playback before restoring the TOT.
        control["dispatched"] = True
        seconds = segment.stat().st_size / 8000
        if self.timeout_guard and not override_timeout:
            await self.timeout_guard.announce(node, seconds,
                lambda: self.playback(node, segment.with_suffix("")))
        elif self.timeout_guard:
            await self.timeout_guard.dispatch(node, seconds,
                lambda: self.playback(node, segment.with_suffix("")))
        else:
            await self.playback(node, segment.with_suffix(""))
        await asyncio.sleep(seconds + GAP_SECONDS)

    async def _prepare_unavailable(self):
        async with self.tts_lock:
            output = self.converted / FALLBACK_FILE
            if not output.exists():
                output = await asyncio.to_thread(self._render_unavailable)
        return output

    async def _announce_unavailable(self, node, control):
        await self._play_segment(node, await self._prepare_unavailable(), control)

    async def _prepare_job_items(self, job, items):
        # Downloads, conversion and synthesis can exceed a playback lease.
        # Complete these with normal TOT protection before any announcement.
        prepared = []
        for item in items:
            source = item[7:] if item.startswith("source:") else None
            try:
                asset_id = item[6:] if not source else None
                if source:
                    cached = self._source_asset(source)
                    if not cached or cached["edition_date"] != expected_news_friday():
                        asset_id = await self.fetch_source(source)
                    else:
                        asset_id = cached["asset_id"]
                segments = sorted(self.converted.glob(f"{asset_id}_[0-9][0-9][0-9].ulaw"))
                if not segments:
                    raise AudioError("Converted audio is missing; refresh or upload again")
                prepared.append((segments, None))
            except Exception as e:
                if not source:
                    raise
                log.warning("%s unavailable for job %s: %s", source, job["id"], e)
                await self._prepare_unavailable()
                prepared.append((None, str(e)[:120]))
        return prepared

    async def _run_job(self, job):
        node = job["node"]
        control = self.controls.setdefault(node, {
            "job": job, "position": 0, "segment": 0, "segments": None,
            "substituted": [], "request": None, "paused": False,
            "intro_done": False, "outro_done": False, "name_audio": None, "prepared": None,
            "blocked": False, "dispatched": False, "lock": asyncio.Lock(),
            "task": asyncio.current_task()})
        control["task"] = asyncio.current_task()
        try:
            items = json.loads(job["items"])
            # Prepare once per job. Pause/resume checkpoints prevent a second
            # opening announcement after it has completed. An interrupted
            # announcement, like an interrupted content segment, starts over.
            if control["name_audio"] is None:
                control["name_audio"] = await self.prepare_stack_name(job["name"])
            if control["prepared"] is None:
                control["prepared"] = await self._prepare_job_items(job, items)
            if not control["intro_done"]:
                # Speak first with the current normal timeout setting; the
                # first content segment then announces TOT disabled.
                await self._play_segment(node, control["name_audio"], control, override_timeout=False)
                control["intro_done"] = True
            for position in range(control["position"], len(items)):
                control["position"] = position
                item = items[position]
                source = item[7:] if item.startswith("source:") else None
                segments, error = control["prepared"][position]
                if error is not None:
                    await self._announce_unavailable(node, control)
                    control["substituted"].append(f"{NEWS[source]['name']}: {error}")
                    control["position"] = position + 1
                    control["segment"] = 0
                    control["segments"] = None
                    self._job_update(job["id"], position=position + 1)
                    continue
                control["segments"] = segments
                for index in range(control["segment"], len(segments)):
                    control["segment"] = index
                    await self._play_segment(node, segments[index], control)
                    control["segment"] = index + 1
                control["position"] = position + 1
                control["segment"] = 0
                control["segments"] = None
                self._job_update(job["id"], position=position + 1)
            if not control["outro_done"]:
                await self._play_segment(node, control["name_audio"], control)
                control["outro_done"] = True
            if self.timeout_guard:
                await self.timeout_guard.finish(node)
            substituted = control["substituted"]
            self._job_update(job["id"], status="substituted" if substituted else "done",
                             error="; ".join(substituted)[:240] if substituted else None)
            self.controls.pop(node, None)
        except asyncio.CancelledError:
            try:
                await self._release_playback(node, control)
                if control["request"] == "pause":
                    control["paused"] = True
                    self._job_update(job["id"], status="paused")
                else:
                    status = "cancelled" if control["request"] == "stop" else "interrupted"
                    self._job_update(job["id"], status=status,
                        error="Service stopped during playback" if status == "interrupted" else None)
                    self.controls.pop(node, None)
            except Exception as e:
                control["blocked"] = True
                self._job_update(job["id"], status="control_failed", error=str(e)[:240])
                log.exception("Audio stop/timeout restoration pending; queue blocked")
            raise
        except Exception as e:
            try:
                await self._release_playback(node, control)
                self.controls.pop(node, None)
                status = "failed"
            except Exception as restoration:
                control["blocked"] = True
                status = "control_failed"
                e = RuntimeError(f"{e}; {restoration}")
            self._job_update(job["id"], status=status, error=str(e)[:240])

    async def _collect_friday(self):
        for source in NEWS:
            try:
                cached = self._source_asset(source)
                today = datetime.now(PACIFIC).date()
                if (cached and cached["edition_date"] == expected_news_friday()
                        and datetime.fromtimestamp(cached["fetched_at"], PACIFIC).date() == today):
                    continue
                await self.fetch_source(source)
            except Exception as e:
                # The next scheduler pass retries after 30 minutes.
                log.warning("Friday %s collection failed: %s", source, e)

    async def run(self):
        self.initialize()
        if self.timeout_guard:
            await self.timeout_guard.recover(force=True)
        try:
            while True:
                self._due_schedules()
                for node in self.nodes:
                    if node not in self.active:
                        job = self._claim_job(node)
                        if job:
                            self.active[node] = asyncio.create_task(self._run_job(job))
                    elif self.active[node].done():
                        self.active.pop(node)
                now = datetime.now(PACIFIC)
                if (now.weekday() == 4 and now.hour >= 13
                        and datetime.now().timestamp() - self.last_collect_attempt >= 1800
                        and (self.collect_task is None or self.collect_task.done())):
                    self.last_collect_attempt = datetime.now().timestamp()
                    self.collect_task = asyncio.create_task(self._collect_friday())
                await asyncio.sleep(2)
        finally:
            if self.collect_task:
                self.collect_task.cancel()
                await asyncio.gather(self.collect_task, return_exceptions=True)
            for task in self.active.values():
                task.cancel()
            await asyncio.gather(*self.active.values(), return_exceptions=True)
