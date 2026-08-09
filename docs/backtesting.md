# AxonForge Geriye Dönük Test Motoru (Backtesting)

Backtest Engine, yatırım stratejilerinin geçmiş fiyat barları üzerinde simüle edilmesini sağlayan, sızıntı korumalı nicel bir analiz bileşenidir.

## 1. Veri Sızıntısı ve Look-Ahead Bias Koruması

Stratejinin geçmişe dönük test edilirken gelecekteki barları görmesini önlemek için test motoru strictly **Event-Driven Loop** (Olay Güdümlü Adım Döngüsü) modelini kullanır:

```python
for t in range(warmup_period, n_bars):
    # Stratejiye sadece t anına kadar olan veri dilimi verilir!
    historical_slice = df.iloc[:t+1]
    signal = strategy(historical_slice, t)
```

Strateji fonksiyonunun `df.iloc[t+1:]` verisine erişmesi veya geleceğe ait teknik indikatörlerin normalizasyonunu (normalization leakage) kullanması engellenmiştir.

## 2. Gerçekçi İşlem Parametreleri

*   **Komisyon (Commission):** Her alım-satım işleminde toplam tutar üzerinden binde 1 (veya ayarlandığı oranda) işlem ücreti kesilir.
*   **Slippage (Fiyat Kayması):** Piyasa derinliği ve işlem anındaki gecikmeler nedeniyle, alış emri tetiklendiğinde günün en düşük/açılış fiyatına %0.05 eklenir; satarken ise %0.05 düşülür.
*   **Likidite Kısıtlaması (Volume Cap):** Bir barda alınabilecek maksimum hisse miktarı, o barın hacminin %10'u (`liquidity_cap_pct = 0.10`) ile sınırlıdır. Bu sınırı aşan büyük emirler kısmi gerçekleşir (partial fill).

## 3. Walk-Forward Doğrulama (Walk-Forward Validation)

Model aşırı öğrenmesini (overfitting) engellemek amacıyla stratejiler Walk-Forward yöntemiyle test edilir:
1.  Model $T_{0}$ ile $T_{1}$ arasında eğitilir (ör. 252 bar).
2.  Eğitilen model $T_{1}$ ile $T_{2}$ arasında sızıntısız test edilir (ör. 63 bar).
3.  Eğitim penceresi $T_{2}$ tarihine kaydırılır ve süreç tekrarlanır.
4.  Test pencerelerinden elde edilen P&L ve Sharpe performans metrikleri birleştirilerek nihai rapor oluşturulur.
