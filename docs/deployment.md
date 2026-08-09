# AxonForge Canlıya Geçiş Kılavuzu (Deployment Guide)

Bu kılavuz, AxonForge terminalini Vercel, Railway, Supabase ve Redis altyapısını kullanarak canlıya almanın tüm adımlarını, çevre değişkenlerini, veritabanı göçlerini ve acil durum geri alma (rollback) senaryolarını açıklar.

---

## 1. CANLIYA ALIM ADIMLARI VE DÜZENİ (DEPLOYMENT ORDER)

Entegrasyon tutarlılığı için canlıya alım işlemlerini kesinlikle aşağıdaki sırayla uygulayın:

```text
1. Supabase Kurulumu & Schema Audit
        ↓
2. Veritabanı Migration Upgrade (Alembic)
        ↓
3. Redis Önbellek & Görev Kuyruğu (Railway)
        ↓
4. Railway Celery Worker Servisleri
        ↓
5. Railway FastAPI API Servisi
        ↓
6. Backend Sağlık ve Hazırlık Doğrulaması (/health, /ready)
        ↓
7. Vercel Frontend Dağıtımı
        ↓
8. Uçtan Uca Duman Testi (Smoke Test)
```

---

## 2. VERİTABANI - SUPABASE POSTGRESQL KURULUMU

1. **Supabase Projesi Oluşturma:** Supabase üzerinde yeni bir proje oluşturun ve veritabanı şifrenizi belirleyin.
2. **DATABASE_URL Tanımlama:** Veritabanı bağlantı dizesini (`connection string`) not edin. Canlı ortamda SSL bağlantısının zorunlu olduğunu unutmayın (`?sslmode=require` parametresini ekleyin).
3. **Migrations (Alembic):**
   * Yerel terminalinizde `DATABASE_URL` çevre değişkenini Supabase bağlantı dizenizle güncelleyin.
   * Supabase şemasını güncellemek için şu komutu koşturun:
     ```bash
     python -m alembic upgrade head
     ```
   * *Not:* Migration başarısız olursa canlıya çıkış durdurulacaktır.

---

## 3. ÖNBELLEK & GÖREV KUYRUĞU - REDIS KURULUMU

1. **Railway Redis:** Railway paneli üzerinden yeni bir Redis servisi ekleyin.
2. **URL Eşleme:** Redis servisinin özel ağ bağlantı adresini (`REDIS_URL`) kopyalayarak backend ve worker servislerinin çevre değişkenlerine ekleyin.

---

## 4. RAILWAY WORKERS & API SERVİSLERİ

Railway üzerinde 2 adet ana servis tanımlanacaktır (ikisi de aynı GitHub deposuna bağlanır):

### A. FastAPI API Servisi
*   **Build Command:** Dockerfile tabanlı build (`docker/backend.Dockerfile`) otomatik çalışır.
*   **Start Command:**
    ```bash
    uvicorn apps.api.app.main:app --host 0.0.0.0 --port $PORT
    ```
*   **Healthcheck Path:** `/health` (timeout 120s)

### B. Celery Worker Servisi (Asenkron Görevler)
*   **Build Command:** Dockerfile tabanlı build (`docker/backend.Dockerfile`) otomatik çalışır.
*   **Start Command:**
    ```bash
    celery -A packages.common.celery_app.celery_app worker --loglevel=info
    ```
*   **Healthcheck:** Celery worker port açmaz, bu nedenle tcp check yerine process health izlenir.

---

## 5. FRONTEND - VERCEL NEXT.JS KURULUMU

1. Vercel paneline giriş yapın ve projenizi GitHub üzerinden ekleyin.
2. **Çevre Değişkeni:** `NEXT_PUBLIC_API_URL` değişkenini Railway API servisinin canlı URL'i (örn: `https://axonforge-api.up.railway.app`) olacak şekilde tanımlayın.
3. Vercel Next.js framework tespitini yaptıktan sonra derlemeyi (`npm run build`) başlatacaktır.

---

## 6. ACİL DURUM GERİ ALMA STRATEJİSİ (ROLLBACK PLAN)

Canlı ortamda kritik bir hata oluştuğunda sistemi hızlıca önceki çalışan duruma döndürmek için:

### A. Veritabanı Geri Alma (Database Migration Rollback)
Alembic üzerinde bir önceki şema versiyonuna dönmek için:
```bash
python -m alembic downgrade -1
```
*Uyarı:* Downgrade işlemi veri kaybına yol açabileceği için downgrade öncesinde mutlaka Supabase üzerinden anlık yedek (`pg_dump` veya Supabase Snapshot) alınmalıdır.

### B. Uygulama Versiyonu Geri Alma (Application Rollback)
*   **Railway:** Railway panelinde geçmiş çalışan deploy'u seçip **"Rollback"** butonuna basarak 10 saniye içinde önceki çalışan Docker imajına geri dönün.
*   **Vercel:** Vercel paneli üzerinden geçmiş başarılı derlemeyi **"Redeploy to Production"** seçeneği ile anında canlıya çekin.
