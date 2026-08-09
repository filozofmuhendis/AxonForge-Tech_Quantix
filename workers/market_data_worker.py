import time
import logging
from datetime import datetime, timezone, timedelta
from packages.common.database import SessionLocal, check_db_connection
from packages.common.models import Asset, PriceBar
from packages.market_data.provider import YahooProvider
from packages.data_quality.quality import calculate_data_quality_score

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.worker.market_data")

def run_market_data_worker():
    logger.info("Market Data Worker başlatılıyor...")
    
    # Veritabanı bağlantısını doğrula
    try:
        check_db_connection()
    except Exception:
        logger.error("Veritabanı bağlantısı kurulamadı. Worker durduruluyor.")
        return

    db = SessionLocal()
    provider = YahooProvider()
    
    try:
        # Aktif varlıkları (Asset) çek
        assets = db.query(Asset).filter(Asset.is_active == True).all()
        logger.info(f"Takip edilen aktif varlık sayısı: {len(assets)}")
        
        for asset in assets:
            logger.info(f"{asset.symbol} için güncel veri kontrol ediliyor...")
            
            # En son verinin çekilme aralığı
            start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            bars = provider.fetch_daily_bars(asset.symbol, start_date, end_date)
            if not bars:
                logger.warning(f"{asset.symbol} için veri alınamadı.")
                continue
                
            # Veri kalitesini hesapla ve kaydet
            for bar in bars:
                # Veritabanında aynı tarihli kayıt var mı?
                existing = db.query(PriceBar).filter(
                    PriceBar.asset_id == asset.id,
                    PriceBar.timestamp == bar["timestamp"]
                ).first()
                
                # Tekil bar için kalite skoru
                quality_res = calculate_data_quality_score([bar])
                
                if existing:
                    # Güncelle
                    existing.open = bar["open"]
                    existing.high = bar["high"]
                    existing.low = bar["low"]
                    existing.close = bar["close"]
                    existing.volume = bar["volume"]
                    existing.adj_close = bar["adj_close"]
                    existing.data_quality_score = quality_res["score"]
                    existing.fetched_at = datetime.now(timezone.utc)
                else:
                    # Yeni ekle
                    db_bar = PriceBar(
                        asset_id=asset.id,
                        timestamp=bar["timestamp"],
                        open=bar["open"],
                        high=bar["high"],
                        low=bar["low"],
                        close=bar["close"],
                        volume=bar["volume"],
                        adj_close=bar["adj_close"],
                        provider_name=bar["provider_name"],
                        fetched_at=datetime.now(timezone.utc),
                        latency_ms=bar["latency_ms"],
                        freshness_seconds=bar["freshness_seconds"],
                        data_quality_score=quality_res["score"]
                    )
                    db.add(db_bar)
            
            db.commit()
            logger.info(f"{asset.symbol} verileri başarıyla işlendi.")
            time.sleep(1.0)  # Rate limiting önleme amaçlı bekleme
            
    except Exception as e:
        logger.error(f"Market Data Worker çalışırken kritik hata: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_market_data_worker()
