import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis

from api.endpoints.certificates import router as certificates_router
from api.endpoints.reports import router as reports_router
from core.config import settings
from core.messaging import consume_notifications
from core.storage import (
    bulk_sync_redis_to_mongo,
    get_job_status_from_db,
    s3_client,
)

# Track WebSocket clients per job_id
websocket_clients: dict[str, list] = {}


async def handle_notification(data: dict):
    """Broadcast a worker status message to WebSocket clients of that job."""
    job_id = data.get("job_id")
    if not job_id:
        return
    for ws in list(websocket_clients.get(job_id, [])):
        try:
            await ws.send_json(data)
        except Exception:  # noqa: BLE001
            pass  # client disconnected; cleaned up in the WS handler


async def cleanup_temp_files():
    """Delete files older than 48 hours in the temp directories."""
    import time

    cutoff = time.time() - 48 * 3600
    for temp_dir in (
        settings.tmp_dir,
        settings.temp_certificates_dir,
        settings.temp_reports_dir,
    ):
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, encoding="utf-8"
    )
    app.state.notification_task = asyncio.create_task(
        consume_notifications(handle_notification)
    )
    print("Application started - RabbitMQ notification consumer running")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        cleanup_temp_files,
        IntervalTrigger(hours=24),
        id="cleanup_temp_files",
        replace_existing=True,
    )
    scheduler.add_job(
        bulk_sync_redis_to_mongo,
        IntervalTrigger(hours=24),
        args=[app.state.redis],
        id="sync_redis_to_mongo",
        replace_existing=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown()
    app.state.notification_task.cancel()
    try:
        await app.state.notification_task
    except asyncio.CancelledError:
        pass
    await app.state.redis.aclose()
    print("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.cors_allow_origins == "*"
        else [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(certificates_router, prefix="/certificates", tags=["certificates"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])


@app.get("/certificates/status/{job_id}")
async def get_status(job_id: str):
    """Current status of a generation job (MongoDB first, then Redis)."""
    status_data = await get_job_status_from_db(job_id)
    if not status_data:
        try:
            redis_status = await app.state.redis.get(f"job_status:{job_id}")
            if redis_status:
                import json

                status_data = json.loads(redis_status)
        except Exception:  # noqa: BLE001
            pass
    if not status_data:
        # Queued but not yet processed by the worker.
        status_data = {"job_id": job_id, "status": "pending"}
    return status_data


@app.get("/health")
async def health_check():
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None, lambda: s3_client.head_bucket(Bucket=settings.certificate_bucket)
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"Storage unreachable: {e}"
        ) from e
    return {"status": "healthy", "storage": "connected"}


@app.websocket("/ws/certificates")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time certificate status updates for a given job_id."""
    await websocket.accept()
    job_id = websocket.query_params.get("job_id")
    if not job_id:
        await websocket.close(code=1008, reason="Job ID not provided")
        return

    websocket_clients.setdefault(job_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep the connection alive
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        print(f"WebSocket error for job {job_id}: {e}")
    finally:
        clients = websocket_clients.get(job_id, [])
        if websocket in clients:
            clients.remove(websocket)
        if not clients:
            websocket_clients.pop(job_id, None)
