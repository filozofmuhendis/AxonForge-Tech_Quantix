from typing import Dict, Any, List
import logging

logger = logging.getLogger("axonforge.risk.stress")

class StressTestEngine:
    """Belirli makro senaryolar ve tahvil faiz şokları altında portföy etki simülasyon motoru."""

    def simulate_scenario(
        self,
        positions: List[Dict[str, Any]],  # Pozisyon detayları (maliyet, değer, sektör, para birimi, ülke vb.)
        betas: Dict[str, float],          # Varlıkların ilgili endekse göre betaları (ör: {"THYAO": 1.2, "AAPL": 1.1})
        shocks: Dict[str, float],         # Şoklar (ör: {"BIST": -0.15, "NASDAQ": -0.12, "USDTRY": 0.10, "GOLD": 0.08, "US10Y": 100})
        base_currency: str = "TRY"
    ) -> Dict[str, Any]:
        """
        Şok senaryolarını portföye uygular ve beklenen etkileri döndürür.
        Faktörler:
        - Doğrudan endeks şoku (BIST ve NASDAQ hisselerinin betalarına göre etkilenmesi)
        - Döviz kurlarındaki değişimler (Para birimi etkileri)
        - Doğrudan varlık sınıfı şokları (örn: Altın şoku)
        - Faiz/Tahvil Şoku (US10Y tahvil faizinin yükselmesi sonucu büyüme/teknoloji hisselerinin değerleme baskısı yemesi)
        """
        total_initial_value = sum(pos["value_in_base"] for pos in positions)
        if total_initial_value <= 0:
            return {
                "senaryo_soklari": shocks,
                "portfoy_baslangic_degeri": 0.0,
                "portfoy_beklenen_pnl": 0.0,
                "portfoy_beklenen_pnl_yuzde": 0.0,
                "pozisyon_etkileri": [],
                "kırilimlar": {"sektor": {}, "para_birimi": {}}
            }
            
        total_pnl = 0.0
        position_impacts = []
        sector_pnl = {}
        currency_pnl = {}
        
        for pos in positions:
            symbol = pos["symbol"]
            val_base = pos["value_in_base"]
            currency = pos["currency"].upper()
            sector = pos["sector"]
            beta = betas.get(symbol, 1.0)
            
            # 1. Döviz kuru şok etkisi (örn: USDTRY +10%)
            fx_shock = 0.0
            if currency == "USD" and "USDTRY" in shocks:
                fx_shock = shocks["USDTRY"]
            elif currency == "EUR" and "EURTRY" in shocks:
                fx_shock = shocks["EURTRY"]
                
            # 2. Varlık fiyat değişim şok etkisi
            price_change_pct = 0.0
            
            # Altın / Gümüş doğrudan şokları
            if symbol in ["XAUUSD", "GOLD"] and "GOLD" in shocks:
                price_change_pct = shocks["GOLD"]
            elif symbol in ["XAGUSD", "SILVER"] and "SILVER" in shocks:
                price_change_pct = shocks["SILVER"]
                
            # BIST endeks şoku ve beta duyarlılığı
            elif pos.get("country", "TR") == "TR" and "BIST" in shocks:
                price_change_pct = shocks["BIST"] * beta
                
            # ABD endeks şoku ve beta duyarlılığı (NYSE / NASDAQ)
            elif pos.get("country", "US") == "US" and "NASDAQ" in shocks:
                price_change_pct = shocks["NASDAQ"] * beta
                
            # Tahvil faizi şoku (örn: US10Y +100bp artışı)
            # Yükselen faizler yüksek büyüme (tech) ve yüksek beta hisselerini olumsuz etkiler (iskonto oranı artar)
            interest_drag = 0.0
            if "US10Y" in shocks and pos.get("asset_class", "EQUITY") == "EQUITY":
                # Her +100bp faiz artışı için beta * %1.5'lik bir değer kaybı baskısı simüle edilir.
                bp_shock = shocks["US10Y"]
                interest_drag = -0.015 * beta * (bp_shock / 100.0)
                
            # Toplam fiyat değişimi
            total_price_change = price_change_pct + interest_drag
            
            # Genel fallback: sembole özel doğrudan şok tanımlandıysa ez
            if symbol in shocks:
                total_price_change = shocks[symbol]
                
            # Şok sonrası değer hesabı
            expected_new_value = val_base * (1.0 + total_price_change) * (1.0 + fx_shock)
            expected_pnl = expected_new_value - val_base
            total_pnl += expected_pnl
            
            pnl_pct = (expected_pnl / val_base) if val_base > 0 else 0.0
            
            pos_impact = {
                "symbol": symbol,
                "initial_value": round(val_base, 2),
                "expected_pnl": round(expected_pnl, 2),
                "expected_new_value": round(expected_new_value, 2),
                "pnl_pct": round(pnl_pct * 100, 2),
                "factor_shock_pct": round(total_price_change * 100, 2),
                "interest_drag_pct": round(interest_drag * 100, 2),
                "fx_shock_pct": round(fx_shock * 100, 2)
            }
            position_impacts.append(pos_impact)
            
            # Kırılımlar
            sector_pnl[sector] = sector_pnl.get(sector, 0.0) + expected_pnl
            currency_pnl[currency] = currency_pnl.get(currency, 0.0) + expected_pnl
            
        portfolio_pnl_pct = (total_pnl / total_initial_value) if total_initial_value > 0 else 0.0
        
        return {
            "senaryo_soklari": shocks,
            "portfoy_baslangic_degeri": round(total_initial_value, 2),
            "portfoy_beklenen_pnl": round(total_pnl, 2),
            "portfoy_beklenen_pnl_yuzde": round(portfolio_pnl_pct * 100, 2),
            "pozisyon_etkileri": position_impacts,
            "kırilimlar": {
                "sektor": {k: round(v, 2) for k, v in sector_pnl.items()},
                "para_birimi": {k: round(v, 2) for k, v in currency_pnl.items()}
            }
        }
