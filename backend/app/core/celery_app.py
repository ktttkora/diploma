"""
Celery application configuration.

Configures Celery worker with Redis broker and task routing.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import settings


# Create Celery app
celery_app = Celery(
    "hustl_analyzer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.video_tasks", "app.tasks.cleanup_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-expired-uploads": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired_uploads",
        "schedule": crontab(minute=0),  # Every hour
    },
}


if __name__ == "__main__":
    celery_app.start()
