# test_notification.py
import pika
import json
# import logging

# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)

def publish_test_notification(job_id):
    credentials = pika.PlainCredentials("certuser", "securepassword123")
    parameters = pika.ConnectionParameters(
        host="localhost",
        port=9105,
        virtual_host="tenant1",
        credentials=credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue="certificate_notifications", durable=True)
    notification = {"job_id": job_id, "status": "completed", "pdf_path": "test.pdf"}
    channel.basic_publish(
        exchange="",
        routing_key="certificate_notifications",
        body=json.dumps(notification),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(f"Published test notification for job {job_id}: {notification}")
    connection.close()

if __name__ == "__main__":
    publish_test_notification("abbsubadk2564")  # Replace with NEW_JOB_ID if needed