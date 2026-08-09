# AxonForge Sistem Mimarisi (Architecture)

AxonForge Personal FinTech AI Platformu, tamamen modüler, gevşek bağlı (loosely coupled) ve deterministik finansal matematiği en üst seviyede koruyan çok katmanlı bir mimariye sahiptir.

## 1. Canlı Altyapı Veri Akış Şeması (Production Data Flow)

Sistemin üretim ortamındaki canlı veri akışı aşağıdaki şemada belirtildiği gibidir:

```text
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │   VERCEL    │
                    │  Next.js    │
                    └──────┬──────┘
                           HTTPS
                            │
                            ▼
                    ┌─────────────┐
                    │   RAILWAY   │
                    │   FastAPI   │
                    └──────┬──────┘
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
          ▼                ▼                 ▼
     AI / Quant        Risk / Portfolio   API Services
          │                │                 │
          └────────────────┼─────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        ┌───────────┐             ┌──────────┐
        │  REDIS    │             │ SUPABASE │
        │ Queue     │             │PostgreSQL│
        │ Cache     │             │  Truth   │
        └─────┬─────┘             └────┬─────┘
              │                         │
       ┌──────┼────────┐                │
       ▼      ▼        ▼                │
     DATA    ML     BACKTEST             │
    WORKER  WORKER   WORKER              │
       │      │        │                 │
       └──────┴────────┴─────────────────┘
                           │
                           ▼
                    DECISION TRACE
                           │
                           ▼
                      AI RESPONSE
```

## 2. Mimari Bileşen Sorumlulukları

1.  **Vercel (Frontend / Sunum Katmanı):**
    *   Statik ve dinamik Next.js terminal sayfalarını barındırır.
    *   Railway backend sunucusuyla strictly HTTPS ve CORS kısıtlamaları altında haberleşir.
    *   Kullanıcıya veri güncelliği (freshness) bilgisini ve güven parametrelerini gösterir.

2.  **Railway (FastAPI / İş Mantığı Katmanı):**
    *   Deterministik finansal hesaplama kütüphanelerini barındırır.
    *   Ağır hesaplamaları (backtest, veri çekme vb.) Redis kuyruğu üzerinden worker'lara delege eder.
    *   Sağlık (/health) ve hazır olma (/ready) durumlarını denetler.

3.  **Supabase (PostgreSQL / Tek Veri Doğrusu):**
    *   Tüm verilerin (varlık tanımları, fiyatlar, modeller, sinyaller, karar günlüğü) kalıcı olarak saklandığı veritabanıdır.
    *   SQLite vb. geçici veritabanı yedekleri canlı ortamda kesinlikle kullanılmaz.

4.  **Redis (Queue & Cache / Geçici Durum Yönetimi):**
    *   İş kuyruğunu (Celery) ve geçici önbellekleri tutar. Kalıcı finansal veri barındırmaz.

5.  **Arka Plan İşçileri (Railway Workers):**
    *   Celery üzerinden asenkron olarak fiyat çekme, ML tahminleme ve strateji test süreçlerini yönetir.
