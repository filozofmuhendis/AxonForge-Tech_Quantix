# AxonForge Veritabanı Şeması (Database Schema)

AxonForge, ilişkisel veri bütünlüğünü ve zaman serisi (time-series) tutarlılığını sağlamak için **yalnızca PostgreSQL** veritabanını destekler. SQLite gibi gömülü alternatifler devre dışı bırakılmıştır.

## 1. Veritabanı Tablo Yapıları

Sistem aşağıdaki ana tablolardan oluşmaktadır (bkz: `packages/common/models.py`):

*   **`assets` & `price_bars` / `intraday_bars`:**
    *   Hisse senetleri ve endekslerin üst verilerini ve OHLCV fiyat barlarını tutar.
    *   Fiyat barlarında veri kalitesi ve sızıntı takibi için `provider_name`, `latency_ms`, `freshness_seconds` ve `data_quality_score` alanları bulunur.

*   **`models` & `model_predictions`:**
    *   Makine öğrenimi modellerinin öznitelik listeleri, eğitim aralıkları, Brier skorları ve anlık durumları (PRODUCTION, DEGRADED) ile olasılıksal tahmin kayıtlarını tutar.

*   **`signals` & `trade_proposals`:**
    *   Sinyal skoru, 6 güven parametresinden oluşan `confidence_breakdown` JSON'u ve tüm veri kaynaklarını izleyen `decision_trace` JSON'unu barındırır.
    *   İşlem teklifleri ise sinyale bağlı giriş, stop, hedef ve risk tutarını kaydeder.

*   **`decision_journal`:**
    *   İşlem açılmadan önce girilen yatırım tezi (thesis_text), giriş gerekçesi (entry_reasoning) ve işlem kapatıldığında oluşan kâr/zarar ile retrospektif yapay zeka hata analizini (post_trade_evaluation) tutar.

*   **`portfolios` & `portfolio_positions` & `portfolio_transactions`:**
    *   Portföy bakiyesi, hisse miktarları, ortalama maliyet bazları ve geçmiş alım-satım işlemlerini komisyon/slippage detaylarıyla kaydeder.

## 2. Veri Lineage / İzleme Günlüğü (Decision Trace JSON)

Her sinyal üretildiğinde oluşan `decision_trace` sütununun örnek şeması:
```json
{
  "symbol": "THYAO.IS",
  "signal_type": "BUY",
  "composite_score": 75.5,
  "timestamp": "2026-08-09T12:00:00Z",
  "weights": {
    "technical": 0.2,
    "momentum": 0.2,
    "ml_probability": 0.3,
    "fundamental": 0.15,
    "news": 0.05,
    "macro": 0.1
  },
  "inputs": {
    "technical": 75.0,
    "momentum": 80.0,
    "ml_probability": 0.65,
    "fundamental": 70.0,
    "news_sentiment": 0.2,
    "macro_score": 60.0,
    "market_regime": "BULL",
    "data_quality_score": 95.0
  },
  "confidence_breakdown": {
    "signal_confidence": 0.755,
    "model_calibration": 0.85,
    "data_quality": 0.95,
    "historical_analog_strength": 0.78,
    "market_regime_stability": 0.80,
    "risk_confidence": 0.80
  }
}
```
