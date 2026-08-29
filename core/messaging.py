"""Shared RabbitMQ helper (producer side).

Used by the FastAPI endpoint to enqueue generation jobs for the worker.
Connection settings come from core.config so there is a single source of
truth.
"""

import json

import aio_pika

from core.config import settings


async def publish_json(queue_name: str, payload: dict) -> None:
    """Publish a persistent JSON message to a durable queue."""
    connection = await aio_pika.connect_robust(settings.amqp_url)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=queue_name,
        )


async def publish_job(job_id: str, data: dict) -> None:
    """Enqueue a generation job for the worker."""
    await publish_json(settings.rabbitmq_job_queue, {"job_id": job_id, "data": data})
