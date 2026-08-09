import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from packages.common.config import settings

logger = logging.getLogger("axonforge.risk.gate")

class RiskGate:
    """Emirlerin aracı kuruma gönderilmeden önce limit ve risk kontrollerinden geçmesini sağlayan koruma geçidi."""
    
    def __init__(self):
        # Ayarları yükle
        self.max_pos_pct = settings.MAX_POSITION_SIZE_PCT
        self.max_daily_loss = settings.MAX_DAILY_LOSS_LIMIT
        self.max_exposure_pct = settings.MAX_PORTFOLIO_EXPOSURE_PCT
        self.freshness_limit = settings.DATA_FRESHNESS_LIMIT_SECONDS

    def validate_order(
        self,
        symbol: str,
        side: str,  # BUY, SELL
        quantity: float,
        price: float,
        portfolio_value: float,
        cash: float,
        existing_qty: float,
        daily_realized_loss: float,
        market_price_time: datetime,
        avg_daily_volume: float = 0.0,
        market_open: bool = True
    ) -> Tuple[bool, str]:
        """
        Emrin risk limitlerini ihlal edip etmediğini doğrular.
        Döndürdüğü değer: (onaylandı_mi: bool, gerekce: str)
        """
        side = side.upper()
        order_value = quantity * price
        
        # 1. Seans Kontrolü
        if not market_open:
            return False, "BLOCKED: Piyasa kapalıyken emir gönderilemez."
            
        # 2. Veri Tazeliği Kontrolü
        now_utc = datetime.now(timezone.utc)
        if market_price_time.tzinfo is None:
            market_price_time = market_price_time.replace(tzinfo=timezone.utc)
            
        age_seconds = (now_utc - market_price_time).total_seconds()
        if age_seconds > self.freshness_limit:
            return False, f"BLOCKED: Fiyat verisi çok eski ({int(age_seconds)} saniye). Limit: {self.freshness_limit} saniye."

        if side == "BUY":
            # 3. Yetersiz Bakiye Kontrolü
            if order_value > cash:
                return False, f"BLOCKED: Yetersiz nakit bakiye. Emir değeri: {order_value:.2f}, Mevcut nakit: {cash:.2f}."

            # 4. Pozisyon Büyüklüğü Sınırı (Max Position Size Pct)
            new_pos_value = (existing_qty * price) + order_value
            new_pos_pct = new_pos_value / portfolio_value if portfolio_value > 0 else 1.0
            if new_pos_pct > self.max_pos_pct:
                return False, f"BLOCKED: Pozisyon limiti aşıldı. Tek hisse limiti %{self.max_pos_pct*100:.1f}, Talep edilen: %{new_pos_pct*100:.1f}."

            # 5. Toplam Portföy Maruziyeti (Max Exposure Pct)
            current_exposure = portfolio_value - cash
            new_exposure = current_exposure + order_value
            new_exposure_pct = new_exposure / portfolio_value if portfolio_value > 0 else 1.0
            if new_exposure_pct > self.max_exposure_pct:
                return False, f"BLOCKED: Toplam portföy maruziyet sınırı aşıldı. Limit %{self.max_exposure_pct*100:.1f}, Talep edilen: %{new_exposure_pct*100:.1f}."

        elif side == "SELL":
            # Satışta yetersiz hisse kontrolü
            if quantity > existing_qty:
                return False, f"BLOCKED: Yetersiz hisse miktarı. Satılmak istenen: {quantity}, Portföydeki: {existing_qty}."

        # 6. Günlük Zarar Limiti Kontrolü
        if daily_realized_loss >= self.max_daily_loss:
            return False, f"BLOCKED: Günlük maksimum zarar limitine ulaşıldı ({self.max_daily_loss} TRY)."

        # 7. Likidite Kontrolü
        if avg_daily_volume > 0 and quantity > (avg_daily_volume * 0.10):  # Günlük hacmin %10'undan büyük tek emir engellenir
            return False, f"BLOCKED: Düşük likidite uyarısı. Emir hacmi günlük ortalamanın %10'undan büyük."

        return True, "PASSED: Risk kontrolleri onaylandı."
