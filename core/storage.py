"""Object storage (Alarik / S3) + MongoDB persistence.

Both the Next.js app and this service share:
  - the same S3-compatible endpoint and buckets (``certificate``),
  - the same MongoDB ``certification`` database
    (``files`` and ``job_statuses`` collections).

The document shape written to ``files`` must stay compatible with the
app's ``models/File.js`` schema (bucket/objectName are read by the
public /api/verify/[id] route).
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from core.config import settings

# --- MongoDB ---
mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
db = mongo_client[settings.mongodb_db_name]
files_collection = db["files"]
job_statuses_collection = db["job_statuses"]

# --- S3 (Alarik) ---
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.storage_endpoint,
    region_name=settings.storage_region,
    aws_access_key_id=settings.storage_access_key,
    aws_secret_access_key=settings.storage_secret_key,
    config=BotoConfig(s3={"addressing_style": "path"}),
)

PRESIGN_EXPIRY_HOURS = 24
FILE_URL_EXPIRY = timedelta(days=7)

_ensured_buckets: set[str] = set()


def _to_public_url(url: str) -> str:
    """Rewrite an internally-signed URL to the public base (browser-reachable)."""
    public_base = settings.storage_public_url.rstrip("/")
    internal_base = settings.storage_endpoint.rstrip("/")
    if public_base and url.startswith(internal_base):
        return public_base + url[len(internal_base):]
    return url


def ensure_bucket(bucket: str) -> None:
    """Create the bucket if it does not exist (cached per process)."""
    if bucket in _ensured_buckets:
        return
    try:
        s3_client.head_bucket(Bucket=bucket)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")
    _ensured_buckets.add(bucket)


def _presigned_get_url(bucket: str, object_name: str, expiry: timedelta) -> str:
    url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": object_name},
        ExpiresIn=int(expiry.total_seconds()),
    )
    return _to_public_url(url)


def _as_object_id(value: str | None):
    """Store as ObjectId when possible so Mongoose can hydrate the doc."""
    if value and ObjectId.is_valid(value):
        return ObjectId(value)
    return value


def _get_object_bytes(bucket: str, object_name: str) -> bytes | None:
    """Fetch an object's raw bytes directly over the internal S3 endpoint."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=object_name)
        return response["Body"].read()
    except ClientError as e:
        print(f"Error fetching object {bucket}/{object_name}: {e}")
        return None


async def get_file_bytes(file_id: str) -> bytes | None:
    """Resolve a MongoDB File _id to its raw bytes for server-side use.

    Reads the object straight from storage via the internal endpoint (no
    presigned URL / public-host rewrite), so the worker can always reach it.
    boto3 is synchronous, so the call runs in a thread executor.
    """
    if not file_id or not ObjectId.is_valid(file_id):
        print(f"Invalid file id: {file_id}")
        return None
    try:
        file_doc = await files_collection.find_one({"_id": ObjectId(file_id)})
    except Exception as e:  # noqa: BLE001
        print(f"Error looking up file {file_id}: {e}")
        return None
    if not file_doc:
        print(f"File {file_id} not found in MongoDB")
        return None
    bucket = file_doc.get("bucket")
    object_name = file_doc.get("objectName")
    if not bucket or not object_name:
        print(f"File {file_id} missing bucket/objectName")
        return None
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_object_bytes, bucket, object_name)


async def upload_pdf_to_storage_and_save_to_db(
    pdf_path: str,
    job_id: str,
    job_type: str,
    course_code: str,
    user_id: str,
    course_id: str | None = None,
) -> str | None:
    """Upload a generated PDF to Alarik and register it in MongoDB.

    Returns the MongoDB File ``_id`` (as string) or None on failure.
    """
    try:
        if job_type == "certificate":
            bucket = settings.certificate_bucket
            object_name = f"{course_code}/{Path(pdf_path).name}"
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        ensure_bucket(bucket)
        s3_client.upload_file(
            pdf_path,
            bucket,
            object_name,
            ExtraArgs={"ContentType": "application/pdf"},
        )

        file_record = {
            "userId": _as_object_id(user_id),
            "courseId": _as_object_id(course_id),
            "bucket": bucket,
            "objectName": object_name,
            "originalName": Path(pdf_path).name,
            "mimeType": "application/pdf",
            "size": Path(pdf_path).stat().st_size,
            "presignedUrl": _presigned_get_url(bucket, object_name, FILE_URL_EXPIRY),
            "expiresAt": datetime.now(tz=UTC) + FILE_URL_EXPIRY,
            "uploadedAt": datetime.now(tz=UTC),
            "metadata": {"job_id": job_id, "type": job_type},
        }
        # Upsert keyed on the job id so a redelivered/retried job replaces its
        # record instead of creating a duplicate certificate File row.
        result = await files_collection.update_one(
            {"metadata.job_id": job_id, "bucket": bucket},
            {"$set": file_record},
            upsert=True,
        )
        if result.upserted_id:
            file_id = str(result.upserted_id)
        else:
            existing = await files_collection.find_one(
                {"metadata.job_id": job_id, "bucket": bucket}, {"_id": 1}
            )
            file_id = str(existing["_id"]) if existing else None
        print(f"PDF uploaded to storage and saved to MongoDB with ID: {file_id}")
        return file_id
    except Exception as e:  # noqa: BLE001
        print(f"Failed to upload/save PDF for job {job_id}: {e}")
        return None


# --- Job status persistence ---
async def upsert_job_status_in_db(job_id: str, status_data: dict) -> None:
    try:
        await job_statuses_collection.update_one(
            {"job_id": job_id},
            {
                "$set": status_data,
                "$setOnInsert": {"createdAt": datetime.now(tz=UTC)},
            },
            upsert=True,
        )
        print(f"Upserted status for job {job_id} to MongoDB: {status_data['status']}")
    except Exception as e:  # noqa: BLE001
        print(f"Error upserting job status for {job_id}: {e}")


async def get_job_status_from_db(job_id: str) -> dict | None:
    try:
        status_doc = await job_statuses_collection.find_one({"job_id": job_id})
        if status_doc:
            status_doc.pop("_id", None)
        return status_doc
    except Exception as e:  # noqa: BLE001
        print(f"Error fetching job status for {job_id}: {e}")
        return None


async def bulk_sync_redis_to_mongo(redis_client) -> int:
    """Scan Redis for job statuses and bulk-upsert them into MongoDB."""
    updated_count = 0
    try:
        print("Starting periodic Redis to MongoDB sync...")
        cursor = "0"
        while True:
            cursor, keys = await redis_client.scan(
                cursor=cursor, match="job_status:*", count=100
            )
            if keys:
                statuses = await redis_client.mget(keys)
                operations = []
                for key, status_json in zip(keys, statuses, strict=True):
                    if not status_json:
                        continue
                    job_id = key.split(":")[-1]
                    operations.append(
                        UpdateOne(
                            {"job_id": job_id},
                            {
                                "$set": json.loads(status_json),
                                "$setOnInsert": {
                                    "createdAt": datetime.now(tz=UTC)
                                },
                            },
                            upsert=True,
                        )
                    )
                if operations:
                    result = await job_statuses_collection.bulk_write(operations)
                    updated_count += result.upserted_count + result.modified_count
            if cursor == 0:
                break
        print(f"Sync complete. Synced {updated_count} job statuses.")
        return updated_count
    except Exception as e:  # noqa: BLE001
        print(f"Error during Redis to MongoDB sync: {e}")
        return 0
