import os
from celery import Celery
from packages.common.config import settings

# Celery uygulamasını tanımla
# Redis broker ve result backend URL'lerini config.py settings üzerinden yükler
redis_url = settings.REDIS_URL or "redis://localhost:6379/0"

celery_app = Celery(
    "axonforge",
    broker=redis_url,
    backend=redis_url
)

# Celery konfigürasyon parametreleri
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Worker hata durumunda görevleri yeniden deneme limitleri
    task_acks_late=True,
    worker_prefetch_multiplier=1
)

# Task dosyalarını otomatik bulması için kaydet
celery_app.autodiscover_tasks(["workers"])
