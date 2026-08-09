import logging
from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from packages.common.models import Asset, Fundamental
from packages.market_data.provider import ProviderRouter

logger = logging.getLogger("axonforge.fundamental_engine.fundamentals")

class FundamentalAnalyzer:
    """Şirket finansal tablolarını, rasyolarını analiz eden ve sektörel karşılaştırma (relative valuation) yapan motor."""
    
    def __init__(self):
        self.router = ProviderRouter()

    def fetch_and_save_fundamentals(self, db: Session, symbol: str) -> Optional[Fundamental]:
        """Veri sağlayıcıdan temel analitik verilerini çeker, veritabanına kaydeder."""
        logger.info(f"{symbol} için finansal temel veriler çekiliyor...")
        try:
            # 1. Sağlayıcı üzerinden veriyi al
            snapshot = self.router.fetch_fundamental_snapshot(symbol)
            if not snapshot:
                logger.warning(f"{symbol} için finansal özet bulunamadı.")
                return None
                
            # 2. Varlık sektör/endüstri bilgilerini veritabanındaki Asset kaydıyla eşleştir / güncelle
            asset = db.query(Asset).filter(Asset.symbol == symbol).first()
            if asset:
                if snapshot.get("sector") and snapshot["sector"] != asset.sector:
                    asset.sector = snapshot["sector"]
                if snapshot.get("industry") and snapshot["industry"] != asset.industry:
                    asset.industry = snapshot["industry"]
                if snapshot.get("country") and snapshot["country"] != asset.country:
                    asset.country = snapshot["country"]
                db.commit()

            # 3. Metrikler sözlüğünü düzenle
            metrics = {
                "revenue": float(snapshot.get("Revenue", 0.0)),
                "revenue_growth": float(snapshot.get("Revenue Growth", 0.0)),
                "gross_profit": float(snapshot.get("Gross Profit", 0.0)),
                "operating_income": float(snapshot.get("Operating Income", 0.0)),
                "net_income": float(snapshot.get("Net Income", 0.0)),
                "eps": float(snapshot.get("EPS", 0.0)),
                "free_cash_flow": float(snapshot.get("Free Cash Flow", 0.0)),
                "total_debt": float(snapshot.get("Total Debt", 0.0)),
                "cash": float(snapshot.get("Cash", 0.0)),
                "equity": float(snapshot.get("Equity", 0.0)),
                "roe": float(snapshot.get("ROE", 0.0)),
                "roa": float(snapshot.get("ROA", 0.0)),
                "margins": float(snapshot.get("Margins", 0.0)),
                "pe_ratio": float(snapshot.get("P/E", 0.0)),
                "pb_ratio": float(snapshot.get("P/B", 0.0)),
                "ev_ebitda": float(snapshot.get("EV/EBITDA", 0.0)),
                "ev_sales": float(snapshot.get("EV/Sales", 0.0)),
                "dividend_yield": float(snapshot.get("Dividend Yield", 0.0))
            }

            # 4. Aynı gün için mükerrer kaydı önle
            today = date.today()
            existing = db.query(Fundamental).filter(
                Fundamental.symbol == symbol,
                Fundamental.snapshot_date == today
            ).first()

            if existing:
                existing.metrics = metrics
                db_fund = existing
            else:
                db_fund = Fundamental(
                    symbol=symbol,
                    snapshot_date=today,
                    metrics=metrics,
                    sector_comparison={}
                )
                db.add(db_fund)
            
            db.commit()
            logger.info(f"{symbol} temel verileri veritabanına kaydedildi.")
            return db_fund
            
        except Exception as e:
            logger.error(f"{symbol} temel verileri kaydedilirken hata oluştu: {str(e)}")
            db.rollback()
            return None

    def calculate_sector_relative_valuation(self, db: Session, symbol: str) -> Dict[str, Any]:
        """Şirketin rasyolarını sektöründeki diğer şirketlerin medyan değerleriyle karşılaştırır."""
        logger.info(f"{symbol} için sektörel relative valuation hesaplanıyor...")
        
        # 1. Şirketin en son temel veri kaydını bul
        target_fund = db.query(Fundamental).filter(Fundamental.symbol == symbol).order_by(Fundamental.snapshot_date.desc()).first()
        if not target_fund or not target_fund.metrics:
            logger.warning(f"{symbol} için temel veri kaydı bulunamadığından karşılaştırma yapılamıyor.")
            return {}
            
        # 2. Şirketin ait olduğu sektörü bul
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        if not asset or not asset.sector:
            logger.warning(f"{symbol} için sektör bilgisi eksik.")
            return {}

        # 3. Aynı sektördeki tüm aktif şirketlerin sembollerini ve en son finansallarını al
        sector_assets = db.query(Asset).filter(Asset.sector == asset.sector, Asset.is_active == True).all()
        symbols_in_sector = [a.symbol for a in sector_assets]
        
        # Sektördeki her şirketin en son finansalını getir
        peer_metrics: List[Dict[str, float]] = []
        for s in symbols_in_sector:
            f = db.query(Fundamental).filter(Fundamental.symbol == s).order_by(Fundamental.snapshot_date.desc()).first()
            if f and f.metrics:
                peer_metrics.append(f.metrics)

        if not peer_metrics:
            return {}

        # 4. Sektör medyanlarını hesapla
        comparison_keys = ["pe_ratio", "pb_ratio", "ev_ebitda", "roe", "margins"]
        medians = {}
        for key in comparison_keys:
            # 0'dan büyük ve geçerli değerleri al
            values = [m[key] for m in peer_metrics if key in m and m[key] > 0]
            if values:
                values.sort()
                mid = len(values) // 2
                medians[key] = values[mid] if len(values) % 2 != 0 else (values[mid - 1] + values[mid]) / 2.0
            else:
                medians[key] = 0.0

        # 5. Göreceli iskontoları hesapla
        metrics = target_fund.metrics
        comparison = {}
        for key in comparison_keys:
            stock_val = metrics.get(key, 0.0)
            sector_val = medians.get(key, 0.0)
            
            if sector_val > 0 and stock_val > 0:
                # P/E, P/B ve EV/EBITDA için düşük olması iskonto (olumlu)
                # ROE ve Margins için yüksek olması prim (olumlu)
                pct_diff = ((stock_val - sector_val) / sector_val) * 100.0
                comparison[key] = {
                    "stock_value": round(stock_val, 2),
                    "sector_median": round(sector_val, 2),
                    "pct_difference": round(pct_diff, 2),
                    "is_undervalued": pct_diff < 0 if key in ["pe_ratio", "pb_ratio", "ev_ebitda"] else pct_diff > 0
                }
            else:
                comparison[key] = {
                    "stock_value": round(stock_val, 2),
                    "sector_median": round(sector_val, 2),
                    "pct_difference": 0.0,
                    "is_undervalued": False
                }

        # 6. Sonuçları veritabanına kaydet
        target_fund.sector_comparison = comparison
        db.commit()
        logger.info(f"{symbol} sektörel karşılaştırma verisi güncellendi.")
        return comparison
