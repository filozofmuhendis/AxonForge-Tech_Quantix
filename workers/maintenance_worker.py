import logging
from datetime import datetime, timezone, timedelta
from packages.common.database import SessionLocal, check_db_connection
from packages.common.models import ModelRegistry, ModelPrediction, PriceBar, DecisionJournal, TradeProposal
from packages.common.journal import JournalManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.worker.maintenance")

def run_maintenance_worker():
    logger.info("Maintenance Worker başlatılıyor...")
    
    try:
        check_db_connection()
    except Exception:
        logger.error("Veritabanı bağlantısı yok. Worker durduruluyor.")
        return

    db = SessionLocal()
    jm = JournalManager()
    
    try:
        # 1. Model Drift ve Kalibrasyon Güncelleme (Drift Tracking)
        # 5 gün önceki tahminleri kontrol et
        five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
        unresolved_predictions = db.query(ModelPrediction).filter(
            ModelPrediction.timestamp <= five_days_ago,
            ModelPrediction.calibration_score == None
        ).all()
        
        logger.info(f"Kalibre edilmeyi bekleyen eski tahmin sayısı: {len(unresolved_predictions)}")
        
        for pred in unresolved_predictions:
            # Gerçekleşen getiri farkını bul
            # Varlığa ait tahminden sonraki close değerini bul
            from packages.common.models import Asset
            asset = db.query(Asset).filter(Asset.symbol == pred.symbol).first()
            if not asset:
                continue
                
            # Tahmin anındaki ve sonraki fiyat barını bul
            price_then = db.query(PriceBar).filter(
                PriceBar.asset_id == asset.id,
                PriceBar.timestamp <= pred.timestamp
            ).order_by(PriceBar.timestamp.desc()).first()
            
            price_five_days_later = db.query(PriceBar).filter(
                PriceBar.asset_id == asset.id,
                PriceBar.timestamp >= pred.timestamp + timedelta(days=5)
            ).order_by(PriceBar.timestamp.asc()).first()
            
            if price_then and price_five_days_later:
                actual_return = (price_five_days_later.close - price_then.close) / price_then.close
                # Eşik: Yön tahmini return > 2% ise 1, değilse 0
                actual_class = 1.0 if actual_return > 0.02 else 0.0
                
                # Brier skoru: (tahmin_olasılığı - gerçek_sınıf)^2
                brier = (pred.probability - actual_class) ** 2
                pred.calibration_score = brier
                
                # Modeli güncelle
                db_model = db.query(ModelRegistry).filter(ModelRegistry.model_id == pred.model_id).first()
                if db_model:
                    # Modelin ortalama Brier skorunu yeniden hesapla
                    all_calibs = db.query(ModelPrediction.calibration_score).filter(
                        ModelPrediction.model_id == pred.model_id,
                        ModelPrediction.calibration_score != None
                    ).all()
                    
                    scores = [float(c[0]) for c in all_calibs if c[0] is not None]
                    if scores:
                        mean_brier = sum(scores) / len(scores)
                        metrics = db_model.metrics.copy()
                        metrics["brier_score"] = round(mean_brier, 4)
                        db_model.metrics = metrics
                        
                        # Bozulma sınırı kontrolü
                        if mean_brier > 0.28:
                            db_model.status = "DEGRADED"
                            logger.warning(f"MODEL_DEGRADATION: {db_model.model_id} kalitesi bozuldu. Durum: DEGRADED.")
                            
        # 2. Karar Günlüğü Sonuç Değerlendirme (Post-Trade Evaluation)
        # Kapatılmış ancak retrospektif AI değerlendirmesi yapılmamış günlük girdilerini bul
        open_journal_entries = db.query(DecisionJournal).filter(
            DecisionJournal.actual_outcome_pnl != None,
            DecisionJournal.post_trade_evaluation == None
        ).all()
        
        for entry in open_journal_entries:
            pnl = entry.actual_outcome_pnl
            
            # Değerlendirme şablonunu oluştur
            if pnl > 0:
                evaluation = (
                    f"Başarılı İşlem. Yatırım tezi onaylandı. Piyasa rejimindeki "
                    f"{entry.regime_at_entry} koşulları hedefe ulaşmayı kolaylaştırdı. "
                    f"Stop loss veya marj ihlali yaşanmadan işlem kâr ile kapatıldı."
                )
            else:
                evaluation = (
                    f"Zararla Kapanan İşlem. Yatırım tezi başarısız oldu. Piyasa rejimindeki "
                    f"beklenmedik kırılımlar veya işlem anındaki aşırı oynaklık (volatilite) "
                    f"hedefin geçilmesini engellemiş olabilir. Gerekçe gözden geçirilmelidir."
                )
                
            entry.post_trade_evaluation = evaluation
            logger.info(f"Karar günlüğü işlemi retrospektif analizi güncellendi (ID: {entry.id})")
            
        db.commit()
        logger.info("Bakım görevleri başarıyla tamamlandı.")
        
    except Exception as e:
        logger.error(f"Maintenance Worker çalışırken hata: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_maintenance_worker()
