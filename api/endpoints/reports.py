import json
import os
from typing import List
import uuid

import aio_pika
from aio_pika import Message
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from models.report import ReportRequest

# --- Load RabbitMQ config from environment variables ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 9105))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "tenant1")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "certuser")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "securepassword123")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "certificate_jobs") # We can reuse the same queue

router = APIRouter()


async def publish_report_job(data: dict, job_id: str):
    """Publishes a report job to RabbitMQ."""
    connection_string = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    connection = await aio_pika.connect_robust(connection_string)
    async with connection:
        channel = await connection.channel()
        message_body = json.dumps({"job_id": job_id, "data": data}).encode("utf-8")
        message = Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        await channel.default_exchange.publish(message, routing_key=RABBITMQ_JOB_QUEUE)
    print(f"✅ Published report job {job_id} to RabbitMQ")


@router.post("/generate/")
async def generate_report_endpoint(request: ReportRequest):
    job_id = str(uuid.uuid4())
    
    # This context object must match the placeholders in your .docx template
    context = {
        "job_id": job_id,
        "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
        "name": f"{request.user.firstName} {request.user.lastName}",
        "national": request.user.nationalId,
        "number":request.reportuniqueid,
          # FIX: Convert Pydantic models to dictionaries before serializing
        "date": request.date.model_dump(),
        "total": request.total.model_dump(),
        "enrollments": [item.model_dump() for item in request.enrollments],
        "labels": request.labels.model_dump(),

        
        
    }

    job_data = {
        "job_type": "report",  # <-- CRITICAL: This tells the worker how to process the job
        "template_path": "templates/report_template.docx",
        "output_dir": "temp_reports", # A separate directory for generated reports
        "userId": request.user.userId, # For saving the file reference later
        "context": context,
    }

    await publish_report_job(job_data, job_id)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "message": "Enrollment report generation has been queued.",
        },
    )