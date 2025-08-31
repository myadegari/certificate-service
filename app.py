from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints.certificates import router as certificates_router
import pika
import json
from typing import Dict
import asyncio
from contextlib import asynccontextmanager



# RabbitMQ connection settings
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 9105  # Updated to match docker-compose.yml
RABBITMQ_VHOST = "tenant1"
RABBITMQ_USER = "certuser"
RABBITMQ_PASS = "securepassword123"
RABBITMQ_JOB_QUEUE = "certificate_jobs"
RABBITMQ_NOTIFICATION_QUEUE = "certificate_notifications"
# Track WebSocket clients per job_id
websocket_clients: Dict[str, list[WebSocket]] = {}


async def consume_notifications():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_NOTIFICATION_QUEUE, durable=True)
    
    def callback(ch, method, properties, body):
        message = json.loads(body)
        job_id = message["job_id"]
        if job_id in websocket_clients:
            for ws in websocket_clients[job_id]:
                asyncio.create_task(ws.send_json(message))
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    channel.basic_consume(queue=RABBITMQ_NOTIFICATION_QUEUE, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (replaces @app.on_event("startup"))
    task = asyncio.create_task(consume_notifications())
    print("Application started - notification consumer running")
    
    yield  # This is where your application runs
    
    # Shutdown logic (replaces @app.on_event("shutdown"))
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("Application shutting down - notification consumer stopped")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",'*'],  # Replace with your Next.js app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(certificates_router, prefix="/certificates", tags=["certificates"])

@app.websocket("/ws/certificates/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    if job_id not in websocket_clients:
        websocket_clients[job_id] = []
    websocket_clients[job_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        websocket_clients[job_id].remove(websocket)
        if not websocket_clients[job_id]:
            del websocket_clients[job_id]