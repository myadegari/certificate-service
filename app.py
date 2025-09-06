import asyncio
from contextlib import asynccontextmanager

# import pika
import json
import os
from typing import Dict

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis

from api.endpoints.certificates import router as certificates_router

load_dotenv()

# RabbitMQ connection settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "")
RABBITMQ_NOTIFICATION_QUEUE = os.getenv("RABBITMQ_NOTIFICATION_QUEUE", "")

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", "")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

# Track WebSocket clients per job_id
websocket_clients: Dict[str, list[WebSocket]] = {}


async def consume_notifications():
    """Async RabbitMQ consumer using aio-pika"""
    connection_string = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT or 5672}/{RABBITMQ_VHOST or '%2F'}"
    try:
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(connection_string)
        print("Connected to RabbitMQ for notifications")

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)

            # Declare queue
            queue = await channel.declare_queue(
                RABBITMQ_NOTIFICATION_QUEUE, durable=True
            )

            async def process_message(message: AbstractIncomingMessage):
                async with message.process():
                    try:
                        body = message.body.decode("utf-8")
                        data = json.loads(body)
                        job_id = data.get("job_id")

                        if not job_id:
                            print("Message missing job_id, skipping")
                            return

                        # Broadcast to all connected WebSocket clients for this job
                        if job_id in websocket_clients:
                            for ws in websocket_clients[job_id]:
                                try:
                                    await ws.send_json(data)
                                    print(
                                        f"Sent update to WebSocket client for job {job_id}: {data['status']}"
                                    )
                                except Exception as e:
                                    print(f"Error sending to WebSocket: {e}")

                    except json.JSONDecodeError:
                        print(f"Invalid JSON: {message.body[:100]}")
                    except Exception as e:
                        print(f"Error processing message: {e}")

            print("Starting to consume notifications...")
            await queue.consume(process_message)

            # Keep consumer alive
            await asyncio.Future()  # Run forever

    except Exception as e:
        print(f"RabbitMQ consumer error: {e}")
        raise Exception("Failed to connect to RabbitMQ")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = aioredis.from_url(
        REDIS_URL, decode_responses=True, encoding="utf-8"
    )

    # Start RabbitMQ consumer task
    consumer_task = asyncio.create_task(consume_notifications())
    print("✅ Application started - RabbitMQ notification consumer running")

    yield  # Application runs here

    # Shutdown
    print("🛑 Shutting down - cancelling consumer...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    await app.state.redis.close()
    print("✅ Application shutdown complete")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # Replace with your Next.js app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(certificates_router, prefix="/certificates", tags=["certificates"])


async def get_job_status(job_id: str) -> dict:
    """Get current job status from Redis"""
    try:
        redis_status = await app.state.redis.get(f"job_status:{job_id}")
        if redis_status:
            return json.loads(redis_status)
        return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        print(f"Error getting job status from Redis: {str(e)}")
        return {"job_id": job_id, "status": "unknown"}


@app.websocket("/ws/certificates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    job_id = websocket.query_params.get("job_id")
    if not job_id:
        await websocket.close(code=1008, reason="job_id is required")
        return

    try:
        # Send initial status
        initial_status = await get_job_status(job_id)
        await websocket.send_json(initial_status)

        # Close immediately if status is already completed
        if initial_status.get("status") == "completed":
            await websocket.close(code=1000, reason="Job already completed")
            return

        # Register client
        if job_id not in websocket_clients:
            websocket_clients[job_id] = []
        websocket_clients[job_id].append(websocket)

        # Keep connection alive and handle ping/pong
        while True:
            try:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "status":
                    current_status = await get_job_status(job_id)
                    await websocket.send_json(current_status)

                    # Close connection if job is completed
                    if current_status.get("status") == "completed":
                        await websocket.close(code=1000, reason="Job completed")
                        break
                else:
                    print(f"Received message: {data}")
            except json.JSONDecodeError:
                continue
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        print(f"Client disconnected for job_id: {job_id}")
    except Exception as e:
        print(f"WebSocket error for job_id {job_id}: {str(e)}")
    finally:
        # Cleanup
        if job_id in websocket_clients:
            if websocket in websocket_clients[job_id]:
                websocket_clients[job_id].remove(websocket)
            if not websocket_clients[job_id]:
                del websocket_clients[job_id]
