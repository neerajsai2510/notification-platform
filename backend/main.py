import asyncio
import json
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis

from fastapi import (
    FastAPI,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    HTTPException
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Notification
from .tasks import process_notification


Base.metadata.create_all(bind=engine)


class ConnectionManager:

    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message):
        disconnected = []

        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


async def redis_listener():
    redis_pubsub_url = os.getenv(
        "REDIS_PUBSUB_URL",
        "redis://localhost:6379/2"
    )

    redis_client = redis.Redis.from_url(
        redis_pubsub_url,
        decode_responses=True
    )

    pubsub = redis_client.pubsub()

    await pubsub.subscribe("notification_updates")

    print("Redis notification listener started.")

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0
            )

            if message:
                data = json.loads(message["data"])

                print(
                    f"Redis event received: {data}"
                )

                await manager.broadcast(data)

            await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        print("Redis notification listener stopping...")

    finally:
        await pubsub.unsubscribe("notification_updates")
        await pubsub.close()
        await redis_client.close()


@asynccontextmanager
async def lifespan(app: FastAPI):

    listener_task = asyncio.create_task(redis_listener())

    yield

    listener_task.cancel()

    try:
        await listener_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://172.27.222.212:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from pydantic import BaseModel, Field


class NotificationRequest(BaseModel):
    recipient: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=500
    )


@app.get("/")
def root():
    return {
        "message": "Notification Platform API is running"
    }


@app.post("/notifications")
def create_notification(
    notification: NotificationRequest,
    db: Session = Depends(get_db)
):
    try:
        new_notification = Notification(
            recipient=notification.recipient.strip(),
            message=notification.message.strip()
        )

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        process_notification.delay(new_notification.id)

        return {
            "id": new_notification.id,
            "recipient": new_notification.recipient,
            "message": new_notification.message,
            "status": new_notification.status
        }

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create notification"
        )

@app.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db)
):
    try:
        return db.query(Notification).all()

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch notifications"
        )


@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)

    print("WebSocket client connected.")

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected.")
