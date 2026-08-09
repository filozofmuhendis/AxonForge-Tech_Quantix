import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List

class RiskEngine:
    """Finansal risk hesaplamalarını (VaR, Sharpe, ES, HHI, Kur/Likidite riskleri) yöneten motor."""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.rf = risk_free_rate

    def calculate_drawdown_metrics(self, portfolio_values: pd.Series) -> Tuple[float, pd.Series]:
        """Maksimum düşüş (Drawdown) ve drawdown serisini hesaplar."""
        if portfolio_values.empty:
            return 0.0, pd.Series()
        rolling_max = portfolio_values.cummax()
        drawdowns = (portfolio_values - rolling_max) / rolling_max
        max_drawdown = float(drawdowns.min())
        return abs(max_drawdown), drawdowns

    def calculate_risk_metrics(
        self,
        weights: Dict[str, float],
        returns_df: pd.DataFrame,  # Kolonlar sembol, indeks tarih, değerler getiri
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Portföy risk metriklerini hesaplar (Sharpe, Sortino, VaR, Expected Shortfall)."""
        symbols = list(weights.keys())
        if not symbols or returns_df.empty:
            return {}
            
        # Ağırlık vektörü
        w = np.array([weights[s] for s in symbols])
        # Sembollerin getirileri
        rets = returns_df[symbols].values
        
        # Günlük portföy getirileri
        port_daily_returns = np.dot(rets, w)
        port_series = pd.Series(port_daily_returns)
        
        # 1. Portföy Performans İstatistikleri
        mean_daily_return = np.mean(port_daily_returns)
        std_daily_return = np.std(port_daily_returns)
        
        annualized_return = mean_daily_return * 252
        annualized_volatility = std_daily_return * np.sqrt(252)
        
        # Sharpe Oranı
        sharpe = 0.0
        if annualized_volatility > 0:
            sharpe = (annualized_return - self.rf) / annualized_volatility
            
        # Downside Deviation & Sortino Oranı
        downside_returns = port_daily_returns[port_daily_returns < 0]
        sortino = 0.0
        if len(downside_returns) > 0:
            downside_deviation = np.std(downside_returns) * np.sqrt(252)
            if downside_deviation > 0:
                sortino = (annualized_return - self.rf) / downside_deviation
                
        # Kumülatif Getiri & Max Drawdown
        cum_returns = (1 + port_series).cumprod()
        max_dd, _ = self.calculate_drawdown_metrics(cum_returns)
        
        # Calmar Oranı
        calmar = 0.0
        if max_dd > 0:
            calmar = annualized_return / max_dd

        # 2. Value at Risk (VaR) Hesaplamaları (95% veya 99%)
        alpha = 1 - confidence_level
        
        # A. Tarihsel (Historical) VaR
        historical_var = -np.percentile(port_daily_returns, alpha * 100)
        
        # B. Parametrik (Parametric) VaR (Gaussian)
        import scipy.stats as stats
        z_score = stats.norm.ppf(confidence_level)
        parametric_var = -(mean_daily_return - z_score * std_daily_return)
        
        # C. Monte Carlo VaR
        # Kovaryans matrisi
        cov_matrix = returns_df[symbols].cov().values
        mean_returns = returns_df[symbols].mean().values
        
        n_simulations = 5000
        # Çok değişkenli normal dağılımdan simülasyon getirisi üret
        sim_rets = np.random.multivariate_normal(mean_returns, cov_matrix, n_simulations)
        sim_port_rets = np.dot(sim_rets, w)
        monte_carlo_var = -np.percentile(sim_port_rets, alpha * 100)
        
        # 3. Expected Shortfall (ES) / Conditional VaR (CVaR)
        # Tarihsel VaR eşiğinin altındaki getirilerin ortalaması
        tail_returns = port_daily_returns[port_daily_returns <= -historical_var]
        expected_shortfall = -np.mean(tail_returns) if len(tail_returns) > 0 else historical_var
        
        return {
            "yillik_getiri": round(float(annualized_return), 4),
            "yillik_volatilite": round(float(annualized_volatility), 4),
            "sharpe": round(float(sharpe), 4),
            "sortino": round(float(sortino), 4),
            "max_drawdown": round(float(max_dd), 4),
            "calmar": round(float(calmar), 4),
            "var_tarihsel": round(float(historical_var), 4),
            "var_parametrik": round(float(parametric_var), 4),
            "var_monte_carlo": round(float(monte_carlo_var), 4),
            "expected_shortfall": round(float(expected_shortfall), 4),
            "guven_duzeyi": confidence_level
        }

    def calculate_structural_risks(
        self,
        weights: Dict[str, float],
        positions_metadata: List[Dict[str, Any]],
        base_currency: str = "TRY"
    ) -> Dict[str, Any]:
        """
        Konsantrasyon (HHI), Kur (Foreign Currency Exposure) ve
        Likidite (Largest position days to liquidate) risklerini hesaplar.
        """
        if not weights:
            return {}

        # 1. Konsantrasyon Riski (Herfindahl-Hirschman Index)
        w_values = np.array(list(weights.values()))
        # Ağırlıkların toplamının 1 olmasını garanti et
        w_norm = w_values / sum(w_values) if sum(w_values) > 0 else w_values
        hhi = float(np.sum(w_norm**2))
        
        # HHI Durum Belirleme (0.15 altı düşük, 0.25 üstü yüksek konsantrasyon)
        if hhi > 0.25:
            concentration_status = "HIGH_CONCENTRATION"
        elif hhi > 0.15:
            concentration_status = "MEDIUM_CONCENTRATION"
        else:
            concentration_status = "LOW_DIVERSIFIED"

        # 2. Kur Riski ve 3. Likidite Riski
        currency_risk_exposure = 0.0
        liquidity_risk_days = 0.0
        
        for pos in positions_metadata:
            symbol = pos.get("symbol")
            weight = weights.get(symbol, 0.0)
            
            # Kur Riski
            pos_curr = pos.get("currency", base_currency).upper()
            if pos_curr != base_currency.upper():
                currency_risk_exposure += weight
                
            # Likidite Riski (Günlük ortalama hacmin %10'u ile pozisyonu kaç günde eritebiliriz)
            avg_volume = float(pos.get("avg_daily_volume", 0.0))
            quantity = float(pos.get("quantity", 0.0))
            if avg_volume > 0 and quantity > 0:
                days = quantity / (0.10 * avg_volume)
                if days > liquidity_risk_days:
                    liquidity_risk_days = days
                    
        return {
            "hhi_concentration": round(hhi, 4),
            "concentration_status": concentration_status,
            "currency_risk_exposure": round(currency_risk_exposure, 4),
            "liquidity_risk_days": round(liquidity_risk_days, 2)
        }
