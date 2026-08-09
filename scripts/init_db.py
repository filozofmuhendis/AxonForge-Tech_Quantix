import logging
from datetime import datetime, timezone
from packages.common.database import Base, engine, SessionLocal
from packages.common.models import Market, Asset, Portfolio
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("axonforge.init_db")

def init_database():
    logger.info("Veritabanı tabloları oluşturuluyor...")
    try:
        # Tüm SQLAlchemy modellerini veritabanında oluştur (Sadece PostgreSQL)
        Base.metadata.create_all(bind=engine)
        logger.info("Tablolar başarıyla oluşturuldu.")
    except Exception as e:
        logger.critical(f"Tablo oluşturma hatası: {str(e)}")
        logger.critical("UYARI: PostgreSQL sunucunuzun çalışır durumda olduğundan emin olun.")
        return False

    # Seed verileri ekleme
    db = SessionLocal()
    try:
        logger.info("Varsayılan piyasa ve seans verileri yükleniyor...")
        # 1. Piyasalar
        bist_market = db.query(Market).filter(Market.name == "BIST").first()
        if not bist_market:
            bist_market = Market(
                name="BIST",
                timezone="Europe/Istanbul",
                trading_hours={"open": "10:00", "close": "18:00"},
                holidays=[]
            )
            db.add(bist_market)
            
        us_market = db.query(Market).filter(Market.name == "US").first()
        if not us_market:
            us_market = Market(
                name="US",
                timezone="America/New_York",
                trading_hours={"open": "09:30", "close": "16:00"},
                holidays=[]
            )
            db.add(us_market)
            
        db.commit()

        logger.info("Varsayılan varlık (Asset) tanımları yükleniyor...")
        # 2. Varlıklar (BIST ve ABD)
        default_assets = [
            ("THYAO.IS", "Türk Hava Yolları", "EQUITY", "BIST", "Sanayi", "Havacılık", "TR", "TRY"),
            ("TUPRS.IS", "Tüpraş", "EQUITY", "BIST", "Sanayi", "Rafineri", "TR", "TRY"),
            ("EREGL.IS", "Ereğli Demir Çelik", "EQUITY", "BIST", "Sanayi", "Demir Çelik", "TR", "TRY"),
            ("GARAN.IS", "Garanti Bankası", "EQUITY", "BIST", "Finans", "Bankacılık", "TR", "TRY"),
            ("ASELS.IS", "Aselsan", "EQUITY", "BIST", "Teknoloji", "Savunma", "TR", "TRY"),
            ("AAPL", "Apple Inc.", "EQUITY", "NASDAQ", "Teknoloji", "Tüketici Elektroniği", "US", "USD"),
            ("NVDA", "Nvidia Corp.", "EQUITY", "NASDAQ", "Teknoloji", "Yarı İletken", "US", "USD"),
            ("MSFT", "Microsoft Corp.", "EQUITY", "NASDAQ", "Teknoloji", "Yazılım", "US", "USD"),
            ("TSLA", "Tesla Inc.", "EQUITY", "NASDAQ", "Sanayi", "Otomotiv", "US", "USD"),
            ("XAUUSD", "Altın Spot", "COMMODITY", "GLOBAL", "Emtia", "Değerli Metal", "GLOBAL", "USD"),
            ("USDTRY=X", "Dolar / TL", "FX", "GLOBAL", "Döviz", "Döviz Çifti", "GLOBAL", "TRY")
        ]

        for symbol, name, a_class, exchange, sector, industry, country, currency in default_assets:
            existing_asset = db.query(Asset).filter(Asset.symbol == symbol).first()
            if not existing_asset:
                new_asset = Asset(
                    symbol=symbol,
                    name=name,
                    asset_class=a_class,
                    exchange=exchange,
                    sector=sector,
                    industry=industry,
                    country=country,
                    currency=currency,
                    is_active=True
                )
                db.add(new_asset)
                
        db.commit()

        logger.info("Varsayılan portföy (Portfolio) oluşturuluyor...")
        # 3. Portföy
        existing_port = db.query(Portfolio).filter(Portfolio.name == "Varsayılan").first()
        if not existing_port:
            new_port = Portfolio(
                name="Varsayılan",
                currency="TRY",
                cash=1000000.0,
                created_at=datetime.utcnow()
            )
            db.add(new_port)
            
        db.commit()
        logger.info("Seed verileri başarıyla yüklendi.")
        return True
        
    except Exception as e:
        logger.error(f"Seed veri yükleme hatası: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)
