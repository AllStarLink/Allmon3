"""Audio conversion, queue, schedule, and bulletin freshness checks."""

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock
from zoneinfo import ZoneInfo


path = Path(__file__).resolve().parents[1] / "src/asl_allmon/audio/__init__.py"
spec = importlib.util.spec_from_file_location("test_audio_module", path)
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class BulletinTest(unittest.TestCase):
    def test_publisher_edition_dates_and_friday_cutoff(self):
        arn = "<h1>Amateur Radio Newsline Report 2559 for Friday, November 13th, 2026</h1>"
        aan = '<a href="/files/file/News/Audio%20News/AAN-2026-11-13.mp3">Download</a>'
        self.assertEqual(audio.edition_date("arn", arn), "2026-11-13")
        self.assertEqual(audio.edition_date("aan", aan, "https://www.arrl.org/AAN-2026-11-13.mp3"),
                         "2026-11-13")
        pacific = ZoneInfo("America/Los_Angeles")
        self.assertEqual(audio.expected_news_friday(datetime(2026, 11, 20, 12, tzinfo=pacific)),
                         "2026-11-13")
        self.assertEqual(audio.expected_news_friday(datetime(2026, 11, 20, 13, tzinfo=pacific)),
                         "2026-11-20")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.calls = []

        async def playback(node, path):
            self.calls.append((node, path))

        self.service = audio.AudioService(Path(self.temp.name) / "state",
                                          Path(self.temp.name) / "cache", [1999, 2000], playback)
        self.service.initialize()
        async def fake_name(name):
            output=self.service.converted/'name.ulaw'
            output.write_bytes(b'\xff'*800)
            return output
        self.service.prepare_stack_name=fake_name
        self.wav = Path(self.temp.name) / "tone.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=1000:duration=0.25", str(self.wav)], check=True)

    async def test_upload_conversion_queue_node_choice_and_restart(self):
        asset = await self.service.ingest(self.wav, "Station ID", ".wav")
        segment = next(self.service.converted.glob(f"{asset}_*.ulaw"))
        self.assertGreater(segment.stat().st_size, 1000)
        self.assertEqual(segment.stat().st_mode & 0o777, 0o644)
        with self.assertRaises(audio.AudioError):
            self.service.enqueue(9999, "Wrong host", ["asset:" + asset])
        job_id = self.service.enqueue(2000, "Station ID", ["asset:" + asset])
        job = self.service._claim_job(2000)
        self.assertEqual(job["id"], job_id)

        async def no_delay(_):
            pass

        with patch.object(audio.asyncio, "sleep", no_delay):
            await self.service._run_job(job)
        self.assertEqual(self.calls, [(2000, self.service.converted/"name"), (2000, segment.with_suffix("")), (2000, self.service.converted/"name")])
        self.assertEqual(self.service.snapshot([2000])["jobs"][0]["status"], "done")
        self.assertFalse(self.service.snapshot([1999])["jobs"])
        self.service.initialize()
        self.assertEqual(self.service.snapshot([2000])["jobs"][0]["status"], "done")

    async def test_schedule_is_persistent_and_node_scoped(self):
        asset = await self.service.ingest(self.wav, "Bulletin", ".wav")
        when = (datetime.now().astimezone() + timedelta(hours=1)).isoformat()
        ident = self.service.create_schedule(1999, "Evening", ["asset:" + asset], "once", run_at=when)
        with self.assertRaises(audio.AudioError):
            self.service.delete_schedule(ident, [2000])
        with self.service._db() as db:
            db.execute("UPDATE schedules SET next_at=? WHERE id=?",
                       (datetime.now().timestamp() - 1, ident))
        self.service._due_schedules()
        self.service.initialize()
        state = self.service.snapshot([1999])
        self.assertEqual(len(state["jobs"]), 1)
        self.assertEqual(state["schedules"][0]["enabled"], 0)
        self.service.cancel_pending(state["jobs"][0]["id"], [1999])
        self.assertEqual(self.service.snapshot([1999])["jobs"][0]["status"], "cancelled")

    async def test_stale_news_speaks_tts_on_selected_node_instead_of_cached_audio(self):
        asset = await self.service.ingest(self.wav, "Old episode", ".wav", "arn")
        next_file = Path(self.temp.name) / "station_id.wav"
        shutil.copyfile(self.service.asset_original(asset), next_file)
        station_id = await self.service.ingest(next_file, "Station ID", ".wav")
        with self.service._db() as db:
            db.execute("INSERT INTO sources VALUES(?,?,?,?,?)",
                       ("arn", asset, datetime.now().timestamp(), "fake", "2020-01-03"))
        job_id = self.service.enqueue(1999, "Latest bulletin then ID",
                                      ["source:arn", "asset:" + station_id])
        job = self.service._claim_job(1999)

        async def unavailable(_):
            raise audio.AudioError("Current bulletin unavailable")

        async def announcement(node, control):
            self.calls.append((node, "QST voice announcement"))

        async def no_delay(_):
            pass

        with patch.object(self.service, "fetch_source", unavailable), \
                patch.object(self.service, "_announce_unavailable", announcement), \
                patch.object(self.service, "_prepare_unavailable", AsyncMock()), \
                patch.object(audio.asyncio, "sleep", no_delay):
            await self.service._run_job(job)
        self.assertEqual(self.service.snapshot([1999])["jobs"][0]["id"], job_id)
        self.assertEqual(self.service.snapshot([1999])["jobs"][0]["status"], "substituted")
        other_segment = next(self.service.converted.glob(f"{station_id}_*.ulaw"))
        self.assertEqual(self.calls, [(1999, self.service.converted/"name"),
                                      (1999, "QST voice announcement"),
                                      (1999, other_segment.with_suffix("")),
                                      (1999, self.service.converted/"name")])

    async def test_missed_schedule_is_not_transmitted_after_restart(self):
        asset = await self.service.ingest(self.wav, "ID", ".wav")
        when = (datetime.now().astimezone() + timedelta(hours=1)).isoformat()
        ident = self.service.create_schedule(1999, "Old", ["asset:" + asset], "once", run_at=when)
        with self.service._db() as db:
            db.execute("UPDATE schedules SET next_at=? WHERE id=?",
                       (datetime.now().timestamp() - 600, ident))
        self.service._due_schedules()
        self.assertEqual(self.service.snapshot([1999])["jobs"][0]["status"], "missed")
        self.assertIsNone(self.service._claim_job(1999))


if __name__ == "__main__":
    unittest.main()
