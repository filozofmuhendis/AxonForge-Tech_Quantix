import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Any, Tuple

class PortfolioOptimizer:
    """Portföy ağırlıklarını optimize eden matematiksel motor."""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.rf = risk_free_rate

    def optimize_equal_weight(self, symbols: List[str]) -> Dict[str, float]:
        """Tüm varlıklara eşit ağırlık verir."""
        n = len(symbols)
        if n == 0:
            return {}
        w = 1.0 / n
        return {s: round(w, 4) for s in symbols}

    def optimize_min_variance(
        self,
        symbols: List[str],
        cov_matrix: pd.DataFrame,
        bounds: Tuple[float, float] = (0.0, 0.30)
    ) -> Dict[str, float]:
        """Portföy varyansını (volatilitesini) minimize eder."""
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}
            
        Sigma = cov_matrix.loc[symbols, symbols].values
        
        # Amaç fonksiyonu: w^T * Sigma * w
        def obj_func(w):
            return np.dot(w.T, np.dot(Sigma, w))
            
        # Başlangıç tahminleri (eşit dağılım)
        init_weights = np.ones(n) / n
        
        # Kısıtlar: Ağırlıklar toplamı 1.0 olmalı
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        
        # Sınırlar: Her pozisyon için min/max limit
        item_bounds = [bounds for _ in range(n)]
        
        res = minimize(obj_func, init_weights, method='SLSQP', bounds=item_bounds, constraints=constraints)
        
        if not res.success:
            # Başarısız olursa Equal Weight dön
            return self.optimize_equal_weight(symbols)
            
        return {symbols[i]: round(float(res.x[i]), 4) for i in range(n)}

    def optimize_max_sharpe(
        self,
        symbols: List[str],
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        bounds: Tuple[float, float] = (0.0, 0.30)
    ) -> Dict[str, float]:
        """Portföy Sharpe oranını maksimize eder (Negatif Sharpe'ı minimize eder)."""
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}
            
        mu = expected_returns.loc[symbols].values
        Sigma = cov_matrix.loc[symbols, symbols].values
        
        # Amaç fonksiyonu: - ( Sharpe Oranı )
        def obj_func(w):
            port_return = np.dot(w, mu)
            port_vol = np.sqrt(np.dot(w.T, np.dot(Sigma, w)))
            if port_vol == 0:
                return 0.0
            return - (port_return - self.rf) / port_vol
            
        init_weights = np.ones(n) / n
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        item_bounds = [bounds for _ in range(n)]
        
        res = minimize(obj_func, init_weights, method='SLSQP', bounds=item_bounds, constraints=constraints)
        
        if not res.success:
            return self.optimize_equal_weight(symbols)
            
        return {symbols[i]: round(float(res.x[i]), 4) for i in range(n)}

    def optimize_risk_parity(
        self,
        symbols: List[str],
        cov_matrix: pd.DataFrame,
        bounds: Tuple[float, float] = (0.0, 0.30)
    ) -> Dict[str, float]:
        """Her varlığın portföy riskine (volatilitesine) katkısını eşitlemeye çalışır."""
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}
            
        Sigma = cov_matrix.loc[symbols, symbols].values
        
        # Hedef risk katkı oranı (eşit dağılım)
        target_risk_contrib = np.ones(n) / n
        
        # Amaç fonksiyonu: Katkılar ile Hedef arasındaki karesel farkların toplamı
        def obj_func(w):
            port_variance = np.dot(w.T, np.dot(Sigma, w))
            if port_variance <= 0:
                return 9999.0
            port_vol = np.sqrt(port_variance)
            
            # Marjinal Risk Katkısı
            marginal_contrib = np.dot(Sigma, w) / port_vol
            # Risk Katkısı (w * MRC)
            risk_contrib = w * marginal_contrib
            # Yüzdesel Risk Katkısı
            pct_risk_contrib = risk_contrib / port_vol
            
            # Hata toplamı
            return np.sum((pct_risk_contrib - target_risk_contrib) ** 2)
            
        init_weights = np.ones(n) / n
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        item_bounds = [bounds for _ in range(n)]
        
        res = minimize(obj_func, init_weights, method='SLSQP', bounds=item_bounds, constraints=constraints)
        
        if not res.success:
            return self.optimize_equal_weight(symbols)
            
        # Ağırlıkların normalize edildiğinden emin ol
        weights = res.x / np.sum(res.x)
        return {symbols[i]: round(float(weights[i]), 4) for i in range(n)}
