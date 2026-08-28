import asyncio
import json
import time

import aio_pika
import redis
from aio_pika.abc import AbstractIncomingMessage

from core.config import settings
from core.messaging import publish_json
from core.storage import (
    upload_pdf_to_storage_and_save_to_db,
    upsert_job_status_in_db,
)
from services import report_generator
from services.certification_generator import (
    convert_to_pdf,
    generate_certificate,
    safe_image,
)

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


async def publish_notification(
    job_id: str,
    status: str,
    file_id: str = "",
    error_message: str = "",
):
    """Persist job status (Redis + MongoDB) and notify the API layer."""
    message = {
        "job_id": job_id,
        "status": status,
        "file_id": file_id,
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

    max_retries = 5
    for attempt in range(max_retries):
        try:
            await publish_json(settings.rabbitmq_notification_queue, message)
            print(f"Published notification for job {job_id}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"Notification attempt {attempt + 1} failed for {job_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                raise


async def process_images(image_refs: dict) -> dict:
    return {key: await safe_image(ref) for key, ref in image_refs.items()}


async def process_job(message: AbstractIncomingMessage):
    async with message.process():
        job_id = "unknown"
        pdf_path = None
        try:
            job = json.loads(message.body.decode("utf-8"))
            job_id = job["job_id"]
            data = job["data"]
            job_type = data.get("job_type", "certificate")
            print(f"Processing job {job_id} of type '{job_type}'")
            await publish_notification(job_id, "processing")

            if job_type == "certificate":
                image_data = await process_images(data["image_data"])
                pptx_path = await generate_certificate(
                    template_path=data["template_path"],
                    output_dir=data["output_dir"],
                    text_data=data["text_data"],
                    image_data=image_data,
                    qr_data=data["qr_data"],
                )
                pdf_path = await convert_to_pdf(pptx_path, data["output_dir"])
            elif job_type == "report":
                docx_path = await report_generator.generate_enrollment_report(
                    template_path=data["template_path"],
                    output_dir=data["output_dir"],
                    context=data["context"],
                )
                pdf_path = await report_generator.convert_to_pdf(
                    docx_path, data["output_dir"]
                )
            else:
                raise ValueError(f"Unknown job_type: {job_type}")

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
            await publish_notification(job_id, "completed", file_id=file_id)

        except Exception as e:  # noqa: BLE001
            error_msg = str(e)
            print(f"Error processing job {job_id}: {error_msg}")
            await publish_notification(job_id, "failed", error_message=error_msg)
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
