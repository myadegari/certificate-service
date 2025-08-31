from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
from models.certificate import CertificateRequest,Signatory
from services.certification_generator import generate_certificate, convert_to_pdf, safe_image
import jdatetime
import uuid
import pika
import json
router = APIRouter()

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 9105  # Updated to match docker-compose.yml
RABBITMQ_VHOST = "tenant1"
RABBITMQ_USER = "certuser"
RABBITMQ_PASS = "securepassword123"
RABBITMQ_JOB_QUEUE = "certificate_jobs"
RABBITMQ_NOTIFICATION_QUEUE = "certificate_notifications"

# Track WebSocket clients per job_id

def publish_to_rabbitmq(data: dict, job_id: str):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, virtual_host=RABBITMQ_VHOST, credentials=credentials)
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_JOB_QUEUE, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_JOB_QUEUE,
            body=json.dumps({"job_id": job_id, "data": data}),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        print(f"Error publishing to RabbitMQ: {str(e)}")

def prepare_signatory_data(data)->Signatory:
    return Signatory(
        name=f"{data.firstName} {data.lastName}",
        position=data.position,
        signature=data.signature
    )

@router.post("/generate/")
async def generate_certificate_endpoint(request: CertificateRequest):
    try:
        template_path = os.path.join("templates", "certificate_template2.pptx" if request.category == "2" else "certificate_template.pptx")
        output_dir = "temp_certificates"
        os.makedirs(output_dir, exist_ok=True)

        date = jdatetime.datetime.now().strftime("%Y/%m/%d")
        cert_id = request.certificateId or str(uuid.uuid4()).upper()
        signatory_data = prepare_signatory_data(request.course.signatory)
        text_data = {
            "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
            "name": f"{request.user.firstName} {request.user.lastName}",
            "national": request.user.nationalId,
            "course": request.course.name,
            "org": request.course.organizingUnit,
            "date": request.course.date,
            "time": request.course.time,
            "issue": date,
            "unique": cert_id,
            "number": request.certificateNumber,
            "signatory": signatory_data.name,
            "position": signatory_data.position
           }
        image_data = {
            "photo": safe_image(signatory_data.signature),
            "logo": safe_image(request.course.unitStamp),
        }
        if request.category == "2":
            signatory2_data = prepare_signatory_data(request.course.signatory2)
            text_data.update({
                "signatory2": signatory2_data.name,
                "position2": signatory2_data.position
            })
            image_data.update({
                "photo2": safe_image(signatory2_data.signature),
                "logo2": safe_image(request.course.unitStamp2 or "")
            })

        qr_data = {}
        if request.qr_url or cert_id:
            qr_data["url"] = request.qr_url or f"https://my.site/cert/{cert_id}"

        job_data = {
            "template_path": template_path,
            "output_dir": output_dir,
            "text_data": text_data,
            "image_data": image_data,
            "qr_data": qr_data,
            "job_id": cert_id
        }
        publish_to_rabbitmq(job_data, cert_id)
        
        
        return JSONResponse(
            status_code=202,
            content={"job_id": cert_id, "status": "queued", "message": "Certificate generation queued"}
        )
    except Exception as e:
        print(f"Error generating certificate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

        # pptx_path = await generate_certificate(
        #     template_path=template_path,
        #     output_dir=output_dir,
        #     text_data=text_data,
        #     image_data=image_data,
        #     qr_data=qr_data,
        # )

        # pdf_path = await convert_to_pdf(pptx_path, output_dir)

    #     return FileResponse(
    #         pdf_path,
    #         media_type="application/pdf",
    #         filename=f"certificate_{cert_id}.pdf"
    #     )
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

@router.get("/{certificate_id}")
async def get_certificate(certificate_id: str):
    pdf_path = f"temp_certificates/certificate_{certificate_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"certificate_{certificate_id}.pdf"
    )