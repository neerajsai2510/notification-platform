from celery import Celery

celery_app = Celery(
    "notification_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["backend.tasks"]
)
