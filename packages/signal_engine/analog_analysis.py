import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

class HistoricalAnalogAnalyzer:
    """Mevcut piyasa koşullarına benzer tarihsel dönemleri bulan ve analiz eden motor."""
    
    def __init__(self, k_neighbors: int = 10, distance_metric: str = "cosine"):
        self.k_neighbors = k_neighbors
        self.distance_metric = distance_metric

    def _get_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """Benzerlik analizi için öznitelik matrisini hazırlar ve ölçeklendirir."""
        feature_cols = ['rsi', 'bb_width', 'volatility', 'returns', 'macd']
        
        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        
        matrix = df[feature_cols].values
        
        # Min-Max Normalizasyonu
        min_vals = np.nanmin(matrix, axis=0)
        max_vals = np.nanmax(matrix, axis=0)
        denom = max_vals - min_vals
        denom[denom == 0] = 1.0
        
        scaled_matrix = (matrix - min_vals) / denom
        return np.nan_to_num(scaled_matrix), feature_cols

    def find_analogs(self, df_indicators: pd.DataFrame, target_horizons: List[int] = [5, 10, 20]) -> Dict[str, Any]:
        """En son piyasa barına benzer geçmiş dönemleri bulur ve getirilerini analiz eder."""
        df = df_indicators.copy().sort_values('timestamp').reset_index(drop=True)
        n_rows = len(df)
        
        if n_rows < 100:
            return {
                "basari": False,
                "hata": "Analiz için yetersiz veri geçmişi (en az 100 bar gerekir).",
                "ornek_sayisi": 0
            }
            
        feature_matrix, _ = self._get_feature_matrix(df)
        
        # Son bar (current state)
        current_vector = feature_matrix[-1]
        
        # Geçmiş barlar (sızıntı engelleme amaçlı son 20 günü hariç tut)
        exclusion_horizon = max(target_horizons)
        compare_matrix = feature_matrix[:-exclusion_horizon]
        compare_dates = df['timestamp'].iloc[:-exclusion_horizon].values
        compare_indices = df.index[:-exclusion_horizon]
        
        # Mesafeleri hesapla
        distances = []
        if self.distance_metric == "cosine":
            curr_norm = np.linalg.norm(current_vector)
            if curr_norm == 0:
                curr_norm = 1.0
            for vec in compare_matrix:
                vec_norm = np.linalg.norm(vec)
                if vec_norm == 0:
                    vec_norm = 1.0
                dot_product = np.dot(current_vector, vec)
                cosine_sim = dot_product / (curr_norm * vec_norm)
                distances.append(1.0 - cosine_sim)
        else:
            for vec in compare_matrix:
                distances.append(np.linalg.norm(current_vector - vec))
                
        distances = np.array(distances)
        
        # En yakın K komşuyu bul
        nearest_indices = np.argsort(distances)[:self.k_neighbors]
        
        analog_results = []
        subsequent_returns = {h: [] for h in target_horizons}
        subsequent_mams = {h: [] for h in target_horizons} # Maximum Adverse Movement
        
        for idx in nearest_indices:
            orig_idx = compare_indices[idx]
            match_date = pd.to_datetime(compare_dates[idx])
            distance = distances[idx]
            similarity = 1.0 - distance if self.distance_metric == "cosine" else 1.0 / (1.0 + distance)
            
            # Sonraki getirileri ve maksimum olumsuz hareketi (drawdown) hesapla
            horizon_returns = {}
            horizon_mams = {}
            
            for h in target_horizons:
                if orig_idx + h < n_rows:
                    price_at_match = df.loc[orig_idx, 'close']
                    price_future = df.loc[orig_idx + h, 'close']
                    ret = (price_future - price_at_match) / price_at_match
                    horizon_returns[h] = ret
                    subsequent_returns[h].append(ret)
                    
                    # Maximum Adverse Movement (h horizon penceresindeki en derin düşüş)
                    sub_prices = df.loc[orig_idx + 1 : orig_idx + h, 'close'].values
                    if len(sub_prices) > 0:
                        min_sub_price = np.min(sub_prices)
                        mam = (min_sub_price - price_at_match) / price_at_match
                        mam = min(0.0, mam) # Sadece negatif düşüşleri say
                    else:
                        mam = 0.0
                    horizon_mams[h] = mam
                    subsequent_mams[h].append(mam)
                else:
                    horizon_returns[h] = None
                    horizon_mams[h] = None
                    
            analog_results.append({
                "tarih": match_date.strftime("%Y-%m-%d"),
                "benzerlik": round(float(similarity), 4),
                "mesafe": round(float(distance), 4),
                "getiriler": horizon_returns,
                "max_adverse_movement": horizon_mams
            })
            
        # İstatistiksel özet çıkar
        stats = {}
        for h in target_horizons:
            rets = np.array([r for r in subsequent_returns[h] if r is not None])
            mams = np.array([m for m in subsequent_mams[h] if m is not None])
            
            if len(rets) > 0:
                win_rate = float((rets > 0).mean())
                mean_mam = float(np.mean(mams)) if len(mams) > 0 else 0.0
                max_mam = float(np.min(mams)) if len(mams) > 0 else 0.0
                
                stats[f"horizon_{h}"] = {
                    "ortalama_getiri": round(float(np.mean(rets)), 4),
                    "medyan_getiri": round(float(np.median(rets)), 4),
                    "std_getiri": round(float(np.std(rets)), 4),
                    "min_getiri": round(float(np.min(rets)), 4),
                    "max_getiri": round(float(np.max(rets)), 4),
                    "kazanma_orani": round(win_rate, 4),
                    "ornek_sayisi": len(rets),
                    "ortalama_max_dusus": round(mean_mam, 4),
                    "en_derin_max_dusus": round(max_mam, 4)
                }
            else:
                stats[f"horizon_{h}"] = {
                    "ortalama_getiri": 0.0,
                    "medyan_getiri": 0.0,
                    "std_getiri": 0.0,
                    "min_getiri": 0.0,
                    "max_getiri": 0.0,
                    "kazanma_orani": 0.0,
                    "ornek_sayisi": 0,
                    "ortalama_max_dusus": 0.0,
                    "en_derin_max_dusus": 0.0
                }
                
        mean_similarity = float(np.mean([a['benzerlik'] for a in analog_results]))
        
        return {
            "basari": True,
            "benzerlik_skoru": round(mean_similarity, 4),
            "analoglar": analog_results,
            "istatistikler": stats,
            "ornek_sayisi": len(analog_results)
        }
