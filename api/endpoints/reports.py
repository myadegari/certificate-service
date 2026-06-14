import json
import os
import uuid
from urllib.parse import quote_plus

import aio_pika
from aio_pika import Message
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models.report import ReportRequest

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "certificate_jobs")
RABBITMQ_CONNECTION_STRING = f"amqp://{quote_plus(RABBITMQ_USER)}:{quote_plus(RABBITMQ_PASS)}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{quote_plus(RABBITMQ_VHOST)}"

router = APIRouter()

_rabbitmq_connection = None

async def get_rabbitmq_connection():
    global _rabbitmq_connection
    if _rabbitmq_connection is None or _rabbitmq_connection.is_closed:
        _rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_CONNECTION_STRING)
    return _rabbitmq_connection


async def publish_report_job(data: dict, job_id: str):
    """Publishes a report job to RabbitMQ."""
    try:
        connection = await get_rabbitmq_connection()
        async with connection.channel() as channel:
            message_body = json.dumps({"job_id": job_id, "data": data}).encode("utf-8")
            message = Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            await channel.default_exchange.publish(message, routing_key=RABBITMQ_JOB_QUEUE)
        print(f"✅ Published report job {job_id} to RabbitMQ")
    except Exception as e:
        print(f"❌ Error publishing report job: {str(e)}")
        raise


@router.post("/generate/")
async def generate_report_endpoint(request: ReportRequest):
    try:
        job_id = str(uuid.uuid4())
        
        context = {
            "job_id": job_id,
            "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
            "name": f"{request.user.firstName} {request.user.lastName}",
            "national": request.user.nationalId,
            "number": request.reportuniqueid,
            "date": request.date.model_dump(mode="json"),
            "total": request.total.model_dump(mode="json"),
            "enrollments": [item.model_dump(mode="json") for item in request.enrollments],
            "labels": request.labels.model_dump(mode="json"),
        }

        job_data = {
            "job_type": "report",
            "output_dir": "temp_reports",
            "userId": request.user.userId,
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
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")