import asyncio
import hashlib
import hmac
import json
import time

import aio_pika
import aiohttp
import redis
from aio_pika.abc import AbstractIncomingMessage

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

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


async def send_status_webhook(payload: dict) -> None:
    """POST an HMAC-signed status payload back to the Next.js app.

    Best-effort with retries; the durable Redis/Mongo status remains the
    fallback if delivery ultimately fails.
    """
    url = settings.next_webhook_url
    if not url:
        return
    secret = settings.webhook_secret or ""
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
    }
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(5):
            try:
                async with session.post(url, data=body, headers=headers) as resp:
                    if resp.status < 400:
                        return
                    print(f"Webhook attempt {attempt + 1} -> {resp.status} for job {payload.get('job_id')}")
            except Exception as e:  # noqa: BLE001
                print(f"Webhook attempt {attempt + 1} failed for job {payload.get('job_id')}: {e}")
            await asyncio.sleep(2 ** attempt)
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
        redis_client.setex(f"job_status:{job_id}", 86400, json.dumps(message))
    except Exception as e:  # noqa: BLE001
        print(f"Error storing status in Redis for job {job_id}: {e}")

    if status in ("completed", "failed"):
        await upsert_job_status_in_db(job_id, message)

    if job_type == "certificate":
        await send_status_webhook(message)


async def process_images(image_refs: dict) -> dict:
    return {key: await safe_image(ref) for key, ref in image_refs.items()}


async def process_job(message: AbstractIncomingMessage):
    async with message.process():
        job_id = "unknown"
        job_type = "certificate"
        pdf_path = None
        try:
            job = json.loads(message.body.decode("utf-8"))
            job_id = job["job_id"]
            data = job["data"]
            job_type = data.get("job_type", "certificate")
            print(f"Processing job {job_id} of type '{job_type}'")
            await publish_notification(job_id, "processing", job_type=job_type)

            if job_type != "certificate":
                raise ValueError(f"Unknown job_type: {job_type}")

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
                raise Exception("Failed to upload PDF to storage")
            await publish_notification(job_id, "completed", job_type=job_type, file_id=file_id)

        except Exception as e:  # noqa: BLE001
            error_msg = str(e)
            print(f"Error processing job {job_id}: {error_msg}")
            await publish_notification(job_id, "failed", job_type=job_type, error_message=error_msg)
            # Swallow the exception so the message is ACKed; re-raising would
            # NACK it and cause an endless redelivery loop for permanent
            # failures (bad template data, unreachable storage, ...).


async def main():
    print(f"Starting worker, connecting to {settings.rabbitmq_host}:{settings.rabbitmq_port}")
    connection = await aio_pika.connect_robust(settings.amqp_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(
            settings.rabbitmq_job_queue, durable=True
        )
        print("Waiting for jobs. Press CTRL+C to exit.")
        await queue.consume(process_job)
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped by user")
    except Exception as e:  # noqa: BLE001
        print(f"Fatal error in worker: {e}")
