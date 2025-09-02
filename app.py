import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints.certificates import router as certificates_router
import pika
import json
from typing import Dict
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from redis import asyncio as aioredis

load_dotenv()

# RabbitMQ connection settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST","")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT","")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST","")
RABBITMQ_USER = os.getenv("RABBITMQ_USER","")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS","")
RABBITMQ_JOB_QUEUE = os.getenv("RABBITMQ_JOB_QUEUE","")
RABBITMQ_NOTIFICATION_QUEUE = os.getenv("RABBITMQ_NOTIFICATION_QUEUE","")

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST","")
REDIS_PORT = os.getenv("REDIS_PORT","")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD","")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"

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
        try:
            # Decode bytes to string before parsing JSON
            message = json.loads(body.decode('utf-8'))
            job_id = message["job_id"]
            if job_id in websocket_clients:
                for ws in websocket_clients[job_id]:
                    # Ensure we're sending valid JSON
                    asyncio.create_task(ws.send_json(message))
                print(f"Broadcasting status update for job {job_id}: {message['status']}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {body[:100]}")  # Print first 100 chars for debugging
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            print(f"Error in notification callback: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    channel.basic_consume(queue=RABBITMQ_NOTIFICATION_QUEUE, on_message_callback=callback, auto_ack=False)
    print("Starting notification consumer...")
    channel.start_consuming()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (replaces @app.on_event("startup"))
    app.state.redis = aioredis.from_url(
        REDIS_URL,
        decode_responses=True,
        encoding="utf-8"
    )
    task = asyncio.create_task(consume_notifications())
    print("Application started - notification consumer running")
    
    yield  # This is where your application runs
    
    # Shutdown logic (replaces @app.on_event("shutdown"))
    # Cleanup
    await app.state.redis.close()
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

async def get_job_status(job_id: str) -> dict:
    """Get current job status from RabbitMQ queue"""
    try:
        redis_status = await app.state.redis.get(f"job_status:{job_id}")
        if redis_status:
            return json.loads(redis_status)
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Check if there are any messages in the notification queue for this job_id
        method_frame, header_frame, body = channel.basic_get(RABBITMQ_NOTIFICATION_QUEUE)
        if method_frame:
            message = json.loads(body)
            if message["job_id"] == job_id:
                channel.basic_ack(method_frame.delivery_tag)
                return message
            # Put the message back if it's not for this job
            channel.basic_reject(method_frame.delivery_tag, requeue=True)
        
        connection.close()
        return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        print(f"Error getting job status: {str(e)}")
        return {"job_id": job_id, "status": "unknown"}

@app.websocket("/ws/certificates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Get job_id from query parameters
    job_id = websocket.query_params.get("job_id")
    if not job_id:
        await websocket.close(code=1008, reason="job_id is required")
        return
    
    try:
        # Send initial job status
        initial_status = await get_job_status(job_id)
        await websocket.send_json(initial_status)
        
        if job_id not in websocket_clients:
            websocket_clients[job_id] = []
        websocket_clients[job_id].append(websocket)
        
        while True:
            # Only accept valid JSON messages
            try:
                data = await websocket.receive_json()  # Changed from receive_text
                print(f"Received message from client: {data}")
            except json.JSONDecodeError:
                print("Received invalid JSON message")
                continue
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        print(f"Client disconnected for job_id: {job_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        if job_id in websocket_clients and websocket in websocket_clients[job_id]:
            websocket_clients[job_id].remove(websocket)
            if not websocket_clients[job_id]:
                del websocket_clients[job_id]