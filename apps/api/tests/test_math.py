import pytest
import pandas as pd
import numpy as np
from packages.quant_engine.indicators import calculate_sma, calculate_rsi
from packages.risk_engine.risk import RiskEngine
from packages.feature_engine.features import FeatureGenerator

def test_sma_calculation():
    # Basit bir SMA kontrolü
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma_2 = calculate_sma(prices, 2)
    
    # 2 periyotlu SMA: [NaN, 15.0, 25.0, 35.0, 45.0]
    assert pd.isna(sma_2.iloc[0])
    assert sma_2.iloc[1] == 15.0
    assert sma_2.iloc[4] == 45.0

def test_rsi_calculation():
    # RSI sınır değerleri kontrolü (0 ile 100 arası olmalı)
    prices = pd.Series([10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0, 15.0, 14.0, 16.0, 15.0, 17.0, 16.0, 18.0, 17.0])
    rsi = calculate_rsi(prices, 5)
    
    assert len(rsi) == len(prices)
    assert rsi.min() >= 0.0
    assert rsi.max() <= 100.0

def test_var_risk_calculations():
    # Risk hesaplamaları doğrulama
    # 5 günlük getiri matrisi simülasyonu
    returns_data = {
        "THYAO": [0.01, -0.02, 0.005, 0.015, -0.01],
        "TUPRS": [0.005, 0.01, -0.015, 0.02, -0.005]
    }
    returns_df = pd.DataFrame(returns_data)
    
    weights = {"THYAO": 0.50, "TUPRS": 0.50}
    
    re = RiskEngine(risk_free_rate=0.05)
    metrics = re.calculate_risk_metrics(weights, returns_df, confidence_level=0.95)
    
    assert "var_tarihsel" in metrics
    assert "var_parametrik" in metrics
    assert "expected_shortfall" in metrics
    assert metrics["var_tarihsel"] > -1.0
    assert metrics["expected_shortfall"] >= metrics["var_tarihsel"]  # ES her zaman VaR'dan büyüktür

def test_data_leakage_protection():
    # Öznitelik etiket birleşiminde zaman sızıntısı kontrolü
    dates = pd.date_range(start="2026-08-01", periods=10, freq="D")
    df_prices = pd.DataFrame({
        "timestamp": dates,
        "close": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]
    })
    
    fg = FeatureGenerator(version="test_v1")
    # 2 gün sonrasını tahmin etmek istiyoruz (horizon=2)
    df_labeled, labels = fg.create_labels(df_prices, horizon=2, threshold=0.01)
    
    # Son 2 satırın silindiğinden emin ol (T+2 verisi sızmasın diye)
    assert len(df_labeled) == len(df_prices) - 2
    assert len(labels) == len(df_labeled)
    
    # Eğitim ve test bölünmesinin sızıntısız olduğunu doğrula (Zaman serisi sıralı bölme)
    X_train, X_test, y_train, y_test = fg.split_train_test_without_leakage(df_labeled, labels, train_ratio=0.8)
    
    # Test setindeki en erken tarih, train setindeki en geç tarihten sonra olmalıdır
    max_train_date = X_train['timestamp'].max()
    min_test_date = X_test['timestamp'].min()
    assert min_test_date > max_train_date

def test_new_technical_indicators():
    from packages.quant_engine.indicators import calculate_roc, calculate_stochastic, calculate_obv, calculate_volume_ratio
    
    close_prices = pd.Series([10.0, 11.0, 12.0, 11.0, 13.0, 14.0])
    volumes = pd.Series([1000, 1500, 2000, 1200, 1800, 2200])
    df = pd.DataFrame({
        "close": close_prices,
        "high": close_prices * 1.05,
        "low": close_prices * 0.95,
        "volume": volumes
    })
    
    # 1. ROC
    roc = calculate_roc(close_prices, 2)
    assert len(roc) == len(close_prices)
    
    # 2. Stochastic
    k, d = calculate_stochastic(df, 3, 2)
    assert len(k) == len(close_prices)
    assert len(d) == len(close_prices)
    
    # 3. OBV
    obv = calculate_obv(close_prices, volumes)
    assert len(obv) == len(close_prices)
    assert obv.iloc[1] > 0
    
    # 4. Volume Ratio
    vr = calculate_volume_ratio(volumes, 3)
    assert len(vr) == len(volumes)

