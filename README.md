# AxonForge Personal FinTech AI Platformu

AxonForge, bireysel kullanım için tasarlanmış, genişletilebilir ve gerçek finansal verilerle (BIST, ABD Borsaları, FX, Emtialar, Makroekonomik Faktörler) çalışan **kurumsal kalitede (production-grade) kişisel finansal zeka ve trading terminalidir.**

Bu sistem bir "AI stock picker" (yapay zeka hisse seçici) değildir. Bunun yerine, finansal matematiğin ve deterministik nicel hesaplamaların merkezde yer aldığı, Yapay Zeka Ajanının (LLM) ise karar gerekçelendirme (reasoning), haber/rapor analizi, stres testleri ve doğal dil terminal arayüzü olarak kullanıldığı katmanlı bir mimariye sahiptir.

---

## 1. ANA MİMARİ YAPI (SYSTEM ARCHITECTURE)

Sistem, deterministik finansal matematiği hiçbir koşulda yapay zekanın halüsinasyonlarına kurban etmemek için aşağıdaki veri akış zincirini takip eder:

```text
PİYASA VERİSİ (Yahoo Finance vb.)
          ↓
VERİ NORMALİZASYONU & KALİTE GEÇİDİ (0-100 Kalite Skoru)
          ↓
MATEMATİKSEL ÖZNİTELİK (FEATURE) ÜRETİMİ
          ↓
PİYASA REJİMİ ALGILAMA (BULL, BEAR, SIDEWAYS, CRISIS vb.)
          ↓
MAKİNE ÖĞRENİMİ OLASILIK TAHMİNİ (Random Forest, XGBoost vb.)
          ↓
TARİHSEL BENZER (ANALOG) DÖNEM ANALİZİ
          ↓
KOMPOZİT SİNYAL MOTORU (Strong Buy, Buy, Hold vb.) & GÜVEN AYRIŞTIRICISI
          ↓
PORTFÖY VE RİSK GEÇİDİ (VaR, Downside Risk, Freshness Kontrolleri)
          ↓
İŞLEM TEKLİFİ (Trade Proposal)
          ↓
KULLANICI ONAYI & SANAL ARACI KURUM (Paper Trading) İŞLEMİ
          ↓
KARAR GÜNLÜĞÜ (Decision Journal) & GERİYE DÖNÜK RETROSPEKTİF ANALİZ
```

---

## 2. ANAHTAR YETENEKLER

*   **Sadece PostgreSQL Desteği:** SQLite gibi geçici veritabanları kullanılmaz. PostgreSQL bağlantı kopması durumunda sistem `DATABASE_UNAVAILABLE` hata durumuna geçer.
*   **Ayrıştırılmış Güven Değeri (Decomposed Confidence):** Güven skoru tek bir yüzde olarak sunulmaz. Sinyal Gücü, Model Kalibrasyonu, Veri Kalitesi, Tarihsel Benzerlik, Rejim Kararlılığı ve Risk seviyesi olarak 6 farklı boyutta ayrıştırılır.
*   **Tarihsel Benzerlik Analizi (Analog Analysis):** Mevcut piyasa teknik özniteliklerini kosinüs benzerliği kullanarak geçmiş 10 yıl içindeki benzer dönemlerle eşleştirir ve sonraki getirilerin kazanma olasılığı dağılımını raporlar.
*   **Veri Sızıntısı (Leakage) Koruması:** Geriye dönük testler ve ML eğitim setleri, look-ahead bias ve future data sızıntılarını önlemek için zaman serisi yapısına uygun olarak kesin sınırlarla ayrılmıştır.
*   **Yatırım ve Karar Günlüğü:** Yatırım tezi, giriş gerekçesi, risk metrikleri ve sonrasındaki gerçekleşen kâr/zarar retro-AI değerlendirmesiyle loglanır.
*   **Yapay Zeka Hata Modu:** Ollama veya harici LLM servisleri kapalı olduğunda sistem `AI_AGENT_UNAVAILABLE` durumuna geçer. Ancak teknik analiz, portföy analitiği ve stres testleri deterministik olarak çalışmaya devam eder.
*   **Tamamen Türkçe:** Tüm terminal, grafik etiketleri, ajan yanıt şablonları ve sistem günlükleri tamamen Türkçe dilindedir.

---

## 3. KURULUM VE BAŞLATMA TALİMATLARI

Terminali Windows üzerinde yerel olarak ayağa kaldırmak için aşağıdaki adımları sırasıyla uygulayınız.

### 3.1 Ön Koşullar
*   **Python:** v3.11.x (Yüklü)
*   **Node.js:** v22.15.x (Yüklü)
*   **PostgreSQL:** Çalışır durumda bir PostgreSQL veritabanı örneği gereklidir.
*   **Ollama (İsteğe Bağlı):** Lokal LLM ajanı için Ollama sunucusunun başlatılmış ve `qwen2.5:14b-instruct` veya benzeri bir modelin indirilmiş olması önerilir.

---

### 3.2 Backend Kurulumu ve Başlatılması

1.  **Çevre Değişkenlerini Tanımlama:**
    Root dizindeki `.env.example` dosyasını `.env` olarak kopyalayın ve PostgreSQL bağlantı dizesi ile Ollama url adresinizi tanımlayın:
    ```bash
    copy .env.example .env
    ```

2.  **Gerekli Python Paketlerinin Kurulması:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Veritabanı Tablolarının Oluşturulması ve İlk Verilerin (Seed) Yüklenmesi:**
    Bu komut PostgreSQL veritabanına bağlanarak tüm tabloları sıfırdan oluşturacak ve varsayılan hisse/emtia tanımlarını yükleyecektir:
    ```bash
    python scripts/init_db.py
    ```

4.  **Backend Sunucusunun Başlatılması (FastAPI):**
    ```bash
    python -m uvicorn apps.api.app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    API servisleri başarıyla ayağa kalktığında tarayıcınızdan `http://localhost:8000/docs` adresine giderek otomatik OpenAPI dökümantasyonunu inceleyebilirsiniz.

---

### 3.3 Frontend Kurulumu ve Başlatılması

1.  **Frontend Klasörüne Geçiş ve Paket Kurulumu:**
    Yeni bir terminal açarak aşağıdaki komutu çalıştırın:
    ```bash
    cd apps/web
    npm install
    npm install lucide-react recharts
    ```

2.  **Next.js Geliştirici Sunucusunun Başlatılması:**
    ```bash
    npm run dev
    ```
    Kurulum tamamlandığında `http://localhost:3000` adresine giderek AxonForge Türkçe Trading Terminal arayüzüne erişebilirsiniz.

---

### 3.4 Otomatik Testlerin Çalıştırılması (Doğrulama)

Matematiksel işlevleri, sızıntı korumalarını ve veri kalitesi puanlayıcılarını test etmek için `pytest` kullanabilirsiniz:
```bash
pytest apps/api/tests/
```
