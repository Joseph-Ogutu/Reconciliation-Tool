import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Mini_Reconciliation_Tool.settings')

app = Celery('Mini_Reconciliation_Tool')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()