from __future__ import annotations

from celery.schedules import crontab

from socialmind.scheduler.celery_app import celery_app

CELERY_BEAT_SCHEDULE: dict[str, dict] = {
    "health-check-proxies": {
        "task": "socialmind.scheduler.tasks.health_check_proxy",
        "schedule": crontab(minute="*/30"),
    },
    "research-trends-instagram-fitness": {
        "task": "socialmind.scheduler.tasks.research_trends",
        "schedule": crontab(hour="*/6", minute=0),
        "args": ("instagram", "fitness"),
    },
    "research-trends-tiktok-general": {
        "task": "socialmind.scheduler.tasks.research_trends",
        "schedule": crontab(hour="*/6", minute=5),
        "args": ("tiktok", "general"),
    },
    "collect-analytics": {
        "task": "socialmind.scheduler.tasks.collect_analytics",
        "schedule": crontab(hour="*/4", minute=15),
    },
    # DM check — every 15 minutes for all active accounts
    "check-dms-all-accounts": {
        "task": "socialmind.scheduler.tasks.dispatch_campaign_tasks",
        "schedule": crontab(minute="*/15"),
    },
    # Campaign dispatch — every minute
    "dispatch-campaign-tasks": {
        "task": "socialmind.scheduler.tasks.dispatch_campaign_tasks",
        "schedule": crontab(minute="*/1"),
    },
}

celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE

