# AxonForge Nicel Analiz Motoru (Quant Engine)

Quant Engine, AxonForge terminalinin matematiksel ve istatistiksel çekirdeğidir. Tüm veri hesaplamaları Pandas ve NumPy kullanılarak vektörize bir biçimde gerçekleştirilir.

## 1. Hesaplanan Temel Teknik İndikatörler

*   **RSI (Relative Strength Index - Göreceli Güç Endeksi):**
     Wilders düzeltmeli hareketli ortalama yöntemi kullanılarak hesaplanır:
    $$RSI = 100 - \frac{100}{1 + RS}$$
    Burada $RS = \frac{\text{Ortalama Kazanç}}{\text{Ortalama Kayıp}}$ değeridir.

*   **Bollinger Bantları:**
    20 günlük hareketli ortalama (SMA) üzerine 2 standart sapma eklenip çıkarılarak hesaplanır.
    $$\text{Bollinger Genişliği} = \frac{\text{Üst Bant} - \text{Alt Bant}}{\text{Orta Bant}}$$

*   **ATR (Average True Range):**
    Piyasa oynaklığını ölçmek amacıyla aşağıdaki True Range değerinin 14 günlük rolling ortalaması alınır:
    $$TR = \max(High - Low, |High - Close_{prev}|, |Low - Close_{prev}|)$$

*   **Beta ve Korelasyon:**
    Varlık getirisi ($R_a$) ile benchmark endeks getirisi ($R_b$) arasındaki 60 günlük hareketli covaryans ve korelasyon katsayılarıdır:
    $$\beta = \frac{Cov(R_a, R_b)}{Var(R_b)}$$

## 2. Tarihsel Benzer (Analog) Dönem Analizi

Ajanın ve sinyal motorunun piyasa benzerliklerini ölçmek için kullandığı Tarihsel Benzer Analiz motoru (`packages/signal_engine/analog_analysis.py`), teknik özniteliklerden oluşan bir durum vektörü hazırlar:

$$\vec{x}_t = [RSI_t, BBWidth_t, Volatility_t, Return5D_t, MACD_t]$$

Her bir geçmiş gün $i$ için, mevcut gün $t$ ile arasındaki kosinüs benzerliği (Cosine Similarity) hesaplanır:

$$\text{Similarity}(\vec{x}_t, \vec{x}_i) = \frac{\vec{x}_t \cdot \vec{x}_i}{\|\vec{x}_t\| \|\vec{x}_i\|}$$

En yüksek benzerliğe sahip (en küçük kosinüs mesafesi olan) $K=10$ komşu dönem seçilerek, bu dönemlerden sonraki 5, 10 ve 20 günlük getirilerin dağılımı, kazanma oranı (win rate) ve standart sapması (belirsizlik) istatistiksel olarak çıkarılır.
