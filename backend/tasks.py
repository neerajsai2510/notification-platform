import json
import os
import redis

from .celery_app import celery_app
from .database import SessionLocal
from .models import Notification


redis_pubsub_url = os.getenv(
    "REDIS_PUBSUB_URL",
    "redis://localhost:6379/2"
)

redis_client = redis.Redis.from_url(
    redis_pubsub_url,
    decode_responses=True
)


def publish_notification_update(notification):
    redis_client.publish(
        "notification_updates",
        json.dumps({
            "id": notification.id,
            "recipient": notification.recipient,
            "message": notification.message,
            "status": notification.status,
            "retry_count": notification.retry_count
        })
    )


@celery_app.task(bind=True, max_retries=3)
def process_notification(self, notification_id):
    db = SessionLocal()

    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if not notification:
            return {
                "notification_id": notification_id,
                "status": "NOT_FOUND"
            }

        notification.status = "PROCESSING"
        db.commit()
        publish_notification_update(notification)

        print(
            f"Processing notification {notification_id}, "
            f"attempt {notification.retry_count + 1}"
        )

        # Simulate delivery failure
        if notification.retry_count < 2:
            notification.retry_count += 1
            notification.status = "FAILED"
            db.commit()
            publish_notification_update(notification)

            raise Exception("Simulated notification delivery failure")

        # Successful delivery
        notification.status = "DELIVERED"
        db.commit()
        publish_notification_update(notification)

        return {
            "notification_id": notification_id,
            "status": "DELIVERED"
        }

    except Exception as error:

        db.rollback()

        notification = db.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if notification:
            notification.status = "FAILED"
            db.commit()
            publish_notification_update(notification)

        # Permanent failure
        if self.request.retries >= self.max_retries:
            print(
                f"Notification {notification_id} permanently failed "
                f"after {self.request.retries} retries."
            )

            if notification:
                notification.status = "FAILED"
                db.commit()
                publish_notification_update(notification)

            return {
                "notification_id": notification_id,
                "status": "FAILED",
                "retry_count": notification.retry_count
                if notification else None
            }

        # Exponential backoff
        retry_delay = 2 ** (self.request.retries + 1)

        print(
            f"Retrying notification {notification_id} "
            f"in {retry_delay} seconds..."
        )

        raise self.retry(
            exc=error,
            countdown=retry_delay
        )

    finally:
        db.close()
