import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve
from typing import Dict, Any, List, Tuple, Optional

class AxonForgeMLModel:
    """Olasılıksal getiri tahmin modellerinin eğitimi, kalibrasyonu ve yönetimi."""
    
    def __init__(self, algorithm: str = "random_forest", model_id: str = "default_model"):
        self.algorithm = algorithm.lower()
        self.model_id = model_id
        self.model = None
        self.feature_names = []
        self.status = "PRODUCTION"  # PRODUCTION, DEGRADED, RETIRED
        self.brier_score = 1.0
        self.feature_importances = {}

    def _initialize_model(self):
        if self.algorithm == "logistic_regression":
            self.model = LogisticRegression(max_iter=500)
        elif self.algorithm == "gradient_boosting":
            self.model = GradientBoostingClassifier(n_estimators=100, max_depth=5)
        elif self.algorithm == "xgboost":
            try:
                import xgboost as xgb
                self.model = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.05, random_state=42, eval_metric='logloss')
            except ImportError:
                logger.warning("XGBoost bulunamadı. Fallback olarak GradientBoostingClassifier kullanılıyor.")
                self.model = GradientBoostingClassifier(n_estimators=100, max_depth=5)
        else:  # Varsayılan: Random Forest
            self.model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)


    def train(self, X_train: pd.DataFrame, y_train: pd.Series, feature_names: List[str]):
        """Modeli eğitir ve öznitelik önem düzeylerini hesaplar."""
        self.feature_names = feature_names
        self._initialize_model()
        
        # Sadece seçilen öznitelikleri eğit
        X = X_train[feature_names].values
        y = y_train.values
        
        self.model.fit(X, y)
        
        # Öznitelik Önemlerini Hesaplama
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            self.feature_importances = {
                feature_names[i]: float(importances[i]) for i in range(len(feature_names))
            }
        elif hasattr(self.model, "coef_"):
            # Lojistik Regresyon katsayıları
            importances = np.abs(self.model.coef_[0])
            importances = importances / np.sum(importances)  # normalize
            self.feature_importances = {
                feature_names[i]: float(importances[i]) for i in range(len(feature_names))
            }
        else:
            self.feature_importances = {f: 1.0/len(feature_names) for f in feature_names}

    def predict_probability(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Sınıf olasılıklarını tahmin eder. P(Yön = 1) olasılığını döndürür."""
        X_mat = X[self.feature_names].values
        probs = self.model.predict_proba(X_mat)
        
        # Yön olasılığı (Sınıf 1: Yükseliş getirisi > Eşik)
        probability_up = probs[:, 1]
        predictions = (probability_up > 0.50).astype(int)
        
        return predictions, probability_up

    def evaluate_calibration(self, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
        """Model kalibrasyonunu ve Brier skorunu analiz eder."""
        preds, probs = self.predict_probability(X_val)
        y = y_val.values
        
        # Brier Skoru Hesaplama (0 en iyi, 1 en kötü olasılık tahmini kalitesi)
        self.brier_score = float(brier_score_loss(y, probs))
        
        # Kalibrasyon eğrisi hesaplama
        prob_true, prob_pred = calibration_curve(y, probs, n_bins=5)
        
        # Kalibrasyon durumunu Brier skoruna göre derecelendir
        # Brier skoru < 0.20 ise mükemmel, > 0.30 ise bozulmuş kabul edilir
        if self.brier_score > 0.28:
            self.status = "DEGRADED"
        elif self.brier_score > 0.40:
            self.status = "RETIRED"
        else:
            self.status = "PRODUCTION"
            
        return {
            "brier_score": round(self.brier_score, 4),
            "model_status": self.status,
            "calibration_curve": {
                "true_probabilities": [round(float(v), 4) for v in prob_true],
                "pred_probabilities": [round(float(v), 4) for v in prob_pred]
            }
        }

    def check_drift(self, initial_brier: float, current_brier: float) -> str:
        """Model sapmasını (drift) izler ve durum güncellemesi yapar."""
        drift_pct = (current_brier - initial_brier) / initial_brier if initial_brier > 0 else 0.0
        
        if drift_pct > 0.25:  # Hata payında %25'ten fazla artış
            self.status = "DEGRADED"
            logger.warning(f"MODEL_DRIFT_DETECTED: Model {self.model_id} kalitesi bozuldu. Durum: DEGRADED.")
        
        return self.status
