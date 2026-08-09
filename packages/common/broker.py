import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from packages.common.config import settings

logger = logging.getLogger("axonforge.broker")

class BrokerProvider:
    """Aracı kurum entegrasyonu için soyut taban sınıf."""
    
    def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
        
    def cancel_order(self, order_id: int) -> bool:
        raise NotImplementedError
        
    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError
        
    def get_cash(self) -> float:
        raise NotImplementedError

class PaperBroker(BrokerProvider):
    """Sanal bakiye ve anlık fiyatlarla çalışan simüle edilmiş aracı kurum."""
    
    def __init__(self, commission_rate: float = 0.001, slippage_rate: float = 0.0005):
        self.commission_rate = commission_rate  # Binde 1 komisyon
        self.slippage_rate = slippage_rate      # On binde 5 slippage

    def process_order_execution(
        self,
        order: Dict[str, Any],
        current_price: float,
        cash: float,
        existing_qty: float
    ) -> Dict[str, Any]:
        """
        Emrin doldurulup doldurulamayacağını simüle eder.
        Döndürür: {
            "status": "FILLED" veya "REJECTED" veya "SUBMITTED",
            "fill_price": float,
            "commission": float,
            "slippage": float,
            "cash_change": float,
            "qty_change": float
        }
        """
        order_type = order["type"].upper()
        side = order["side"].upper()
        qty = order["quantity"]
        limit_price = order.get("price")
        stop_price = order.get("stop_price")
        
        result = {
            "status": "SUBMITTED",
            "fill_price": 0.0,
            "commission": 0.0,
            "slippage": 0.0,
            "cash_change": 0.0,
            "qty_change": 0.0
        }
        
        # MARKET emirleri anında gerçekleşir
        if order_type == "MARKET":
            # Slippage hesabı
            slippage = current_price * self.slippage_rate
            fill_price = current_price + slippage if side == "BUY" else current_price - slippage
            
            # Komisyon hesabı
            value = qty * fill_price
            commission = value * self.commission_rate
            
            result["status"] = "FILLED"
            result["fill_price"] = fill_price
            result["commission"] = commission
            result["slippage"] = slippage
            
            if side == "BUY":
                result["cash_change"] = -(value + commission)
                result["qty_change"] = qty
            else:
                result["cash_change"] = (value - commission)
                result["qty_change"] = -qty
                
        # LIMIT emirleri
        elif order_type == "LIMIT":
            if limit_price is None:
                result["status"] = "REJECTED"
                return result
                
            is_triggered = False
            if side == "BUY" and current_price <= limit_price:
                is_triggered = True
            elif side == "SELL" and current_price >= limit_price:
                is_triggered = True
                
            if is_triggered:
                # Limit fiyattan gerçekleşme varsayımı
                fill_price = limit_price
                value = qty * fill_price
                commission = value * self.commission_rate
                
                result["status"] = "FILLED"
                result["fill_price"] = fill_price
                result["commission"] = commission
                
                if side == "BUY":
                    result["cash_change"] = -(value + commission)
                    result["qty_change"] = qty
                else:
                    result["cash_change"] = (value - commission)
                    result["qty_change"] = -qty
                    
        # STOP / STOP LIMIT emirleri
        elif order_type in ["STOP", "STOP_LIMIT"]:
            if stop_price is None:
                result["status"] = "REJECTED"
                return result
                
            is_triggered = False
            if side == "BUY" and current_price >= stop_price:
                is_triggered = True
            elif side == "SELL" and current_price <= stop_price:
                is_triggered = True
                
            if is_triggered:
                # Stop tetiklendiğinde market emrine dönüşür
                fill_price = current_price
                value = qty * fill_price
                commission = value * self.commission_rate
                
                result["status"] = "FILLED"
                result["fill_price"] = fill_price
                result["commission"] = commission
                
                if side == "BUY":
                    result["cash_change"] = -(value + commission)
                    result["qty_change"] = qty
                else:
                    result["cash_change"] = (value - commission)
                    result["qty_change"] = -qty
                    
        return result
