import pika
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 9105  # Updated to match docker-compose.yml
RABBITMQ_VHOST = "tenant1"
RABBITMQ_USER = "certuser"
RABBITMQ_PASS = "securepassword123"
RABBITMQ_JOB_QUEUE = "certificate_jobs"
RABBITMQ_NOTIFICATION_QUEUE = "certificate_notifications"

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, virtual_host=RABBITMQ_VHOST, credentials=credentials)

try:
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    print("Connected successfully!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")