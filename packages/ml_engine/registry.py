import os
import joblib
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from packages.common.config import settings
from packages.common.models import ModelRegistry
from sqlalchemy.orm import Session

logger = logging.getLogger("axonforge.ml.registry")

class ModelRegistryManager:
    """Modellerin kaydedilmesi, yüklenmesi ve versiyonlanmasını yöneten registry."""
    
    def __init__(self, registry_dir: str = "models/registry"):
        self.registry_dir = registry_dir
        # Klasörün varlığından emin ol
        os.makedirs(self.registry_dir, exist_ok=True)

    def register_model(
        self,
        db: Session,
        model_obj: Any,  # AxonForgeMLModel nesnesi
        model_id: str,
        version: str,
        dataset_version: str,
        feature_version: str,
        training_period: Dict[str, str],
        metrics: Dict[str, Any]
    ) -> ModelRegistry:
        """Eğitilen modeli disk üzerine yazar ve veritabanına kaydeder."""
        filename = f"{model_id}_{version}.joblib"
        filepath = os.path.join(self.registry_dir, filename)
        
        # 1. Modeli diske kaydet
        joblib.dump(model_obj, filepath)
        logger.info(f"Model disk üzerine kaydedildi: {filepath}")
        
        # 2. Veritabanı kaydı oluştur veya güncelle
        db_model = db.query(ModelRegistry).filter(
            ModelRegistry.model_id == model_id,
            ModelRegistry.version == version
        ).first()
        
        if not db_model:
            db_model = ModelRegistry(
                model_id=model_id,
                version=version,
                algorithm=model_obj.algorithm,
                training_period=training_period,
                features=model_obj.feature_names,
                dataset_version=dataset_version,
                metrics=metrics,
                status=model_obj.status,
                created_at=datetime.utcnow()
            )
            db.add(db_model)
        else:
            db_model.metrics = metrics
            db_model.status = model_obj.status
            db_model.dataset_version = dataset_version
            db_model.features = model_obj.feature_names
            
        db.commit()
        db.refresh(db_model)
        return db_model

    def load_model(self, db: Session, model_id: str, version: str) -> Optional[Any]:
        """İstenen versiyondaki modeli veritabanı kontrolünden sonra diskten yükler."""
        db_model = db.query(ModelRegistry).filter(
            ModelRegistry.model_id == model_id,
            ModelRegistry.version == version
        ).first()
        
        if not db_model:
            logger.error(f"Kayıtlı model bulunamadı: {model_id} v{version}")
            return None
            
        filename = f"{model_id}_{version}.joblib"
        filepath = os.path.join(self.registry_dir, filename)
        
        if not os.path.exists(filepath):
            logger.error(f"Model dosyası diskte bulunamadı: {filepath}")
            return None
            
        try:
            model_obj = joblib.load(filepath)
            model_obj.status = db_model.status  # veritabanı durumunu eşitle
            return model_obj
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            return None
