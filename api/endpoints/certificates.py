import json
import os
import uuid
from urllib.parse import quote_plus

import aio_pika
from aio_pika import Message
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models.certificate import CertificateRequest, Signatory, User

router = APIRouter()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE", "certificate_jobs")
RABBITMQ_NOTIFICATION_QUEUE = os.getenv("RABBITMQ_NOTIFICATION_QUEUE", "certificate_notifications")
RABBITMQ_CONNECTION_STRING = f"amqp://{quote_plus(RABBITMQ_USER)}:{quote_plus(RABBITMQ_PASS)}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{quote_plus(RABBITMQ_VHOST)}"

# Reusable connection pool
_rabbitmq_connection = None

async def get_rabbitmq_connection():
    global _rabbitmq_connection
    if _rabbitmq_connection is None or _rabbitmq_connection.is_closed:
        _rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_CONNECTION_STRING)
    return _rabbitmq_connection


async def publish_to_rabbitmq(data: dict, job_id: str):
    """Async: Publish job to RabbitMQ"""
    try:
        connection = await get_rabbitmq_connection()
        async with connection.channel() as channel:
            await channel.declare_queue(RABBITMQ_JOB_QUEUE, durable=True)
            message_body = json.dumps({"job_id": job_id, "data": data}).encode("utf-8")
            message = Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await channel.default_exchange.publish(
                message, routing_key=RABBITMQ_JOB_QUEUE
            )
            print(f"✅ Published job {job_id} to RabbitMQ")

    except Exception as e:
        print(f"❌ Error publishing to RabbitMQ: {str(e)}")
        raise


def prepare_signatory_data(data: User) -> Signatory:
    return Signatory(
        name=f"{data.firstName} {data.lastName}",
        position=data.position or "",
        signature=data.signature or "",
    )


def _safe_image(image_path: str | None) -> str | None:
    return image_path if image_path else None


@router.post("/generate/")
async def generate_certificate_endpoint(request: CertificateRequest):
    try:
        output_dir = "temp_certificates"
        os.makedirs(output_dir, exist_ok=True)

        cert_id = request.certificationId or str(uuid.uuid4()).upper()
        signatory_data = prepare_signatory_data(request.course.signatory)
        text_data = {
            "name": f"{request.user.firstName} {request.user.lastName}",
            "national": request.user.nationalId,
            "course": request.course.name,
            "org": request.course.organizingUnit,
            "date": request.course.date,
            "time": request.course.time,
            "issue": request.issuedAt,
            "unique": request.certificationId,
            "number": request.certificateNumber,
            "signatory": signatory_data.name,
            "position": signatory_data.position,
        }
        image_data = {
            "logo": _safe_image(signatory_data.signature),
            "photo": _safe_image(request.course.unitStamp),
        }
        if request.category == "2" and request.course.signatory2:
            signatory2_data = prepare_signatory_data(request.course.signatory2)
            text_data.update(
                {
                    "signatory2": signatory2_data.name,
                    "position2": signatory2_data.position,
                }
            )
            image_data.update(
                {
                    "logo2": _safe_image(signatory2_data.signature),
                    "photo2": _safe_image(request.course.unitStamp2 or ""),
                }
            )

        qr_data = {}
        if request.qr_url or cert_id:
            qr_data["url"] = request.qr_url or f"https://my.site/cert/{cert_id}"

        job_data = {
            "job_type": "certificate",
            "output_dir": output_dir,
            "text_data": text_data,
            "image_data": image_data,
            "qr_data": qr_data,
            "job_id": cert_id,
            "courseCode": request.course.courseCode,
            "userId": request.user.userId
        }
        await publish_to_rabbitmq(job_data, cert_id)

        return JSONResponse(
            status_code=202,
            content={
                "job_id": cert_id,
                "status": "queued",
                "message": "Certificate generation queued",
            },
        )
    except Exception as e:
        print(f"Error generating certificate: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")



