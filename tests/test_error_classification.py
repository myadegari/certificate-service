"""Characterization tests for the worker's error classification.

Pins the transient-vs-permanent split that governs the retry loop and the
dead-letter path, ahead of the pipeline extraction.
"""

import asyncio

import pytest

import worker


class FakeMessage:
    """Minimal aio_pika message stand-in: records ack, keeps raw bytes."""

    def __init__(self, body: bytes):
        self.body = body
        self.acked = False

    async def ack(self):
        self.acked = True


@pytest.fixture
def no_side_effects(monkeypatch):
    """Silence notifications and dead-lettering so tests observe only flow."""
    notified = []

    async def fake_notify(job_id, status, job_type="certificate", file_id="", error_message=""):
        notified.append({"job_id": job_id, "status": status, "error": error_message})

    async def fake_dead_letter(message):
        message.acked = True

    monkeypatch.setattr(worker, "publish_notification", fake_notify)
    monkeypatch.setattr(worker, "dead_letter", fake_dead_letter)
    return notified


def make_job_body(job_id="job-1", job_type="certificate", data=None):
    import json

    payload = {
        "job_id": job_id,
        "data": data
        or {
            "job_type": job_type,
            "template_path": "templates/certificate_template.pptx",
            "output_dir": "temp_certificates",
            "text_data": {"unique": "u1"},
            "image_data": {},
            "qr_data": {},
        },
    }
    return json.dumps(payload).encode("utf-8")


class TestPermanentErrorsNoRetry:
    def test_malformed_json_dead_letters_without_notification(self, no_side_effects):
        message = FakeMessage(b"{not json")

        asyncio.run(worker.process_job(message))

        assert message.acked is True
        assert no_side_effects == []  # no bogus webhook storm

    def test_unknown_job_type_is_permanent_no_retry(self, no_side_effects, monkeypatch):
        attempts = []

        async def failing_run_job(job_id, data, job_type):
            attempts.append(1)
            raise ValueError(f"Unknown job_type: {job_type}")

        monkeypatch.setattr(worker, "run_job", failing_run_job)
        message = FakeMessage(make_job_body(job_type="invoice"))

        asyncio.run(worker.process_job(message))

        # process_job rejects non-certificate types itself (before run_job),
        # so the job runs zero times and goes straight to failed+DLQ.
        assert len(attempts) == 0
        assert no_side_effects[-1]["status"] == "failed"
        assert "Unknown job_type" in no_side_effects[-1]["error"]
        assert message.acked is True

    def test_missing_fields_is_permanent(self, no_side_effects, monkeypatch):
        attempts = []

        async def failing_run_job(job_id, data, job_type):
            attempts.append(1)
            raise KeyError("text_data")

        monkeypatch.setattr(worker, "run_job", failing_run_job)
        message = FakeMessage(make_job_body(data={"job_type": "certificate"}))

        asyncio.run(worker.process_job(message))

        assert len(attempts) == 1
        assert no_side_effects[-1]["status"] == "failed"
        assert message.acked is True


class TestTransientErrorsRetry:
    def test_transient_error_retries_then_raises(self, no_side_effects, monkeypatch):
        attempts = []
        delays = []

        async def failing_run_job(job_id, data, job_type):
            attempts.append(1)
            raise RuntimeError("LibreOffice hiccup")

        async def fake_sleep(delay):
            delays.append(delay)

        monkeypatch.setattr(worker, "run_job", failing_run_job)
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        message = FakeMessage(make_job_body())

        asyncio.run(worker.process_job(message))

        # MAX_JOB_ATTEMPTS=3, linear 5*attempt backoff between tries.
        assert len(attempts) == 3
        assert delays == [5, 10]
        assert no_side_effects[-1]["status"] == "failed"
        assert "3 attempt(s)" in no_side_effects[-1]["error"]
        assert "LibreOffice hiccup" in no_side_effects[-1]["error"]
        assert message.acked is True

    def test_transient_then_success_recover(self, no_side_effects, monkeypatch):
        attempts = []

        async def flaky_run_job(job_id, data, job_type):
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("storage blip")
            return "file-id-1"

        monkeypatch.setattr(worker, "run_job", flaky_run_job)
        monkeypatch.setattr(asyncio, "sleep", _noop_sleep)
        message = FakeMessage(make_job_body())

        asyncio.run(worker.process_job(message))

        assert len(attempts) == 2
        assert no_side_effects[-1]["status"] == "completed"
        assert no_side_effects[-1]["error"] == ""
        assert message.acked is True

    def test_upload_failure_returns_none_retries_as_transient(self, no_side_effects, monkeypatch):
        attempts = []

        async def failing_run_job(job_id, data, job_type):
            attempts.append(1)
            raise RuntimeError("Failed to upload PDF to storage")

        monkeypatch.setattr(worker, "run_job", failing_run_job)
        monkeypatch.setattr(asyncio, "sleep", _noop_sleep)
        message = FakeMessage(make_job_body())

        asyncio.run(worker.process_job(message))

        # The `if not file_id: raise RuntimeError(...)` path is transient.
        assert len(attempts) == 3
        assert no_side_effects[-1]["status"] == "failed"


class TestNotificationFlow:
    def test_processing_notification_precedes_run(self, no_side_effects, monkeypatch):
        order = []

        async def ok_run_job(job_id, data, job_type):
            order.append("run")
            return "file-id-1"

        async def fake_notify(job_id, status, job_type="certificate", file_id="", error_message=""):
            order.append(f"notify:{status}")
            no_side_effects.append({"job_id": job_id, "status": status, "error": error_message})

        async def fake_dead_letter(message):
            message.acked = True

        monkeypatch.setattr(worker, "run_job", ok_run_job)
        monkeypatch.setattr(worker, "publish_notification", fake_notify)
        monkeypatch.setattr(worker, "dead_letter", fake_dead_letter)

        async def fake_ack():
            order.append("ack")
            message.acked = True

        message = FakeMessage(make_job_body())
        message.ack = fake_ack

        asyncio.run(worker.process_job(message))

        assert order == ["notify:processing", "run", "notify:completed", "ack"]


async def _noop_sleep(_delay):
    return None
