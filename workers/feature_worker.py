import os
import joblib
import logging
import pandas as pd
from packages.common.database import SessionLocal, check_db_connection
from packages.common.models import Asset, PriceBar, Fundamental, MacroObservation, NewsArticle
from packages.feature_engine.features import FeatureGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.worker.feature")

def run_feature_worker(version: str = "v1.0"):
    logger.info(f"Feature Worker ({version}) başlatılıyor...")
    
    try:
        check_db_connection()
    except Exception:
        logger.error("Veritabanı bağlantısı yok. Worker durduruluyor.")
        return

    db = SessionLocal()
    fg = FeatureGenerator(version=version)
    
    try:
        assets = db.query(Asset).filter(Asset.is_active == True).all()
        
        # Makro ve haber verilerini genel olarak çek (her hisseye as-of bağlanacak)
        macro_obs = db.query(MacroObservation).all()
        df_macro = pd.DataFrame([{
            "timestamp": m.timestamp,
            "indicator_name": m.indicator_name,
            "value": m.value
        } for m in macro_obs]) if macro_obs else None
        
        news_art = db.query(NewsArticle).all()
        df_news = pd.DataFrame([{
            "published_at": n.published_at,
            "sentiment": n.sentiment
        } for n in news_art]) if news_art else None

        for asset in assets:
            logger.info(f"{asset.symbol} için öznitelikler güncelleniyor...")
            
            prices = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.timestamp.asc()).all()
            if len(prices) < 20:
                logger.warning(f"{asset.symbol} için yetersiz fiyat geçmişi var. Atlanıyor.")
                continue
                
            df_prices = pd.DataFrame([{
                "timestamp": p.timestamp,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
                "returns": p.close / p.open - 1.0, # Basit getiri
                "rsi": 50.0, # Default, indicators sonradan hesaplayacak
                "bb_width": 0.10,
                "volatility": 0.20,
                "macd": 0.0,
                "beta": 1.0,
                "correlation": 1.0
            } for p in prices])
            
            # Teknik hesaplamaları yap
            from packages.quant_engine.indicators import calculate_all_indicators
            df_prices = calculate_all_indicators(df_prices)
            
            # Temel verileri çek
            fund = db.query(Fundamental).filter(Fundamental.symbol == asset.symbol).order_by(Fundamental.snapshot_date.asc()).all()
            df_fund = pd.DataFrame([{
                "snapshot_date": f.snapshot_date,
                "metrics": f.metrics
            } for f in fund]) if fund else None
            
            # Öznitelik matrisi üret
            df_features = fg.generate_features(df_prices, df_fund, df_macro, df_news)
            
            # Sonuçları diske kaydet
            out_dir = f"models/datasets/{asset.symbol}"
            os.makedirs(out_dir, exist_ok=True)
            filepath = os.path.join(out_dir, f"features_{version}.joblib")
            
            joblib.dump(df_features, filepath)
            logger.info(f"{asset.symbol} öznitelik matrisi kaydedildi: {filepath}")
            
    except Exception as e:
        logger.error(f"Feature Worker çalışırken hata: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_feature_worker()
