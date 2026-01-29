from celery import Celery
import os
import logging

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

app = Celery("alx_travel_app")
app.config_from_object("django.cong:settings", "CELERY")

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.debug(f"[!] Request: {self.request}")

