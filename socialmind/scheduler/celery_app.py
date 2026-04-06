from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from socialmind.config.settings import settings

celery_app = Celery("socialmind")

celery_app.conf.update(
    # Broker & backend
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    result_expires=86400,

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task routing
    task_routes={
        "socialmind.scheduler.tasks.execute_post": {"queue": "high"},
        "socialmind.scheduler.tasks.execute_dm_reply": {"queue": "high"},
        "socialmind.scheduler.tasks.engage_feed": {"queue": "normal"},
        "socialmind.scheduler.tasks.research_trends": {"queue": "low"},
        "socialmind.scheduler.tasks.health_check_proxy": {"queue": "low"},
        "socialmind.scheduler.tasks.collect_analytics": {"queue": "low"},
        "socialmind.scheduler.tasks.run_warmup": {"queue": "low"},
        "socialmind.scheduler.tasks.dispatch_campaign_tasks": {"queue": "normal"},
    },

    # Queue definitions
    task_queues=(
        Queue("high", Exchange("high"), routing_key="high", max_priority=10),
        Queue("normal", Exchange("normal"), routing_key="normal", max_priority=5),
        Queue("low", Exchange("low"), routing_key="low", max_priority=1),
    ),
    task_default_queue="normal",

    # Concurrency & execution
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Timeouts
    task_soft_time_limit=300,
    task_time_limit=360,

    # Retry behaviour
    task_max_retries=3,
    task_default_retry_delay=60,

    # Time
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,

    # Beat
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/data/celerybeat-schedule",
)

celery_app.conf.include = ["socialmind.scheduler.tasks"]

