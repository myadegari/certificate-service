import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path

import aio_pika
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aio_pika.abc import AbstractIncomingMessage
from redis import asyncio as aioredis

from core.config import settings
from core.storage import (
    upload_pdf_to_storage_and_save_to_db,
    upsert_job_status_in_db,
)
from services.certification_generator import (
    convert_to_pdf,
    generate_certificate,
    safe_image,
)

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

# In-worker retries for potentially transient failures (storage blips,
# LibreOffice hiccups). Permanent errors (bad payloads) never retry.
MAX_JOB_ATTEMPTS = 3

# Dead-letter plumbing: failures are published here for forensics instead of
# being silently dropped. Declared as a fanout exchange so no routing-key
# contract is needed, and the main queue needs no redeclaration.
DLX_NAME = "certificate_dlx"
DLQ_NAME = "certificate_dead_letters"
_dlx_exchange = None


def cleanup_temp_files():
    """Delete files older than 48 hours in the worker's temp directories.

    Runs in the WORKER (not the API): the pptx/pdf/qr artifacts are written by
    this container, so cleanup elsewhere would never see them.
    """
    cutoff = time.time() - 48 * 3600
    for temp_dir in (settings.tmp_dir, settings.temp_certificates_dir):
        dir_path = Path(temp_dir)
        if not dir_path.exists():
            continue
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    print(f"Deleted stale temp file: {file_path}")
                except OSError as e:
                    print(f"Error deleting {file_path}: {e}")


async def send_status_webhook(payload: dict) -> None:
    """POST an HMAC-signed status payload back to the Next.js app.

    Best-effort. The signature covers "{timestamp}.{raw_body}" and the
    timestamp travels in X-Webhook-Timestamp so the verifier can reject
    replays. Only 5xx responses and transport errors are retried; 4xx means
    the delivery can never succeed (bad secret, unknown job) and is abandoned
    immediately. The durable Redis/Mongo status remains the fallback.
    """
    url = settings.next_webhook_url
    if not url:
        return
    secret = settings.webhook_secret or ""
    body = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.".encode("utf-8") + body
    signature = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Timestamp": timestamp,
    }

    attempts = 4
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(1, attempts + 1):
                retryable = False
                try:
                    async with session.post(url, data=body, headers=headers) as resp:
                        if resp.status < 400:
                            return
                        if resp.status < 500:
                            print(
                                f"Webhook got {resp.status} for job {payload.get('job_id')}; "
                                "not retryable, giving up"
                            )
                            return
                        print(
                            f"Webhook attempt {attempt} -> {resp.status} for job {payload.get('job_id')}"
                        )
                        retryable = True
                except Exception as e:  # noqa: BLE001
                    print(
                        f"Webhook attempt {attempt} failed for job {payload.get('job_id')}: {e}"
                    )
                    retryable = True
                if retryable and attempt < attempts:
                    await asyncio.sleep(2 ** (attempt - 1))
    except Exception as e:  # noqa: BLE001
        print(f"Webhook delivery failed for job {payload.get('job_id')}: {e}")
    print(f"Webhook delivery exhausted for job {payload.get('job_id')}")


async def publish_notification(
    job_id: str,
    status: str,
    job_type: str = "certificate",
    file_id: str = "",
    error_message: str = "",
):
    """Persist job status (Redis + MongoDB) and notify the app via webhook."""
    message = {
        "job_id": job_id,
        "status": status,
        "file_id": file_id,
        "job_type": job_type,
        "timestamp": time.time(),
    }
    if error_message and status == "failed":
        message["error"] = error_message

    try:
        await redis_client.setex(f"job_status:{job_id}", 86400, json.dumps(message))
    except Exception as e:  # noqa: BLE001
        print(f"Error storing status in Redis for job {job_id}: {e}")

    if status in ("completed", "failed"):
        await upsert_job_status_in_db(job_id, message)

    if job_type == "certificate":
        await send_status_webhook(message)


async def process_images(image_refs: dict) -> dict:
    return {key: await safe_image(ref) for key, ref in image_refs.items()}


