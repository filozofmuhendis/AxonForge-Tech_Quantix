# AxonForge Production Readiness Audit

Bu rapor, AxonForge-Tech Quantix monoreposunun canlı ortama (Vercel, Railway, Supabase) çıkışı öncesindeki teknik denetim (audit) sonuçlarını listeler.

---

## 1. SİSTEM SINIFLANDIRMASI (PRODUCTION CLASS)

| Bileşen | Durum | Detaylar |
| :--- | :--- | :--- |
| **Frontend (Next.js)** | `READY` | Vercel üzerinde derlenmeye uygun, Türkçe dil kuralları ve Celery polling yapısı tam entegre. |
| **Backend (FastAPI)** | `READY` | Railway üzerinde `$PORT` ve `0.0.0.0` uyuşumu tam, hata yakalama middleware'leri devrede. |
| **PostgreSQL (Supabase)** | `READY` | SQLAlchemy modelleri hazır, 23 tablo için ilk Alembic migration'ı tamamlandı. SQLite fallback bulunmamaktadır. |
| **Önbellek & Kuyruk (Redis)** | `READY` | Celery broker ve result backend olarak yapılandırıldı. |
| **Aracı Kurum (Broker)** | `READY` | `PAPER_TRADING=true`, `AUTO_TRADING=false` ve `ALLOW_REAL_BROKER=false` korumaları devrede. |
| **Geriye Dönük Test (Backtesting)** | `READY` | Asenkron Celery görevine ve frontend polling yapısına bağlandı. |
| **Nicel Motor (Quant Engine)** | `READY` | Vektörize indikatörler, rejim saptama ve analog getiri hesapları doğrulandı. |
| **ML Engine** | `READY` | XGBoost entegrasyonu, model arşivi ve drift takibi tamamlandı. |
| **Market Data Providers** | `NEEDS_FIX` | Çoklu sağlayıcı abstraction'ları ve fallback router'ı çalışıyor; ancak rate-limit ve token yokluğunda çökme riskleri üretim ayarlarıyla iyileştirilmeli. |
| **Background Workers** | `NEEDS_FIX` | Celery kuyruğu dışında kalan `market_data_worker`, `news_worker`, `feature_worker` ve `prediction_worker` gibi bağımsız infinite-loop betikleri, Celery/Redis entegrasyonuyla merkezi asenkron işler haline getirilmeli. |
| **Gözlemlenebilirlik (Observability)** | `NEEDS_FIX` | `/health` ve `/ready` durumları çalışıyor; ancak `/system/status` altında tüm harici sağlayıcıların (Twelve Data, Finnhub, FRED, TCMB) durumlarını detaylı gösteren veri sağlayıcı status paneli zenginleştirilmeli. |
| **Güvenlik (Security)** | `READY` | Çevre değişkenleri ayrıştırıldı, dynamic CORS entegre edildi. Git geçmişi taranıp hiçbir gizli anahtarın sızdırılmadığı doğrulandı. |

---

## 2. GÖZLEMLENEN PROBLEMLER (FINDINGS)

### Finding #1: Bağımsız Arka Plan Worker Betiklerinin Kuyruğa Bağlanmaması
*   **Severity:** `HIGH`
*   **Location:** [workers/](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/workers/) dizinindeki `market_data_worker.py`, `news_worker.py`, `feature_worker.py`, `prediction_worker.py` ve `maintenance_worker.py` dosyaları.
*   **Problem:** Bu betikler sonsuz döngü (`while True`) veya tek seferlik tetiklenen bağımsız dosyalar şeklinde çalışıyor. Railway üzerinde her biri için ayrı servis açılması kaynak tüketimini artırır ve takibi zorlaştırır.
*   **Production Impact:** CPU/bellek sızıntıları, takip edilemeyen işlem durumları ve asenkron kuyruk yönetimi dışında kalan kontrolsüz arka plan işlemleri.
*   **Required Fix:** Tüm bu worker mantıkları [workers/tasks.py](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/workers/tasks.py) dosyasına birer Celery görevi (`@celery_app.task`) olarak eklenmeli. Böylece tek bir Celery worker servisi tüm iş yükünü yönetebilir.
*   **Status:** `NEEDS_FIX`

### Finding #2: Veri Sağlayıcı Sağlık ve Bağlantı Statülerinin Eksik Raporlanması
*   **Severity:** `MEDIUM`
*   **Location:** [apps/api/app/main.py](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/apps/api/app/main.py) içindeki `/health` ve `/ready` uç noktaları ile [router.py](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/apps/api/app/api/router.py).
*   **Problem:** API gözlemlenebilirliği (`Observability`) için kritik olan `/system/status` uç noktası henüz mevcut değil. Hangi sağlayıcıların (TwelveData, Finnhub, FRED, TCMB, Ollama vb.) aktif, yetersiz (DEGRADED) veya yapılandırılmamış (NOT_CONFIGURED) olduğu izlenemiyor.
*   **Production Impact:** Canlı ortamda sağlayıcı API anahtarları tükendiğinde veya rate-limit yendiğinde sistem yöneticisinin durumdan haberdar olamaması.
*   **Required Fix:** `/system/status` uç noktası FastAPI API router'ına eklenmeli ve tüm servislerin (DB, Redis, LLM, Veri Sağlayıcıları) durumlarını dinamik olarak denetleyip Türkçe raporlamalı.
*   **Status:** `NEEDS_FIX`

### Finding #3: Next.js Frontend Sert Kodlanmış API Adresi Varsayımı
*   **Severity:** `HIGH`
*   **Location:** [apps/web/src/app/page.tsx](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/apps/web/src/app/page.tsx) (satır 9: `const API_BASE = 'http://localhost:8000/api/v1';`) ve sağlık kontrol fonksiyonları.
*   **Problem:** İstemci tarafı doğrudan `http://localhost:8000` adresine istek gönderiyor. Canlıya alımda bu durum hata verecektir.
*   **Production Impact:** Frontend uygulamasının canlı backend'e bağlanamaması ve çalışmaması.
*   **Required Fix:** `API_BASE` ve ilgili tüm istekler `process.env.NEXT_PUBLIC_API_URL` çevre değişkeninden okunacak şekilde düzenlenmeli.
*   **Status:** `NEEDS_FIX`

### Finding #4: Veritabanı ve İş Takip Kalıcılığı (Job Persistence)
*   **Severity:** `HIGH`
*   **Location:** [workers/tasks.py](file:///c:/Users/bilal/OneDrive/Belgeler/My Repo/AxonForge-Tech_Quantix/workers/tasks.py) ve asenkron backtest akışı.
*   **Problem:** Celery görev durumları ve sonuçları sadece geçici olarak Redis üzerinde tutuluyor. Görev bittiğinde veya Redis yeniden başladığında geçmiş işlemler kaybolabilir.
*   **Production Impact:** Kullanıcının geçmiş backtest sonuçlarına veya sistem veri çekme işlerinin durum geçmişine erişememesi.
*   **Required Fix:** `BacktestRun` ve genel `Job` statülerinin her adımda (QUEUED, RUNNING, COMPLETED, FAILED) Supabase PostgreSQL veritabanındaki tablolara yazılması tam olarak doğrulanmalı ve eksik loglar tamamlanmalı.
*   **Status:** `NEEDS_FIX`
