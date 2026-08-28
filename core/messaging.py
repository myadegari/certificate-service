"""Shared RabbitMQ helpers (producer side).

Used by the FastAPI endpoints (to enqueue jobs) and by the worker
(to publish status notifications). Connection settings come from
core.config so there is a single source of truth.
"""

import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

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


async def consume_notifications(handler) -> None:
    """Consume the notification queue; `handler` is an async callable(dict)."""
    connection = await aio_pika.connect_robust(settings.amqp_url)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(
            settings.rabbitmq_notification_queue, durable=True
        )

        async def _wrap(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    await handler(json.loads(message.body.decode("utf-8")))
                except Exception as e:  # noqa: BLE001
                    print(f"Error processing notification: {e}")

        await queue.consume(_wrap)
        await asyncio.Future()  # run forever
