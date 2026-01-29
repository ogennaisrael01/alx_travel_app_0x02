from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

app = Celery("alx_travel_app")

