import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import time
from typing import Dict
from urllib.parse import quote_plus

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from redis import asyncio as aioredis

from api.endpoints.certificates import router as certificates_router
from api.endpoints.reports import router as reports_router
from core.storage import (  # <-- Import new functions
    bulk_sync_redis_to_mongo,
    get_job_status_from_db,
)

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
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://:{quote_plus(REDIS_PASSWORD)}@{REDIS_HOST}:{REDIS_PORT}" if REDIS_PASSWORD else f"redis://{REDIS_HOST}:{REDIS_PORT}"

TEMP_DIRS = [
    "tmp",  # where QR codes, images, etc. are stored
]

# Track WebSocket clients per job_id
websocket_clients: Dict[str, list[WebSocket]] = {}


async def cleanup_temp_files():
    """Delete files older than 48 hours in temp directories"""
    cutoff_time = time.time() - (48 * 3600)

    for temp_dir in TEMP_DIRS:
        dir_path = Path(temp_dir)

        if not dir_path.exists():
            continue

        for file_path in dir_path.iterdir():
            if file_path.is_file():
                try:
                    # Get file modification time
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        print(f"🗑️  Deleted: {file_path}")
                except Exception as e:
                    print(f"❌ Error deleting {file_path}: {e}")


async def consume_notifications(redis_client):
    """Consume status updates from RabbitMQ and push to WebSocket clients."""
    from aio_pika import connect_robust
    from aio_pika.abc import AbstractIncomingMessage

    connection_string = f"amqp://{quote_plus(RABBITMQ_USER)}:{quote_plus(RABBITMQ_PASS)}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{quote_plus(RABBITMQ_VHOST)}"
    connection = await connect_robust(connection_string)
    print("✅ Connected to RabbitMQ (notifications consumer)")

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(RABBITMQ_NOTIFICATION_QUEUE, durable=True)

        async def process_message(message: AbstractIncomingMessage):
            async with message.process():
                try:
                    body = message.body.decode()
                    data = json.loads(body)
                    job_id = data.get("job_id")
                    if not job_id:
                        return
                    # Broadcast to all WebSocket clients for this job
                    clients = websocket_clients.get(job_id, [])
                    for ws in list(clients):  # copy to avoid mutation during iteration
                        try:
                            await ws.send_json(data)
                        except Exception:
                            # Client likely disconnected; will be cleaned up on disconnect
                            pass
                except Exception as e:
                    print(f"❌ Error processing notification: {e}")

        await queue.consume(process_message)
        print("👂 Listening for notifications...")
        await asyncio.Future()  # run forever


@asynccontextmanager
async def lifespan(app: FastAPI):
     # Startup
    app.state.redis = aioredis.from_url(
        REDIS_URL, decode_responses=True, encoding="utf-8"
    )
        # Start RabbitMQ consumer task
    app.state.notification_task = asyncio.create_task(consume_notifications(app.state.redis))
    print("✅ Application started - RabbitMQ notification consumer running")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        cleanup_temp_files,
        IntervalTrigger(hours=24),
        id="cleanup_temp_files",
        name="Clean temp files older than 48h",
        replace_existing=True,
    )
    scheduler.add_job(
        bulk_sync_redis_to_mongo,
        IntervalTrigger(hours=24),
        args=[app.state.redis],
        id="sync_redis_to_mongo",
        name="Sync Redis job statuses to MongoDB",
        replace_existing=True,
    )
    scheduler.start()
    print("✅ File cleanup and DB sync schedulers started")

   



    yield  # Application runs here

    # Shutdown
    print("🛑 Shutting down - cancelling consumer...")
    scheduler.shutdown()
    app.state.notification_task.cancel()
    try:
        await app.state.notification_task
    except asyncio.CancelledError:
        pass

    await app.state.redis.close()
    print("✅ Cleanup scheduler and app shut down")
    print("✅ Application shutdown complete")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API key auth
API_KEY = os.getenv("API_KEY", "")
API_REQUIRE_AUTH = os.getenv("API_REQUIRE_AUTH", "false").lower() == "true"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(x_api_key: str = Depends(api_key_header)):
    if API_KEY and API_REQUIRE_AUTH:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=403, detail="Invalid or missing API key")
    elif API_KEY and not x_api_key:
        print("Warning: API key not sent by client. Set API_REQUIRE_AUTH=true to enforce.")
    return True

app.include_router(
    certificates_router,
    prefix="/certificates",
    tags=["certificates"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    reports_router,
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(verify_api_key)],
)

@app.get("/certificates/status/{job_id}")
async def get_status(job_id: str):
    """
    REST API endpoint to get the status of a specific job.
    This is used for initial status check on page load.
    """
    status_data = await get_job_status_from_db(job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Job status not found.")
    return status_data



@app.websocket("/ws/certificates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time certificate status updates.
    """
    await websocket.accept()
    job_id = websocket.query_params.get("job_id")
    if not job_id:
        await websocket.close(code=1008, reason="Job ID not provided")
        return

    # Add the client to our list for this job
    if job_id not in websocket_clients:
        websocket_clients[job_id] = []
    websocket_clients[job_id].append(websocket)

    print(f"WebSocket client connected for job: {job_id}")

    try:
        # Listen for messages from the client.
        # This loop will keep the connection open.
        while True:
            # We don't need to process incoming messages from the client for this use case.
            # We just need to keep the connection alive.
            # If a client sends a message, we can just acknowledge it.
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Client disconnected for job_id: {job_id}")
    except Exception as e:
        print(f"WebSocket error for job_id {job_id}: {str(e)}")
    finally:
        # Cleanup when the connection closes
        if job_id in websocket_clients:
            if websocket in websocket_clients[job_id]:
                websocket_clients[job_id].remove(websocket)
            if not websocket_clients[job_id]:
                del websocket_clients[job_id]
        print(f"🔌 WebSocket disconnected for job: {job_id}")
