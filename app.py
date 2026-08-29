import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis

from api.endpoints.certificates import router as certificates_router
from core.config import settings
from core.storage import (
    bulk_sync_redis_to_mongo,
    get_job_status_from_db,
    s3_client,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, encoding="utf-8"
    )
    print("Application started")

    # NOTE: temp-file cleanup lives in the worker (worker.py) — that is the
    # container that actually writes tmp/ and temp_certificates/.
    scheduler = AsyncIOScheduler()
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
    await app.state.redis.aclose()
    print("Application shutdown complete")


app = FastAPI(lifespan=lifespan)

_cors_origins = (
    ["*"]
    if settings.cors_allow_origins == "*"
    else [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
)
# A wildcard origin can never be combined with credentials: Starlette would
# echo any requesting origin with Access-Control-Allow-Credentials, letting
# arbitrary websites make credentialed calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=(_cors_origins != ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(certificates_router, prefix="/certificates", tags=["certificates"])


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
