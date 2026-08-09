import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("axonforge.portfolio")

class PortfolioManager:
    """Portföy değerleme, maliyet ve çok boyutlu maruziyet (exposure) yönetim sınıfı."""
    
    def __init__(self, portfolio_id: int, base_currency: str = "TRY"):
        self.portfolio_id = portfolio_id
        self.base_currency = base_currency.upper()

    def calculate_position_details(
        self,
        positions: List[Dict[str, Any]],
        current_prices: Dict[str, float],
        fx_rates: Dict[str, float]  # Örn: {"USDTRY": 32.50, "EURTRY": 35.10}
    ) -> Dict[str, Any]:
        """
        Portföydeki açık pozisyonların maliyetlerini, güncel değerlerini, kâr/zarar durumlarını
        ve 6 boyutlu maruziyetlerini (Varlık, Sektör, Ülke, Para Birimi, Borsa/Piyasa, Faktör)
        base_currency cinsinden hesaplar.
        """
        total_value = 0.0
        total_cost = 0.0
        position_details = []
        
        # Çok boyutlu maruziyet havuzları
        sector_exposure = {}
        country_exposure = {}
        asset_class_exposure = {}
        currency_exposure = {}
        market_exposure = {}
        factor_exposure = {}
        
        for pos in positions:
            symbol = pos["symbol"]
            qty = pos["quantity"]
            cost = pos["cost_basis"]
            currency = pos["currency"].upper()
            
            # Güncel fiyat, yoksa maliyet
            curr_price = current_prices.get(symbol, cost)
            
            # FX kur çevrim katsayısı
            conversion_rate = 1.0
            if currency != self.base_currency:
                pair = f"{currency}{self.base_currency}"
                reverse_pair = f"{self.base_currency}{currency}"
                
                if pair in fx_rates:
                    conversion_rate = fx_rates[pair]
                elif reverse_pair in fx_rates and fx_rates[reverse_pair] > 0:
                    conversion_rate = 1.0 / fx_rates[reverse_pair]
                else:
                    logger.warning(f"FX conversion rate not found for {pair}. Using 1.0.")
            
            # Getiri hesapları
            pos_cost_base = qty * cost * conversion_rate
            pos_value_base = qty * curr_price * conversion_rate
            unrealized_pnl = pos_value_base - pos_cost_base
            unrealized_pnl_pct = (unrealized_pnl / pos_cost_base) if pos_cost_base > 0 else 0.0
            
            total_cost += pos_cost_base
            total_value += pos_value_base
            
            # Metadata bilgileri
            sector = pos.get("sector", "Bilinmeyen")
            country = pos.get("country", "Bilinmeyen")
            asset_class = pos.get("asset_class", "EQUITY")
            
            # Market (Borsa/Piyasa) tespiti
            exchange = pos.get("exchange", "Bilinmeyen").upper()
            if "BIST" in exchange or symbol.endswith(".IS"):
                market = "BIST"
            elif "NYSE" in exchange or "NASDAQ" in exchange or country == "US":
                market = "US_MARKET"
            elif "LSE" in exchange or "LONDON" in exchange:
                market = "LSE"
            else:
                market = "OTHER_MARKET"
                
            # Factor (Beta bazlı agresif/defansif sınıflandırması)
            beta = float(pos.get("beta", 1.0))
            if beta > 1.2:
                factor = "HIGH_BETA_AGGRESSIVE"
            elif beta < 0.8:
                factor = "LOW_BETA_DEFENSIVE"
            else:
                factor = "MARKET_BETA_NEUTRAL"
            
            pos_info = {
                "symbol": symbol,
                "quantity": qty,
                "cost_basis": cost,
                "current_price": curr_price,
                "currency": currency,
                "cost_in_base": round(pos_cost_base, 2),
                "value_in_base": round(pos_value_base, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct * 100, 2),
                "sector": sector,
                "country": country,
                "asset_class": asset_class,
                "market": market,
                "factor": factor,
                "beta": beta
            }
            position_details.append(pos_info)
            
            # Maruziyetleri topla
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + pos_value_base
            country_exposure[country] = country_exposure.get(country, 0.0) + pos_value_base
            asset_class_exposure[asset_class] = asset_class_exposure.get(asset_class, 0.0) + pos_value_base
            currency_exposure[currency] = currency_exposure.get(currency, 0.0) + pos_value_base
            market_exposure[market] = market_exposure.get(market, 0.0) + pos_value_base
            factor_exposure[factor] = factor_exposure.get(factor, 0.0) + pos_value_base
            
        # Maruziyet oranlarını yüzdesel hale getir
        def to_pct(ex_dict, total):
            if total <= 0:
                return {}
            return {k: round((v / total) * 100, 2) for k, v in ex_dict.items()}

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) if total_cost > 0 else 0.0

        return {
            "base_currency": self.base_currency,
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct * 100, 2),
            "positions": position_details,
            "exposures": {
                "sector": to_pct(sector_exposure, total_value),
                "country": to_pct(country_exposure, total_value),
                "asset_class": to_pct(asset_class_exposure, total_value),
                "currency": to_pct(currency_exposure, total_value),
                "market": to_pct(market_exposure, total_value),
                "factor": to_pct(factor_exposure, total_value)
            }
        }
