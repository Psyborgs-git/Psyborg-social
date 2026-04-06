from __future__ import annotations

from celery.schedules import crontab
from socialmind.scheduler.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "proxy-health-check": {
        "task": "socialmind.scheduler.tasks.check_proxy_health",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
}
