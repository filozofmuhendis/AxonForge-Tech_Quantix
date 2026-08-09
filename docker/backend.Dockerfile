# Python 3.11 tabanlı Docker imajı
FROM python:3.11-slim

# Çalışma dizini oluşturma
WORKDIR /app

# Gerekli sistem kütüphanelerini kur
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY apps/ /app/apps/
COPY packages/ /app/packages/
COPY scripts/ /app/scripts/
COPY workers/ /app/workers/
COPY database/ /app/database/
COPY alembic.ini /app/alembic.ini


# Python Path ayarla
ENV PYTHONPATH=/app

# API portunu aç
EXPOSE 8000

# API başlatma komutu
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
