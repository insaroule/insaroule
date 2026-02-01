import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.development")

app = Celery("project")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-unread-messages-emails": {
        "task": "chat.tasks.send_email_unread_messages",
        "schedule": crontab(
            minute=f"*/{settings.EMAIL_NOTIFICATION_THRESHOLD_MINUTES}"
        ),
    },
    "daily-statistics": {
        "task": "carpool.tasks.compute_daily_statistics",  # Every day at 5:00 AM
        "schedule": crontab(hour=5, minute=0),
    },
    "delete-non-verified-accounts": {
        "task": "accounts.tasks.delete_non_verified_accounts",  # Every day at 6:00 AM
        "schedule": crontab(hour=6, minute=0),
    },
}
