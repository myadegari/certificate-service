import asyncio
import json
import os
from pathlib import Path
import time

import aio_pika
from aio_pika import Message as AioPikaMessage  # Optional, for clarity
from aio_pika.abc import AbstractIncomingMessage
from dotenv import load_dotenv
import redis

from core.storage import upload_pdf_to_minio_and_save_to_db, upsert_job_status_in_db
from services.certification_generator import (
    convert_to_pdf,
    generate_certificate,
    safe_image,
)

load_dotenv()

# Config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "certificate_jobs")
RABBITMQ_NOTIFICATION_QUEUE = os.getenv(
    "RABMQ_NOTIFICATION_QUEUE", "certificate_notifications"
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Redis client (sync, since we're using it in async context — fine for simple ops)
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    password=REDIS_PASSWORD,
    decode_responses=True,
)


# ================================
# ASYNC PUBLISH NOTIFICATION
# ================================
async def publish_notification(
    job_id: str, status: str, file_id: str = "", error_message: str = ""
):
    """Async: Publish job status notification to RabbitMQ and Redis with retry"""
    message = {
        "job_id": job_id,
        "status": status,
        "file_id": file_id,  # ✅ Send MongoDB File ID instead of path
        "timestamp": time.time(),
    }
    if error_message and status == "failed":
        message["error"] = error_message

    # Store in Redis first
    try:
        redis_client.setex(f"job_status:{job_id}", 86400, json.dumps(message))
    except Exception as e:
        print(f"Error storing in Redis for job {job_id}: {str(e)}")
    if status in ["completed", "failed"]:
        await upsert_job_status_in_db(job_id, message)

    connection_string = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT or 5672}/{RABBITMQ_VHOST or '%2F'}"

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        connection = None
        try:
            connection = await aio_pika.connect_robust(connection_string)
            async with connection:
                channel = await connection.channel()
                await channel.declare_queue(RABBITMQ_NOTIFICATION_QUEUE, durable=True)

                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(message).encode("utf-8"),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        content_type="application/json",
                        headers={"timestamp": int(time.time())},
                    ),
                    routing_key=RABBITMQ_NOTIFICATION_QUEUE,
                )

            print(f"✅ Successfully published notification for job {job_id}")
            return True

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for job {job_id}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ Max retries reached for job {job_id}. Giving up.")
                raise
        finally:
            if connection and not connection.is_closed:
                await connection.close()


# ================================
# ASYNC IMAGE PROCESSING
# ================================
async def process_images(data):
    image_data = {}
    for k, v in data["image_data"].items():
        saved_path = await safe_image(v)
        image_data[k] = saved_path
    return image_data


# ================================
# ASYNC JOB PROCESSOR
# ================================
async def process_job(message: AbstractIncomingMessage):
    async with message.process():
        job_id = "unknown"
        try:
            body = message.body.decode("utf-8")
            job = json.loads(body)
            job_id = job["job_id"]
            data = job["data"]
            print(f"🔧 Processing job {job_id}")

            redis_client.setex(
                f"job_status:{job_id}",
                86400,
                json.dumps(
                    {"job_id": job_id, "status": "processing", "timestamp": time.time()}
                ),
            )

            image_data = await process_images(data)

            print("🎨 Generating PPTX...")
            pptx_path = await generate_certificate(
                template_path=data["template_path"],
                output_dir=data["output_dir"],
                text_data=data["text_data"],
                image_data=image_data,
                qr_data=data["qr_data"],
            )
            pptx_path = str(Path(pptx_path).resolve())
            print(f"✅ Generated PPTX: {pptx_path}")

            print("📄 Converting PPTX to PDF...")
            pdf_path = await convert_to_pdf(pptx_path, data["output_dir"])
            print(f"✅ Generated PDF: {pdf_path}")
            # ✅ --- UPLOAD TO MINIO + SAVE TO MONGODB ---
            file_id = await upload_pdf_to_minio_and_save_to_db(
                pdf_path, job_id, data["courseCode"], data["userId"]
            )
            if not file_id:
                raise Exception("Failed to upload PDF to storage")
            # ✅ --- SEND NOTIFICATION WITH FILE_ID ---
            await publish_notification(job_id, "completed", file_id=file_id)

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error processing job {job_id}: {error_msg}")
            await publish_notification(job_id, "failed", error_message=error_msg)
            raise  # Triggers NACK + requeue


# ================================
# MAIN CONSUMER LOOP
# ================================
async def main():
    connection_string = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT or 5672}/{RABBITMQ_VHOST or '%2F'}"

    print(
        f"🚀 Starting worker, connecting to {RABBITMQ_HOST}:{RABBITMQ_PORT or 5672}, vhost={RABBITMQ_VHOST or '/'}"
    )

    connection = await aio_pika.connect_robust(connection_string)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(RABBITMQ_JOB_QUEUE, durable=True)

        print(" [*] Waiting for messages. To exit press CTRL+C")
        await queue.consume(process_job)

        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Worker stopped by user")
    except Exception as e:
        print(f"💥 Fatal error in worker: {e}")
