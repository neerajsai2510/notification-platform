from .celery_app import celery_app


@celery_app.task
def process_notification(notification_id):
    print(f"Processing notification {notification_id}")

    return {
        "notification_id": notification_id,
        "status": "PROCESSED"
    }
