# app/core/storage.py
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

load_dotenv()

# --- Config (safe at module level) ---
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGODB_DB_NAME", "certification")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_PORT = int(os.getenv("MINIO_PORT", 9000))
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
MINIO_CERT_BUCKET = os.getenv("MINIO_CERT_BUCKET", "certificates")
MINIO_REPORT_BUCKET = os.getenv("MINIO_REPORT_BUCKET", "reports")
EXPIRY_HOURS = 24

_mongo_client = None
_minio_client = None
_buckets_initialized = False


async def get_mongo():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGO_URI)
    return _mongo_client


async def get_db():
    client = await get_mongo()
    return client[MONGO_DB_NAME]


async def get_files_collection():
    db = await get_db()
    return db["files"]


async def get_users_collection():
    db = await get_db()
    return db["users"]


async def get_job_statuses_collection():
    db = await get_db()
    return db["job_statuses"]


def get_minio():
    global _minio_client, _buckets_initialized
    if _minio_client is None:
        _minio_client = Minio(
            f"{MINIO_ENDPOINT}:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_USE_SSL,
        )
    if not _buckets_initialized:
        for bucket in (MINIO_CERT_BUCKET, MINIO_REPORT_BUCKET):
            try:
                if not _minio_client.bucket_exists(bucket):
                    _minio_client.make_bucket(bucket)
                    print(f"Created MinIO bucket: {bucket}")
            except S3Error as e:
                if e.code != "BucketAlreadyOwnedByYou":
                    print(f"Error ensuring bucket {bucket}: {e}")
        _buckets_initialized = True
    return _minio_client


async def get_file_presigned_url(file_id: str) -> str | None:
    if not file_id:
        return None

    try:
        if not ObjectId.is_valid(file_id):
            print(f"Invalid file_id: {file_id}")
            return None
        obj_id = ObjectId(file_id)
        files_collection = await get_files_collection()
        file_doc = await files_collection.find_one({"_id": obj_id})
        if not file_doc:
            print(f"File {file_id} not found in MongoDB")
            return None

        bucket = file_doc.get("bucket")
        object_name = file_doc.get("objectName")

        if not bucket or not object_name:
            print(f"File {file_id} missing bucket/objectName")
            return None

        mc = get_minio()
        url = mc.presigned_get_object(
            bucket, object_name, expires=timedelta(hours=EXPIRY_HOURS)
        )
        return url

    except Exception as e:
        print(f"Error generating presigned URL for {file_id}: {e}")
        return None


async def upload_pdf_to_minio_and_save_to_db(
    pdf_path: str, job_id: str, job_type: str, courseCode: str, userId: str
) -> str | None:
    try:
        mc = get_minio()
        object_name = None
        file_record = None
        if job_type == "certificate":
            object_name = f"{courseCode}/{Path(pdf_path).name}"
            mc.fput_object(
                bucket_name=MINIO_CERT_BUCKET,
                object_name=object_name,
                file_path=pdf_path,
                content_type="application/pdf",
            )
            presigned_url = mc.presigned_get_object(
                MINIO_CERT_BUCKET, object_name, expires=timedelta(days=7),
            )
            file_record = {
                "userId": userId,
                "courseId": courseCode,
                "bucket": MINIO_CERT_BUCKET,
                "objectName": object_name,
                "originalName": Path(pdf_path).name,
                "mimeType": "application/pdf",
                "size": os.path.getsize(pdf_path),
                "presignedUrl": presigned_url,
                "expiresAt": datetime.now(tz=timezone.utc) + timedelta(days=7),
                "uploadedAt": datetime.now(tz=timezone.utc),
                "metadata": {"job_id": job_id, "type": "certificate"},
            }
        elif job_type == "report":
            object_name = f"{userId}/{Path(pdf_path).name}"
            mc.fput_object(
                bucket_name=MINIO_REPORT_BUCKET,
                object_name=object_name,
                file_path=pdf_path,
                content_type="application/pdf",
            )
            presigned_url = mc.presigned_get_object(
                MINIO_REPORT_BUCKET, object_name, expires=timedelta(days=7),
            )
            file_record = {
                "userId": userId,
                "bucket": MINIO_REPORT_BUCKET,
                "objectName": object_name,
                "originalName": Path(pdf_path).name,
                "mimeType": "application/pdf",
                "size": os.path.getsize(pdf_path),
                "presignedUrl": presigned_url,
                "expiresAt": datetime.now(tz=timezone.utc) + timedelta(days=7),
                "uploadedAt": datetime.now(tz=timezone.utc),
                "metadata": {"job_id": job_id, "type": "report"},
            }
        else:
            raise ValueError(f"Unknown job_type: {job_type}")

        files_collection = await get_files_collection()
        result = await files_collection.insert_one(file_record)
        file_id = str(result.inserted_id)

        print(f"✅ PDF uploaded to MinIO and saved to MongoDB with ID: {file_id}")
        return file_id

    except Exception as e:
        print(f"❌ Failed to upload/save PDF for job {job_id}: {e}")
        return None

async def upsert_job_status_in_db(job_id: str, status_data: dict):
    try:
        collection = await get_job_statuses_collection()
        await collection.update_one(
            {"job_id": job_id},
            {"$set": status_data, "$setOnInsert": {"createdAt": datetime.now(tz=timezone.utc)}},
            upsert=True
        )
        print(f"Upserted status for job {job_id} to MongoDB: {status_data['status']}")
    except Exception as e:
        print(f"Error upserting job status to MongoDB for {job_id}: {e}")

async def get_job_status_from_db(job_id: str) -> dict | None:
    try:
        collection = await get_job_statuses_collection()
        status_doc = await collection.find_one({"job_id": job_id})
        if status_doc:
            status_doc.pop('_id', None)
        return status_doc
    except Exception as e:
        print(f"Error fetching job status from MongoDB for {job_id}: {e}")
        return None

async def bulk_sync_redis_to_mongo(redis_client):
    updated_count = 0
    try:
        print("🚀 Starting periodic Redis to MongoDB sync...")
        cursor = '0'
        while cursor != 0:
            cursor, keys = await redis_client.scan(cursor=cursor, match='job_status:*', count=100)
            if not keys:
                continue

            statuses = await redis_client.mget(keys)

            operations = []
            for i, status_json in enumerate(statuses):
                if status_json:
                    status_data = json.loads(status_json)
                    job_id = keys[i].split(':')[-1]
                    operations.append(
                        UpdateOne(
                            {"job_id": job_id},
                            {"$set": status_data, "$setOnInsert": {"createdAt": datetime.now(tz=timezone.utc)}},
                            upsert=True
                        )
                    )

            if operations:
                collection = await get_job_statuses_collection()
                result = await collection.bulk_write(operations)
                updated_count += result.upserted_count + result.modified_count

        print(f"✅ Sync complete. Synced {updated_count} job statuses.")
        return updated_count
    except Exception as e:
        print(f"❌ Error during Redis to MongoDB sync: {e}")
        return 0
