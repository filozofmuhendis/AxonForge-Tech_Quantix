import pandas as pd
import numpy as np
from typing import Dict, Any

class MarketRegimeDetector:
    """Farklı piyasa koşullarını (BULL, BEAR, SIDEWAYS, CRISIS vb.) tespit eden kural tabanlı ve istatistiksel motor."""
    
    def __init__(self, lookback: int = 252):
        self.lookback = lookback

    def detect_regimes(self, df_indicators: pd.DataFrame) -> pd.DataFrame:
        """Tüm zaman serisi için kural tabanlı piyasa rejimlerini hesaplar."""
        df = df_indicators.copy().sort_values('timestamp')
        
        if len(df) < 50:
            df['market_regime'] = "TRANSITION"
            return df
            
        vol = df['volatility']
        rolling_90_vol = vol.rolling(window=self.lookback, min_periods=50).quantile(0.90)
        rolling_98_vol = vol.rolling(window=self.lookback, min_periods=50).quantile(0.98)
        rolling_25_vol = vol.rolling(window=self.lookback, min_periods=50).quantile(0.25)
        
        close = df['close']
        sma_50 = df['sma_50']
        sma_200 = df['sma_200']
        
        regimes = []
        for idx, row in df.iterrows():
            curr_vol = row['volatility']
            curr_close = row['close']
            curr_sma50 = row['sma_50']
            curr_sma200 = row['sma_200']
            
            limit_98 = rolling_98_vol.loc[idx] if not pd.isna(rolling_98_vol.loc[idx]) else 0.50
            limit_90 = rolling_90_vol.loc[idx] if not pd.isna(rolling_90_vol.loc[idx]) else 0.35
            limit_25 = rolling_25_vol.loc[idx] if not pd.isna(rolling_25_vol.loc[idx]) else 0.10
            
            # 1. Kriz & Oynaklık Limiti Kontrolü
            if curr_vol > limit_98:
                regimes.append("CRISIS")
            elif curr_vol > limit_90:
                regimes.append("HIGH_VOLATILITY")
            elif curr_vol < limit_25:
                regimes.append("LOW_VOLATILITY")
            else:
                # 2. Trend ve Konsolidasyon Kontrolü
                sma_diff_pct = abs(curr_sma50 - curr_sma200) / curr_sma200 if curr_sma200 > 0 else 0
                
                if sma_diff_pct < 0.02:
                    regimes.append("SIDEWAYS")
                elif curr_close > curr_sma50 > curr_sma200:
                    regimes.append("BULL")
                elif curr_close < curr_sma50 < curr_sma200:
                    regimes.append("BEAR")
                else:
                    regimes.append("TRANSITION")
                    
        df['market_regime'] = regimes
        return df

    def detect_regimes_statistical(self, df_indicators: pd.DataFrame, n_regimes: int = 3) -> pd.DataFrame:
        """K-Means kümeleme kullanarak istatistiksel (statistical clustering) piyasa rejim segmentasyonu yapar."""
        from sklearn.cluster import KMeans
        df = df_indicators.copy().sort_values('timestamp')
        
        if len(df) < 50:
            df['statistical_regime'] = "TRANSITION"
            return df
            
        # Volatilite ve 20 günlük getiri üzerinden kümeleme
        df['return_20d'] = df['close'].pct_change(20).fillna(0.0)
        X = df[['volatility', 'return_20d']].values
        
        kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X)
        
        # Kümeleri getiri ve oynaklık karakterlerine göre isimlendir
        # Önce küme merkezlerini incele
        centers = kmeans.cluster_centers_
        cluster_names = {}
        
        for cluster_id in range(n_regimes):
            vol_center, ret_center = centers[cluster_id]
            if vol_center > np.mean(centers[:, 0]) and ret_center < 0:
                cluster_names[cluster_id] = "STAT_CRISIS"
            elif ret_center > 0 and vol_center < np.mean(centers[:, 0]):
                cluster_names[cluster_id] = "STAT_BULL"
            else:
                cluster_names[cluster_id] = "STAT_SIDEWAYS"
                
        df['statistical_regime'] = [cluster_names.get(c, "STAT_SIDEWAYS") for c in clusters]
        return df

    def detect_current_regime(self, df_indicators: pd.DataFrame) -> Dict[str, Any]:
        """En son barda geçerli olan piyasa rejimini analiz eder."""
        df_regimes = self.detect_regimes(df_indicators)
        if df_regimes.empty:
            return {"regime": "TRANSITION", "stability_score": 0.50, "volatility_percentile": 0.50}
            
        latest = df_regimes.iloc[-1]
        
        vol = df_regimes['volatility']
        current_vol = latest['volatility']
        vol_percentile = float((vol < current_vol).mean())
        
        # Kararlılık skoru: Son 10 gündeki hakim rejim oranı
        recent_regimes = df_regimes['market_regime'].tail(10)
        stability_score = float((recent_regimes == latest['market_regime']).mean())
        
        # İstatistiksel rejim saptama
        try:
            df_stat = self.detect_regimes_statistical(df_indicators)
            stat_regime = df_stat.iloc[-1]['statistical_regime']
        except Exception:
            stat_regime = "STAT_SIDEWAYS"
        
        return {
            "regime": latest['market_regime'],
            "statistical_regime": stat_regime,
            "stability_score": round(stability_score, 2),
            "volatility_percentile": round(vol_percentile, 2),
            "timestamp": latest['timestamp']
        }
