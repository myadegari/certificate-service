import json
import os
import uuid

import aio_pika
from aio_pika import Message
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from models.certificate import CertificateRequest, Signatory

router = APIRouter()

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 9105  # Updated to match docker-compose.yml
RABBITMQ_VHOST = "tenant1"
RABBITMQ_USER = "certuser"
RABBITMQ_PASS = "securepassword123"
RABBITMQ_JOB_QUEUE = "certificate_jobs"
RABBITMQ_NOTIFICATION_QUEUE = "certificate_notifications"

# Track WebSocket clients per job_id


async def publish_to_rabbitmq(data: dict, job_id: str):
    """Async: Publish job to RabbitMQ"""
    connection_string = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT or 5672}/{RABBITMQ_VHOST or '%2F'}"

    try:
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(connection_string)
        async with connection:
            channel = await connection.channel()

            # Declare queue (durable = survives broker restart)
            await channel.declare_queue(RABBITMQ_JOB_QUEUE, durable=True)

            # Publish message
            message_body = json.dumps({"job_id": job_id, "data": data}).encode("utf-8")
            message = Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # survive broker restart
                content_type="application/json",
            )

            await channel.default_exchange.publish(
                message, routing_key=RABBITMQ_JOB_QUEUE
            )

            print(f"✅ Published job {job_id} to RabbitMQ")

    except Exception as e:
        print(f"❌ Error publishing to RabbitMQ: {str(e)}")
        raise  # Let FastAPI handle it and return 500


def prepare_signatory_data(data) -> Signatory:
    return Signatory(
        name=f"{data.firstName} {data.lastName}",
        position=data.position,
        signature=data.signature,
    )


def safe_image(image_path: str) -> str:
    return image_path if image_path else "services/n-image.png"


@router.post("/generate/")
async def generate_certificate_endpoint(request: CertificateRequest):
    try:
        template_path = os.path.join(
            "templates",
            "certificate_template2.pptx"
            if request.category == "2"
            else "certificate_template.pptx",
        )
        output_dir = "temp_certificates"
        os.makedirs(output_dir, exist_ok=True)

        # date = jdatetime.datetime.now().strftime("%Y/%m/%d")
        cert_id = request.certificationId or str(uuid.uuid4()).upper()
        signatory_data = prepare_signatory_data(request.course.signatory)
        text_data = {
            "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
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
            "logo": safe_image(signatory_data.signature),
            "photo": safe_image(request.course.unitStamp),
        }
        if request.category == "2":
            signatory2_data = prepare_signatory_data(request.course.signatory2)
            text_data.update(
                {
                    "signatory2": signatory2_data.name,
                    "position2": signatory2_data.position,
                }
            )
            image_data.update(
                {
                    "logo2": safe_image(signatory2_data.signature),
                    "photo2": safe_image(request.course.unitStamp2 or ""),
                }
            )

        qr_data = {}
        if request.qr_url or cert_id:
            qr_data["url"] = request.qr_url or f"https://my.site/cert/{cert_id}"

        job_data = {
            "template_path": template_path,
            "output_dir": output_dir,
            "text_data": text_data,
            "image_data": image_data,
            "qr_data": qr_data,
            "job_id": cert_id,
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{certificate_id}")
async def get_certificate(certificate_id: str):
    pdf_path = f"temp_certificates/certificate_{certificate_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"certificate_{certificate_id}.pdf",
    )
