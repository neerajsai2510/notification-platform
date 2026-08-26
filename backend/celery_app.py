import os

from celery import Celery


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379"
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/1"
)


celery_app = Celery(
    "notification_worker",
    broker=REDIS_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["backend.tasks"]
)
