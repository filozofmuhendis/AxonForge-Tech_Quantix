import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from packages.common.models import DecisionJournal, TradeProposal

logger = logging.getLogger("axonforge.journal")

class JournalManager:
    """Yatırım kararlarının, tezlerinin ve geçmiş hata değerlendirmelerinin kaydını tutan günlük yöneticisi."""

    def create_journal_entry(
        self,
        db: Session,
        proposal_id: int,
        thesis_text: str,
        entry_reasoning: str,
        regime_at_entry: str,
        risk_metrics: Dict[str, Any]
    ) -> DecisionJournal:
        """Yeni bir işlem tezi ve giriş gerekçesi içeren günlük kaydı oluşturur."""
        
        # Daha önce oluşturulmuş mu kontrol et
        existing = db.query(DecisionJournal).filter(DecisionJournal.proposal_id == proposal_id).first()
        if existing:
            existing.thesis_text = thesis_text
            existing.entry_reasoning = entry_reasoning
            existing.regime_at_entry = regime_at_entry
            existing.risk_metrics_at_entry = risk_metrics
            existing.updated_at = datetime.utcnow()
            db.commit()
            return existing
            
        entry = DecisionJournal(
            proposal_id=proposal_id,
            thesis_text=thesis_text,
            entry_reasoning=entry_reasoning,
            regime_at_entry=regime_at_entry,
            risk_metrics_at_entry=risk_metrics,
            created_at=datetime.utcnow()
        )
        
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"Yeni karar günlüğü kaydı oluşturuldu (Teklif ID: {proposal_id})")
        return entry

    def close_journal_entry(
        self,
        db: Session,
        proposal_id: int,
        exit_reasoning: str,
        actual_pnl: float,
        post_evaluation_text: str
    ) -> Optional[DecisionJournal]:
        """Kapanan pozisyonun çıkış gerekçesini, kâr/zararını ve yapay zeka/kullanıcı değerlendirmesini günlüğe yazar."""
        entry = db.query(DecisionJournal).filter(DecisionJournal.proposal_id == proposal_id).first()
        
        if not entry:
            logger.warning(f"Kapatılmak istenen günlüğe ait giriş kaydı bulunamadı (Teklif ID: {proposal_id})")
            return None
            
        entry.exit_reasoning = exit_reasoning
        entry.actual_outcome_pnl = actual_pnl
        entry.post_trade_evaluation = post_evaluation_text
        entry.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(entry)
        logger.info(f"Karar günlüğü kaydı işlem sonuçlandırılarak güncellendi (Teklif ID: {proposal_id})")
        return entry

    def get_journal_history(self, db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Geçmiş günlük kayıtlarını ilişkili teklif bilgileriyle birlikte listeler."""
        entries = db.query(DecisionJournal).join(TradeProposal).order_by(DecisionJournal.created_at.desc()).limit(limit).all()
        
        history = []
        for e in entries:
            prop = e.proposal
            history.append({
                "journal_id": e.id,
                "proposal_id": e.proposal_id,
                "symbol": prop.symbol,
                "direction": prop.direction,
                "thesis": e.thesis_text,
                "entry_reasoning": e.entry_reasoning,
                "exit_reasoning": e.exit_reasoning,
                "market_regime": e.regime_at_entry,
                "risk_metrics": e.risk_metrics_at_entry,
                "actual_pnl": e.actual_outcome_pnl,
                "post_evaluation": e.post_trade_evaluation,
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
            
        return history