async def run_job(job_id: str, data: dict, job_type: str) -> str:
    """Generate, convert, and upload one certificate. Returns the File id."""
    image_data = await process_images(data["image_data"])
    pptx_path = await generate_certificate(
        template_path=data["template_path"],
        output_dir=data["output_dir"],
        text_data=data["text_data"],
        image_data=image_data,
        qr_data=data["qr_data"],
    )
    pdf_path = await convert_to_pdf(pptx_path, data["output_dir"])

    print(f"Uploading final PDF: {pdf_path}")
    file_id = await upload_pdf_to_storage_and_save_to_db(
        pdf_path,
        job_id,
        job_type,
        data.get("courseCode", ""),
        data["userId"],
        data.get("courseId"),
    )
    if not file_id:
        raise RuntimeError("Failed to upload PDF to storage")
    return file_id


async def dead_letter(message: AbstractIncomingMessage) -> None:
    """Publish the original payload to the DLQ (for forensics) and ack it.

    Done explicitly rather than via x-dead-letter-exchange queue arguments so
    the existing durable queue never needs a destructive redeclaration.
    """
    try:
        if _dlx_exchange is not None:
            await _dlx_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers={"x-death-reason": "processing-failed"},
                ),
                routing_key="",
            )
        await message.ack()
    except Exception as e:  # noqa: BLE001
        print(f"Failed to dead-letter message: {e}")


async def process_job(message: AbstractIncomingMessage):
    # Parse before anything else: a malformed message is dead-lettered without
    # triggering a bogus webhook storm for job_id "unknown".
    try:
        job = json.loads(message.body.decode("utf-8"))
        job_id = job["job_id"]
        data = job["data"]
        job_type = data.get("job_type", "certificate")
    except Exception as e:  # noqa: BLE001
        print(f"Malformed message dropped to DLQ: {e}")
        await dead_letter(message)
        return

    try:
        print(f"Processing job {job_id} of type '{job_type}'")
        await publish_notification(job_id, "processing", job_type=job_type)

        if job_type != "certificate":
            raise ValueError(f"Unknown job_type: {job_type}")

        file_id = None
        last_error = None
        attempts_used = 0
        for attempt in range(1, MAX_JOB_ATTEMPTS + 1):
            attempts_used = attempt
            try:
                file_id = await run_job(job_id, data, job_type)
                break
            except (ValueError, KeyError) as e:
                # Bad payload: retrying can never succeed.
                last_error = e
                break
            except Exception as e:  # noqa: BLE001
                last_error = e
                if attempt < MAX_JOB_ATTEMPTS:
                    delay = 5 * attempt
                    print(
                        f"Transient failure for job {job_id} "
                        f"(attempt {attempt}/{MAX_JOB_ATTEMPTS}), retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)

        if not file_id:
            raise RuntimeError(
                f"Job failed after {attempts_used} attempt(s): {last_error}"
            ) from last_error

        await publish_notification(
            job_id, "completed", job_type=job_type, file_id=file_id
        )
        await message.ack()

    except Exception as e:  # noqa: BLE001
        error_msg = str(e)
        print(f"Error processing job {job_id}: {error_msg}")
        # Mark the job failed for the user, then preserve the payload in the
        # DLQ instead of silently discarding it.
        await publish_notification(
            job_id, "failed", job_type=job_type, error_message=error_msg
        )
        await dead_letter(message)


async def main():
    global _dlx_exchange
    print(f"Starting worker, connecting to {settings.rabbitmq_host}:{settings.rabbitmq_port}")
    connection = await aio_pika.connect_robust(settings.amqp_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        # Dead-letter plumbing (fanout: no routing-key contract). The queue
        # MUST be bound to the exchange — an unbound fanout silently drops
        # everything published to it.
        _dlx_exchange = await channel.declare_exchange(
            DLX_NAME, aio_pika.ExchangeType.FANOUT, durable=True
        )
        dlq = await channel.declare_queue(DLQ_NAME, durable=True)
        await dlq.bind(_dlx_exchange)

        queue = await channel.declare_queue(
            settings.rabbitmq_job_queue, durable=True
        )

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            cleanup_temp_files,
            IntervalTrigger(hours=6),
            id="cleanup_temp_files",
            replace_existing=True,
        )
        scheduler.start()

        print("Waiting for jobs. Press CTRL+C to exit.")
        try:
            await queue.consume(process_job)
            await asyncio.Future()
        finally:
            scheduler.shutdown()
            await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped by user")
    except Exception as e:  # noqa: BLE001
        print(f"Fatal error in worker: {e}")
