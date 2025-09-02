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
from dotenv import load_dotenv
from pathlib import Path
import os
import redis

load_dotenv()

# RabbitMQ connection settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST","")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT","")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST","")
RABBITMQ_USER = os.getenv("RABBITMQ_USER","")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS","")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE","")
RABBITMQ_NOTIFICATION_QUEUE = os.getenv("RABBITMQ_NOTIFICATION_QUEUE","")

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", "")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    password=REDIS_PASSWORD,
    decode_responses=True
)

def publish_notification(job_id: str, status: str, pdf_path: str = "", error_message: str = ""):
    """Publish job status notification to RabbitMQ queue and Redis with retry mechanism"""
    print(f"Publishing notification for job {job_id}: status={status}, pdf_path={pdf_path}")
    
    message = {
        "job_id": job_id,
        "status": status,
        "pdf_path": pdf_path,
        "timestamp": time.time()
    }
    if error_message and status == "failed":
        message["error"] = error_message

    # Store status in Redis first
    try:
        # Store for 24 hours
        redis_client.setex(
            f"job_status:{job_id}",
            86400,  
            json.dumps(message)
        )
    except Exception as e:
        print(f"Error storing status in Redis for job {job_id}: {str(e)}")

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameter = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,  # Add heartbeat to prevent connection timeouts
        blocked_connection_timeout=300
    )
    
    max_retries = 5
    retry_delay = 5  # seconds
    
    message = {
        "job_id": job_id,
        "status": status,
        "pdf_path": pdf_path,
        "timestamp": time.time()
    }
    if error_message and status == "failed":
        message["error"] = error_message

    for attempt in range(max_retries):
        connection = None
        try:
            connection = pika.BlockingConnection(parameter)
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_NOTIFICATION_QUEUE, durable=True)
            
            # Publish with mandatory flag to ensure message delivery
            channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_NOTIFICATION_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json',
                    timestamp=int(time.time())
                ),
                mandatory=True
            )
            
            connection.close()
            print(f"Successfully published notification for job {job_id}")
            return True
            
        except AMQPConnectionError as e:
            print(f"Connection error publishing notification for job {job_id}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                print(f"Max retries reached for job {job_id}. Failed to publish notification.")
                raise
        except Exception as e:
            print(f"Unexpected error publishing notification for job {job_id}: {str(e)}")
            raise
        finally:
            try:
                if connection is not None and connection.is_open:
                    connection.close()
            except Exception:
                pass

async def process_images(data):
    image_data = {}
    for k, v in data["image_data"].items():
        saved_path = await safe_image(v)
        image_data[k] = saved_path
    return image_data

def callback(ch, method, properties, body):
    job = json.loads(body)
    job_id = job["job_id"]
    data = job["data"]
    print(f"Processing job {job_id}")
    
    # image_data = {k: safe_image(v) for k, v in data["image_data"].items()}
        # Update initial status in Redis
    redis_client.setex(
        f"job_status:{job_id}",
        86400,
        json.dumps({"job_id": job_id, "status": "processing", "timestamp": time.time()})
    )
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        image_data = loop.run_until_complete(process_images(data))
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
        error_msg = str(e)
        print(f"Error processing job {job_id}: {error_msg}")
        publish_notification(job_id, "failed", error_message=error_msg)
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