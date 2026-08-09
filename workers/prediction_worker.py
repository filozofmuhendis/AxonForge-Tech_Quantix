import os
import joblib
import logging
from datetime import datetime, timezone
from packages.common.database import SessionLocal, check_db_connection
from packages.common.models import Asset, ModelRegistry, ModelPrediction
from packages.ml_engine.registry import ModelRegistryManager
from packages.ml_engine.ml_models import AxonForgeMLModel
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.worker.prediction")

def run_prediction_worker():
    logger.info("Prediction Worker başlatılıyor...")
    
    try:
        check_db_connection()
    except Exception:
        logger.error("Veritabanı bağlantısı yok. Worker durduruluyor.")
        return

    db = SessionLocal()
    registry = ModelRegistryManager()
    
    try:
        # Aktif üretimdeki (PRODUCTION) modelleri çek
        active_models = db.query(ModelRegistry).filter(ModelRegistry.status == "PRODUCTION").all()
        if not active_models:
            logger.warning("Kayıtlı üretimde (PRODUCTION) model bulunamadı.")
            return
            
        assets = db.query(Asset).filter(Asset.is_active == True).all()
        
        for db_model in active_models:
            logger.info(f"Model yükleniyor: {db_model.model_id} v{db_model.version}...")
            ml_model = registry.load_model(db, db_model.model_id, db_model.version)
            
            if not ml_model:
                logger.error(f"Model yüklenemedi: {db_model.model_id}")
                continue
                
            for asset in assets:
                # Varlığa ait en son öznitelikleri yükle
                feat_path = f"models/datasets/{asset.symbol}/features_{db_model.feature_version}.joblib"
                if not os.path.exists(feat_path):
                    logger.warning(f"{asset.symbol} için öznitelik dosyası bulunamadı: {feat_path}")
                    continue
                    
                df_features = joblib.load(feat_path)
                if df_features.empty:
                    continue
                    
                # Son satırı tahmin et (anlık durum)
                latest_row = df_features.tail(1)
                
                # Tahmin koştur
                preds, probs = ml_model.predict_probability(latest_row)
                pred_val = float(preds[0])
                prob_val = float(probs[0])
                
                # Olasılığı veritabanına kaydet
                prediction = ModelPrediction(
                    model_id=db_model.model_id,
                    symbol=asset.symbol,
                    timestamp=datetime.now(timezone.utc),
                    prediction_value=pred_val,
                    probability=prob_val,
                    confidence=prob_val if pred_val == 1 else (1.0 - prob_val),
                    horizon="5D",
                    feature_version=db_model.feature_version,
                    dataset_version=db_model.dataset_version,
                    calibration_score=db_model.metrics.get("brier_score", 0.0),
                    created_at=datetime.now(timezone.utc)
                )
                
                db.add(prediction)
                logger.info(f"{asset.symbol} yön tahmini kaydedildi: P(UP) = %{prob_val*100:.1f}")
                
            db.commit()
            
    except Exception as e:
        logger.error(f"Prediction Worker çalışırken hata: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_prediction_worker()
