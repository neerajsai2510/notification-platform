from .tasks import process_notification
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Notification

Base.metadata.create_all(bind=engine)

app = FastAPI()


class NotificationRequest(BaseModel):
    recipient: str
    message: str


@app.get("/")
def root():
    return {"message": "Notification Platform API is running"}


@app.post("/notifications")
def create_notification(
    notification: NotificationRequest,
    db: Session = Depends(get_db)
):
    new_notification = Notification(
        recipient=notification.recipient,
        message=notification.message
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
@app.get("/notifications")
def get_notifications(db: Session = Depends(get_db)):
    notifications = db.query(Notification).all()

    return notifications
