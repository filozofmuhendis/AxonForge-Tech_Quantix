import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

class FeatureGenerator:
    """Makine öğrenimi için öznitelik (feature) üreten, yöneten ve sızıntı koruması sağlayan motor."""
    
    def __init__(self, version: str = "v1.0"):
        self.version = version

    def generate_features(
        self,
        df_prices: pd.DataFrame,
        df_fundamentals: Optional[pd.DataFrame] = None,
        df_macro: Optional[pd.DataFrame] = None,
        df_news: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Farklı veri kaynaklarını tarihsel bazda birleştirerek sızıntı (leakage) korumalı 
        öznitelik seti üretir. Tüm birleştirmeler 'timestamp' bazında geriye dönük (as-of) yapılır.
        """
        df = df_prices.copy().sort_values('timestamp')
        
        feature_cols = []
        feature_metadata = {}
        now_str = datetime.now(timezone.utc).isoformat()
        
        # 1. Teknik Öznitelikler
        tech_cols = [
            'rsi', 'bb_width', 'volatility', 'returns', 'macd', 
            'beta', 'correlation', 'roc', 'stoch_k', 'stoch_d', 
            'obv', 'volume_ratio'
        ]
        
        # Meta tanım parametreleri
        tech_meta = {
            "rsi": {"lookback": "14D", "source": "YahooFinance"},
            "bb_width": {"lookback": "20D", "source": "YahooFinance"},
            "volatility": {"lookback": "20D", "source": "YahooFinance"},
            "returns": {"lookback": "1D", "source": "YahooFinance"},
            "macd": {"lookback": "12,26,9D", "source": "YahooFinance"},
            "beta": {"lookback": "60D", "source": "YahooFinance"},
            "correlation": {"lookback": "60D", "source": "YahooFinance"},
            "roc": {"lookback": "12D", "source": "YahooFinance"},
            "stoch_k": {"lookback": "14D", "source": "YahooFinance"},
            "stoch_d": {"lookback": "3D", "source": "YahooFinance"},
            "obv": {"lookback": "0D", "source": "YahooFinance"},
            "volume_ratio": {"lookback": "20D", "source": "YahooFinance"}
        }

        for col in tech_cols:
            if col in df.columns:
                feature_cols.append(col)
                meta = tech_meta.get(col, {"lookback": "unknown", "source": "YahooFinance"})
                feature_metadata[col] = {
                    "feature_name": col,
                    "version": self.version,
                    "timestamp": now_str,
                    "source": meta["source"],
                    "lookback": meta["lookback"],
                    "normalization": "none"
                }
                
        # 2. Temel Analiz Özniteliklerini Birleştir (Fundamentals)
        if df_fundamentals is not None and not df_fundamentals.empty:
            df_fundamentals = df_fundamentals.copy().sort_values('snapshot_date')
            df_fundamentals['timestamp'] = pd.to_datetime(df_fundamentals['snapshot_date'])
            
            df = pd.merge_asof(
                df,
                df_fundamentals[['timestamp', 'metrics']],
                on='timestamp',
                direction='backward'
            )
            
            if 'metrics' in df.columns:
                metrics_list = df['metrics'].tolist()
                metrics_df = pd.DataFrame([m if isinstance(m, dict) else {} for m in metrics_list], index=df.index)
                
                num_metrics = metrics_df.select_dtypes(include=[np.number])
                for col in num_metrics.columns:
                    col_name = f"fund_{col.lower().replace(' ', '_').replace('/', '_')}"
                    df[col_name] = num_metrics[col]
                    feature_cols.append(col_name)
                    
                    feature_metadata[col_name] = {
                        "feature_name": col_name,
                        "version": self.version,
                        "timestamp": now_str,
                        "source": "YahooFinance/SEC",
                        "lookback": "0D (As-Of Latest)",
                        "normalization": "none"
                    }
                df = df.drop(columns=['metrics'])

        # 3. Makroekonomik Verileri Birleştir (Macro)
        if df_macro is not None and not df_macro.empty:
            df_macro = df_macro.copy().sort_values('timestamp')
            indicators = df_macro['indicator_name'].unique()
            
            for ind in indicators:
                col_name = f'macro_{ind.lower()}'
                df_ind = df_macro[df_macro['indicator_name'] == ind][['timestamp', 'value']].rename(columns={'value': col_name})
                df = pd.merge_asof(
                    df,
                    df_ind,
                    on='timestamp',
                    direction='backward'
                )
                feature_cols.append(col_name)
                
                feature_metadata[col_name] = {
                    "feature_name": col_name,
                    "version": self.version,
                    "timestamp": now_str,
                    "source": "TCMB/FRED",
                    "lookback": "0D (As-Of Latest)",
                    "normalization": "none"
                }

        # 4. Haber Duygu Analizi Özniteliklerini Birleştir (News Sentiment)
        if df_news is not None and not df_news.empty:
            df_news = df_news.copy().sort_values('published_at')
            df_news['timestamp'] = pd.to_datetime(df_news['published_at'])
            
            sentiment_series = []
            for idx, row in df.iterrows():
                bar_time = row['timestamp']
                mask = (df_news['timestamp'] < bar_time) & (df_news['timestamp'] >= bar_time - pd.Timedelta(days=3))
                recent_news = df_news[mask]
                
                mean_sent = recent_news['sentiment'].mean() if not recent_news.empty else 0.0
                sentiment_series.append(mean_sent)
                
            col_name = 'news_sentiment_3d'
            df[col_name] = sentiment_series
            feature_cols.append(col_name)
            
            feature_metadata[col_name] = {
                "feature_name": col_name,
                "version": self.version,
                "timestamp": now_str,
                "source": "NewsNLP",
                "lookback": "3D Window",
                "normalization": "none"
            }
            
        # Boş değerleri temizle / ffill
        df[feature_cols] = df[feature_cols].fillna(method='ffill').fillna(0.0)
        
        # Meta veriyi DataFrame nesnesinde sakla
        df.attrs['feature_version'] = self.version
        df.attrs['feature_cols'] = feature_cols
        df.attrs['feature_metadata'] = feature_metadata
        
        return df

    def create_labels(self, df: pd.DataFrame, horizon: int = 5, threshold: float = 0.02) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Model eğitimi için veri sızıntısız etiketler (target) üretir.
        Yön tahmini için: Getiri > threshold ise 1, aksi halde 0.
        """
        # Gelecekteki getiri (Look-ahead bias içermeyen target üretimi)
        future_price = df['close'].shift(-horizon)
        returns = (future_price - df['close']) / df['close']
        
        # Target sınıflandırma etiketi
        labels = (returns > threshold).astype(int)
        
        # Son 'horizon' adet satırın geleceğe ait verisi olmadığı için silinmelidir
        valid_idx = df.index[:-horizon]
        
        return df.loc[valid_idx], labels.loc[valid_idx]

    def split_train_test_without_leakage(
        self,
        df_features: pd.DataFrame,
        labels: pd.Series,
        train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Zaman serisi yapısına uygun olarak veriyi sızıntısız böler.
        Rastgele bölme (random split) finansal verilerde sızıntıya yol açar.
        """
        split_idx = int(len(df_features) * train_ratio)
        
        X_train = df_features.iloc[:split_idx]
        X_test = df_features.iloc[split_idx:]
        
        y_train = labels.iloc[:split_idx]
        y_test = labels.iloc[split_idx:]
        
        return X_train, X_test, y_train, y_test
