# AxonForge Yapay Zeka Ajanı (AI Agent)

AI Agent, AxonForge trading terminalinin doğal dil arayüzünü ve araç koordinasyonunu (tool orchestration) yöneten katmandır.

## 1. Araç Tabanlı Mimari (Tool-Based Architecture)

Yapay zeka ajanı veritabanına doğrudan rastgele SQL sorguları atamaz. Bunun yerine, backend tarafında tanımlanmış olan deterministik araçları (tools) tetikler (bkz: `packages/ai_agent/tools.py`):

*   `get_historical_prices()`: Belirli bir hissenin geçmiş fiyat barlarını çeker.
*   `calculate_technical_indicators()`: Teknik göstergeleri ve destek/direnç noktalarını hesaplar.
*   `get_portfolio_status()`: Açık portföy pozisyonlarını, kâr/zararı ve dağılımları raporlar.
*   `run_stress_test_scenario()`: Portföye şok senaryoları uygulayarak etki simüle eder.
*   `generate_asset_trade_proposal()`: Hissenin sinyal skorlarını hesaplar ve işlem önerisi üretir.

## 2. LLM Çevrimdışı Modu (Graceful Degradation)

Eğer yerel Ollama sunucusuna veya harici LLM sağlayıcısına (OpenAI/Anthropic) bağlanılamazsa, ajan `check_llm_health()` fonksiyonunda `AIAgentUnavailableException` hatası fırlatır.

Bu durumda API katmanı kullanıcıya `AI_AGENT_UNAVAILABLE` hata kodunu döner. Arayüzde chat ekranı kısıtlanırken, fiyat tabloları, teknik indikatörler, portföy değerlemeleri, VaR risk hesaplamaları ve backtest ekranları tamamen çalışır durumda kalır.

## 3. Yanıt Şablonu (Response Format)

Ajan, kullanıcı sorgularına cevap verirken finansal bilgilerin yapısını korumak için aşağıdaki şablonu kullanır:

```text
ÖZET (SUMMARY)
PİYASA BAĞLAMI (MARKET CONTEXT)
VERİ (DATA)
ANALİZ (ANALYSIS)
SİNYALLER (SIGNALS)
RİSKLER (RISKS)
ALTERNATİFLER (ALTERNATIVES)
İŞLEM ÖNERİSİ (TRADE PROPOSAL)
GÜVEN DEĞERİ (CONFIDENCE BREAKDOWN)
VERİ KALİTESİ (DATA QUALITY)
VARSAYIMLAR (ASSUMPTIONS)
```
