import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from packages.common.config import settings

logger = logging.getLogger("axonforge.signal")

class SignalEngine:
    """Teknik, temel, ML ve makro verileri birleştirerek kompozit işlem sinyalleri üreten motor."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        # Varsayılan sinyal bileşen ağırlıkları
        self.weights = weights or {
            "technical": 0.20,
            "momentum": 0.20,
            "ml_probability": 0.30,
            "fundamental": 0.15,
            "news": 0.05,
            "macro": 0.10
        }
        # Ağırlıkların toplamının 1.0 olduğunu doğrula
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def calculate_composite_signal(
        self,
        symbol: str,
        technical_score: float,       # 0-100
        momentum_score: float,        # 0-100
        ml_probability: float,        # 0-1 (tahmin edilen olasılık)
        fundamental_score: float,     # 0-100
        news_sentiment: float,        # -1 ile +1 arası
        macro_score: float,           # 0-100
        market_regime: str,
        data_quality_score: float,
        model_calibration: float,     # 1 - Brier score (0-1)
        analog_similarity: float,     # 0-1 (tarihsel analog benzerliği)
        regime_stability: float,      # 0-1
        risk_confidence: float        # 0-1 (riske maruz değer payı)
    ) -> Dict[str, Any]:
        """
        Sinyal skorunu ve ayrıştırılmış 6 güven parametresini hesaplar.
        Veri kalitesi ve risk cezalarını (penalty) uygular.
        """
        # ML olasılığını 0-100 aralığına çek
        ml_score = ml_probability * 100
        
        # Haber sentiment skoru (-1 ile +1 arası) -> 0-100 aralığına yerleştir
        news_score = (news_sentiment + 1.0) * 50.0
        
        # Kompozit Puan Hesaplama
        raw_score = (
            technical_score * self.weights["technical"] +
            momentum_score * self.weights["momentum"] +
            ml_score * self.weights["ml_probability"] +
            fundamental_score * self.weights["fundamental"] +
            news_score * self.weights["news"] +
            macro_score * self.weights["macro"]
        )
        
        # Veri kalitesi 70'in altındaysa ceza uygula
        penalty = 0.0
        if data_quality_score < 70.0:
            penalty += (70.0 - data_quality_score) * 0.5
            
        # Rejim risk cezası (Kriz anlarında skoru düşürür)
        if market_regime == "CRISIS":
            penalty += 15.0
        elif market_regime == "HIGH_VOLATILITY":
            penalty += 5.0
            
        composite_score = max(0.0, min(100.0, raw_score - penalty))
        
        # Sinyal Sınıflandırma (8-State Model)
        if composite_score >= 85:
            signal_type = "STRONG_BUY"
        elif composite_score >= 70:
            signal_type = "BUY"
        elif composite_score >= 55:
            signal_type = "WEAK_BUY"
        elif composite_score >= 45:
            signal_type = "HOLD"
        elif composite_score >= 35:
            signal_type = "WATCH"
        elif composite_score >= 25:
            signal_type = "WEAK_SELL"
        elif composite_score >= 10:
            signal_type = "SELL"
        else:
            signal_type = "STRONG_SELL"

            
        # 6 Ayrıştırılmış Güven Parametresi (Decomposed Confidence Parameters)
        signal_confidence = composite_score / 100.0
        
        confidence_breakdown = {
            "signal_confidence": round(signal_confidence, 4),
            "model_calibration": round(model_calibration, 4),
            "data_quality": round(data_quality_score / 100.0, 4),
            "historical_analog_strength": round(analog_similarity, 4),
            "market_regime_stability": round(regime_stability, 4),
            "risk_confidence": round(risk_confidence, 4)
        }
        
        # Karar İzleme (Data Lineage & Decision Trace) Yapısı
        now_utc = datetime.now(timezone.utc)
        decision_trace = {
            "symbol": symbol,
            "signal_type": signal_type,
            "composite_score": round(composite_score, 2),
            "timestamp": now_utc.isoformat(),
            "weights": self.weights,
            "inputs": {
                "technical": round(technical_score, 2),
                "momentum": round(momentum_score, 2),
                "ml_probability": round(ml_probability, 4),
                "fundamental": round(fundamental_score, 2),
                "news_sentiment": round(news_sentiment, 2),
                "macro_score": round(macro_score, 2),
                "market_regime": market_regime,
                "data_quality_score": round(data_quality_score, 2)
            },
            "confidence_breakdown": confidence_breakdown,
            "penalties_applied": round(penalty, 2)
        }
        
        return {
            "symbol": symbol,
            "signal_type": signal_type,
            "score": round(composite_score, 2),
            "confidence_breakdown": confidence_breakdown,
            "decision_trace": decision_trace,
            "market_regime_state": market_regime,
            "data_quality_score": data_quality_score,
            "analog_similarity": analog_similarity
        }

    def generate_trade_proposal(
        self,
        signal_result: Dict[str, Any],
        current_price: float,
        atr: float,
        portfolio_value: float
    ) -> Optional[Dict[str, Any]]:
        """
        Sinyal BUY veya STRONG_BUY ise işlem önerisi (Trade Proposal) oluşturur.
        Risk/Ödül, Stop Loss ve Target seviyelerini ATR çarpanına göre belirler.
        """
        signal_type = signal_result["signal_type"]
        if signal_type not in ["BUY", "STRONG_BUY"]:
            return None  # Sadece alış sinyallerinde işlem önerisi üretilir
            
        symbol = signal_result["symbol"]
        
        # Teknik kurallarla Stop ve Target belirleme (ATR çarpanı kullanarak)
        # Giriş Bölgesi: anlık fiyatın %0.5 altı ve üstü
        min_entry = current_price * 0.995
        max_entry = current_price * 1.005
        
        # Stop loss: Giriş fiyatından 2 * ATR aşağısı
        stop_loss = current_price - (2.0 * atr)
        if stop_loss <= 0:
            stop_loss = current_price * 0.95  # Fallback %5 stop
            
        # Target: Giriş fiyatından 4 * ATR yukarısı (Minimum 1:2 R/R oranı)
        target_price = current_price + (4.0 * atr)
        
        risk_per_share = current_price - stop_loss
        reward_per_share = target_price - current_price
        risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 2.0
        
        # Pozisyon Büyüklüğü Hesaplama: Toplam portföyün %2'lik risk kuralı
        # Risk Miktarı = Portföy * %2
        risk_amount = portfolio_value * 0.02
        position_size_shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
        
        # Portföy limitlerine göre maks pozisyon büyüklüğü kontrolü (Örn: Maks %10 sermaye tahsisi)
        max_capital_allocation = portfolio_value * settings.MAX_POSITION_SIZE_PCT
        if (position_size_shares * current_price) > max_capital_allocation:
            position_size_shares = max_capital_allocation / current_price
            
        position_size_shares = round(position_size_shares, 2)
        total_investment = position_size_shares * current_price
        
        reason = (
            f"Kompozit Sinyal Skoru {signal_result['score']} ({signal_type}). "
            f"Piyasa rejimi: {signal_result['market_regime_state']}. "
            f"Tarihsel analog benzerlik gücü: %{signal_result['analog_similarity']*100:.1f}. "
            f"Yapay zeka yön olasılığı tahmini: %{signal_result['decision_trace']['inputs']['ml_probability']*100:.1f}."
        )
        
        return {
            "symbol": symbol,
            "direction": "BUY",
            "entry_zone": {"min": round(min_entry, 2), "max": round(max_entry, 2)},
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "position_size": position_size_shares,
            "risk_amount": round(position_size_shares * risk_per_share, 2),
            "total_investment": round(total_investment, 2),
            "holding_horizon": "10D",
            "reason": reason,
            "invalidation_conditions": "Piyasa rejiminin kriz durumuna geçmesi, destek seviyesinin kırılması veya hedefin altına inen makroekonomik veriler."
        }
