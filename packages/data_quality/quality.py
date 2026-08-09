import pandas as pd
import numpy as np
from typing import Dict, Any, List, Union

def calculate_data_quality_score(df_or_bars: Union[pd.DataFrame, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Verilen bar verilerinin kalite kontrollerini yapar ve 0-100 arasında bir skor üretir.
    Hataların ve uyarıların detaylı listesini döndürür.
    """
    # Liste halindeyse DataFrame'e dönüştür
    if isinstance(df_or_bars, list):
        if not df_or_bars:
            return {"score": 0.0, "anomaliler": ["Veri seti boş."], "valid": False}
        df = pd.DataFrame(df_or_bars)
    else:
        df = df_or_bars.copy()
        
    if df.empty:
        return {"score": 0.0, "anomaliler": ["Veri seti boş."], "valid": False}
        
    score = 100.0
    anomaliler = []
    
    # 1. Kolon Kontrolü
    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        return {
            "score": 0.0,
            "anomaliler": [f"Eksik zorunlu kolonlar: {list(missing_cols)}"],
            "valid": False
        }

    # 2. Tekrar Eden Zaman Damgası Kontrolü (Duplicates)
    if 'timestamp' in df.columns:
        duplicate_count = df.duplicated(subset=['timestamp']).sum()
        if duplicate_count > 0:
            score -= min(20.0, float(duplicate_count * 2.0))
            anomaliler.append(f"Tekrarlanan zaman damgası tespit edildi: {duplicate_count} adet.")

    # 3. İmkansız OHLC Değerleri Kontrolü
    # High < Low
    impossible_hl = df['high'] < df['low']
    if impossible_hl.any():
        count = impossible_hl.sum()
        score -= min(30.0, float(count * 5.0))
        anomaliler.append(f"En Yüksek Fiyat (High), En Düşük Fiyattan (Low) küçük: {count} satır.")
        
    # Open veya Close sınırların dışında (High'dan büyük veya Low'dan küçük)
    out_of_bounds = (df['open'] > df['high']) | (df['open'] < df['low']) | \
                    (df['close'] > df['high']) | (df['close'] < df['low'])
    if out_of_bounds.any():
        count = out_of_bounds.sum()
        score -= min(25.0, float(count * 4.0))
        anomaliler.append(f"Açılış veya kapanış fiyatı, High-Low sınırlarının dışında: {count} satır.")

    # Negatif Fiyat Kontrolü
    negative_prices = (df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)
    if negative_prices.any():
        count = negative_prices.sum()
        score -= min(40.0, float(count * 10.0))
        anomaliler.append(f"Sıfır veya negatif fiyat tespit edildi: {count} satır.")

    # Negatif Hacim Kontrolü
    negative_volume = df['volume'] < 0
    if negative_volume.any():
        count = negative_volume.sum()
        score -= min(20.0, float(count * 5.0))
        anomaliler.append(f"Negatif işlem hacmi tespit edildi: {count} satır.")

    # 4. Anormal Fiyat Değişim Sıçramaları (Abnormal Jumps)
    # Günlük getirilerde %50'den büyük hareketler (kriptolar hariç normal hisseler için şüpheli)
    if len(df) > 1:
        pct_change = df['close'].pct_change().abs()
        abnormal_jumps = pct_change > 0.50
        if abnormal_jumps.any():
            count = abnormal_jumps.sum()
            score -= min(25.0, float(count * 5.0))
            anomaliler.append(f"Anormal fiyat sıçraması (tek bir barda > %50 değişim): {count} satır.")

    # 5. Bayat Veri Kontrolü (Stale Data / Stagnant prices)
    # Close fiyatı ardışık 10 bar boyunca birebir aynı mı kalmış (işlem hacmi sıfır olmayan aktif piyasalarda şüpheli)
    if len(df) >= 10:
        stale_series = df['close'].rolling(window=10).std() == 0
        if stale_series.any():
            count = stale_series.sum()
            score -= min(15.0, float(count * 1.5))
            anomaliler.append(f"Bayat/Durgun fiyat hareketi (10 bar boyunca değişim yok): {count} durum.")

    # Skor sınırlandırması
    score = max(0.0, min(100.0, score))
    
    return {
        "score": round(score, 2),
        "anomaliler": anomaliler,
        "valid": score >= 70.0  # 70 altı veri güvenilir kabul edilmez
    }

def validate_and_annotate_bars(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bar listesini tarar, her bara genel veri seti kalite skorunu yazar."""
    quality_result = calculate_data_quality_score(bars)
    annotated = []
    for bar in bars:
        new_bar = bar.copy()
        new_bar["data_quality_score"] = quality_result["score"]
        annotated.append(new_bar)
    return annotated
