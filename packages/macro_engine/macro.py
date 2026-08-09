import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from packages.common.models import MacroObservation

logger = logging.getLogger("axonforge.macro")

# Desteklenen Makro Göstergeler
TR_INDICATORS = ["TCMB_RATE", "TUFE", "UFE", "CDS", "BIST_10Y_YIELD"]
US_INDICATORS = ["FED_RATE", "US_CPI", "US_PCE", "US_NFP", "VIX", "DXY", "US_10Y_YIELD"]

class MacroEngine:
    """TCMB ve FED makroekonomik göstergelerinin veri takibi, vintage (as-of) zaman serisi yönetimi sınıfı."""

    def register_observation(
        self,
        db: Session,
        indicator_name: str,
        category: str,  # TCMB veya FED
        value: float,
        timestamp: datetime,
        provider_name: str = "TCMB_EVDS"
    ) -> MacroObservation:
        """Yeni bir makro gözlemi sisteme kaydeder."""
        indicator_name = indicator_name.upper()
        category = category.upper()
        
        # UTC zaman dilimi koruması
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)
            
        # Mükerrer kaydı önle
        existing = db.query(MacroObservation).filter(
            MacroObservation.indicator_name == indicator_name,
            MacroObservation.category == category,
            MacroObservation.timestamp == timestamp
        ).first()
        
        now_utc = datetime.now(timezone.utc)
        
        if existing:
            existing.value = value
            existing.fetched_at = now_utc
            db.commit()
            return existing
            
        observation = MacroObservation(
            indicator_name=indicator_name,
            category=category,
            timestamp=timestamp,
            value=value,
            provider_name=provider_name,
            fetched_at=now_utc,
            data_quality_score=100.0
        )
        
        db.add(observation)
        db.commit()
        db.refresh(observation)
        return observation

    def get_observation_as_of(
        self,
        db: Session,
        indicator_name: str,
        category: str,
        as_of_date: datetime
    ) -> Optional[MacroObservation]:
        """
        Geriye dönük testlerde (backtesting) revision bias ve look-ahead bias'ı engellemek amacıyla;
        belirtilen as_of_date itibariyle yayınlanmış (yani veritabanına daha önceden çekilmiş)
        en güncel gözlemi getirir.
        """
        indicator_name = indicator_name.upper()
        category = category.upper()
        
        if as_of_date.tzinfo is None:
            as_of_date = as_of_date.replace(tzinfo=timezone.utc)
            
        # fetched_at (verinin sisteme ulaştığı an) <= as_of_date koşulu revision bias'ı strictly engeller.
        return db.query(MacroObservation).filter(
            MacroObservation.indicator_name == indicator_name,
            MacroObservation.category == category,
            MacroObservation.fetched_at <= as_of_date
        ).order_by(MacroObservation.timestamp.desc()).first()

    def get_latest_macro_summary(self, db: Session) -> Dict[str, Any]:
        """Tüm kayıtlı makro indikatörlerin en son değerlerini özet olarak döndürür."""
        summary = {"TR": {}, "US": {}}
        
        # Türkiye
        for ind in TR_INDICATORS:
            obs = db.query(MacroObservation).filter(
                MacroObservation.indicator_name == ind,
                MacroObservation.category == "TCMB"
            ).order_by(MacroObservation.timestamp.desc()).first()
            if obs:
                summary["TR"][ind] = {
                    "value": obs.value,
                    "date": obs.timestamp.strftime("%Y-%m-%d"),
                    "provider": obs.provider_name
                }
                
        # ABD
        for ind in US_INDICATORS:
            obs = db.query(MacroObservation).filter(
                MacroObservation.indicator_name == ind,
                MacroObservation.category == "FED"
            ).order_by(MacroObservation.timestamp.desc()).first()
            if obs:
                summary["US"][ind] = {
                    "value": obs.value,
                    "date": obs.timestamp.strftime("%Y-%m-%d"),
                    "provider": obs.provider_name
                }
                
        return summary
