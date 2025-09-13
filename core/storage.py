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

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "certification")

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
files_collection = db["files"]  # Collection where FileModel saves records
job_statuses_collection = db["job_statuses"] # <-- New collection

# --- MinIO Setup ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_PORT = int(os.getenv("MINIO_PORT", 9000))
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
MINIO_CERT_BUCKET = os.getenv("MINIO_CERT_BUCKET", "certificates")

minio_client = Minio(
    f"{MINIO_ENDPOINT}:{MINIO_PORT}",
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL,
)

# Presigned URL expiry
EXPIRY_HOURS = 24

# Ensure bucket exists
found = minio_client.bucket_exists(MINIO_CERT_BUCKET)
if not found:
    minio_client.make_bucket(MINIO_CERT_BUCKET)
    print(f"Created bucket: {MINIO_CERT_BUCKET}")


async def get_file_presigned_url(file_id: str) -> str | None:
    """
    Given a MongoDB File _id, fetch its record, then generate presigned URL from MinIO.
    """
    if not file_id:
        return None

    try:
        # Fetch file record from MongoDB
        obj_id = ObjectId(file_id)  # Convert string to ObjectId
        file_doc = await files_collection.find_one({"_id": obj_id})
        if not file_doc:
            print(f"File {file_id} not found in MongoDB")
            return None

        bucket = file_doc.get("bucket")
        object_name = file_doc.get("objectName")

        if not bucket or not object_name:
            print(f"File {file_id} missing bucket/objectName")
            return None

        # Generate presigned URL
        url = minio_client.presigned_get_object(
            bucket, object_name, expires=timedelta(hours=EXPIRY_HOURS)
        )
        return url

    except Exception as e:
        print(f"Error generating presigned URL for {file_id}: {e}")
        return None


async def upload_pdf_to_minio_and_save_to_db(
    pdf_path: str, job_id: str, courseCode: str, userId: str 
) -> str | None:
    """
    Uploads PDF to MinIO, saves record to MongoDB, returns MongoDB File _id.
    """
    try:
        # --- Upload to MinIO ---
        object_name = f"{courseCode}/{Path(pdf_path).name}"

        # Upload file
        minio_client.fput_object(
            bucket_name=MINIO_CERT_BUCKET,
            object_name=object_name,
            file_path=pdf_path,
            content_type="application/pdf",
        )

        presigned_url = minio_client.presigned_get_object(
            MINIO_CERT_BUCKET,
            object_name,
            expires=timedelta(days=7),  # Long expiry for certificates
        )

        # --- Save to MongoDB ---
        file_record = {
            "userId": userId,  # Link to user if available
            "courseId": courseCode,  # Optional: link to user if you have user ID in job data
            "bucket": MINIO_CERT_BUCKET,
            "objectName": object_name,
            "originalName": Path(pdf_path).name,
            "mimeType": "application/pdf",
            "size": os.path.getsize(pdf_path),
            "presignedUrl": presigned_url,
            "expiresAt": datetime.now(tz=timezone.utc) + timedelta(days=7),
            "uploadedAt": datetime.now(tz=timezone.utc),
            "metadata": {
                "job_id": job_id,
                "type": "certificate",
            },
        }

        result = await files_collection.insert_one(file_record)
        file_id = str(result.inserted_id)

        print(f"✅ PDF uploaded to MinIO and saved to MongoDB with ID: {file_id}")
        return file_id

    except Exception as e:
        print(f"❌ Failed to upload/save PDF for job {job_id}: {e}")
        return None

# --- NEW: Job Status Storage Logic ---
async def upsert_job_status_in_db(job_id: str, status_data: dict):
    """
    Updates or inserts a job status record in MongoDB.
    """
    try:
        await job_statuses_collection.update_one(
            {"job_id": job_id},
            {"$set": status_data, "$setOnInsert": {"createdAt": datetime.now(tz=timezone.utc)}},
            upsert=True
        )
        print(f"Upserted status for job {job_id} to MongoDB: {status_data['status']}")
    except Exception as e:
        print(f"Error upserting job status to MongoDB for {job_id}: {e}")

async def get_job_status_from_db(job_id: str) -> dict | None:
    """
    Retrieves the latest job status from MongoDB.
    """
    try:
        status_doc = await job_statuses_collection.find_one({"job_id": job_id})
        if status_doc:
            # Pydantic models might not like ObjectId, so remove it
            status_doc.pop('_id', None)
        return status_doc
    except Exception as e:
        print(f"Error fetching job status from MongoDB for {job_id}: {e}")
        return None

async def bulk_sync_redis_to_mongo(redis_client):
    """
    Scans Redis for job statuses and bulk-updates them in MongoDB.
    """
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
                    job_id = keys[i].decode('utf-8').split(':')[-1]
                    operations.append(
                        UpdateOne(
                            {"job_id": job_id},
                            {"$set": status_data, "$setOnInsert": {"createdAt": datetime.now(tz=timezone.utc)}},
                            upsert=True
                        )
                    )
            
            if operations:
                result = await job_statuses_collection.bulk_write(operations)
                updated_count += result.upserted_count + result.modified_count

        print(f"✅ Sync complete. Synced {updated_count} job statuses.")
        return updated_count
    except Exception as e:
        print(f"❌ Error during Redis to MongoDB sync: {e}")
        return 0
