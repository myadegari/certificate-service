import pika
import json
import asyncio
# import logging
from services.certification_generator import generate_certificate, convert_to_pdf, safe_image
from pathlib import Path
import time
from pika.exceptions import AMQPConnectionError


# Configure logging
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 9105
RABBITMQ_VHOST = "tenant1"
RABBITMQ_USER = "certuser"
RABBITMQ_PASS = "securepassword123"
RABBITMQ_JOB_QUEUE = "certificate_jobs"
RABBITMQ_NOTIFICATION_QUEUE = "certificate_notifications"

def publish_notification(job_id: str, status: str, pdf_path: str = ""):
    print(f"Publishing notification for job {job_id}: status={status}, pdf_path={pdf_path}")
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameter = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials
    )
    max_retries = 5
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(parameter)

            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_NOTIFICATION_QUEUE, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_NOTIFICATION_QUEUE,
                body=json.dumps({"job_id": job_id, "status": status, "pdf_path": pdf_path}),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            connection.close()
        except AMQPConnectionError as e:
            print(f"Error publishing notification for job {job_id}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Worker failed to start.")
                raise
        except Exception as e:
            print(f"Unexpected error in worker: {str(e)}")
            raise

def callback(ch, method, properties, body):
    job = json.loads(body)
    job_id = job["job_id"]
    data = job["data"]
    print(f"Processing job {job_id}")
    
    image_data = {k: safe_image(v) for k, v in data["image_data"].items()}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print(f"Generating PPTX...")
        print(f"Generated PPTX: {data['template_path']}")
        pptx_path = loop.run_until_complete(
            generate_certificate(
                template_path=data["template_path"],
                output_dir=data["output_dir"],
                text_data=data["text_data"],
                image_data=image_data,
                qr_data=data["qr_data"]
            )
        )
        pptx_path = str(Path(pptx_path).resolve())
        print(f"Generated PPTX: {pptx_path}")
        print(f"Converting PPTX to PDF...")
        print(f"Generated PDF: {data['output_dir']}")
        pdf_path = loop.run_until_complete(
            convert_to_pdf(pptx_path, data["output_dir"])
        )
        print(f"Generated certificate {job_id}: {pdf_path}")
        publish_notification(job_id, "completed", pdf_path)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        publish_notification(job_id, "failed")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        loop.close()

def main():
    print(f"Starting worker, connecting to {RABBITMQ_HOST}:{RABBITMQ_PORT}, vhost={RABBITMQ_VHOST}")
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameter = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials
        )
    try:
        connection = pika.BlockingConnection(
            parameter
        )
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_JOB_QUEUE, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=RABBITMQ_JOB_QUEUE, on_message_callback=callback)
        print(" [*] Waiting for messages. To exit press CTRL+C")
        # logger.info("Worker started, waiting for jobs...")
        channel.start_consuming()
    except Exception as e:
        print(f"Error in worker: {str(e)}")
        # logger.error(f"Error in worker: {str(e)}")

if __name__ == "__main__":
    main()