import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional

def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()

def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def calculate_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).copy()
    loss = (-delta.where(delta < 0, 0)).copy()
    
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    for i in range(window, len(series)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window - 1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window - 1) + loss.iloc[i]) / window
        
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    sma = calculate_sma(series, window)
    rstd = series.rolling(window=window).std()
    upper_band = sma + (rstd * num_std)
    lower_band = sma - (rstd * num_std)
    bandwidth = (upper_band - lower_band) / sma
    return upper_band, lower_band, sma, bandwidth

def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr.fillna(method='bfill')

def calculate_rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    return returns.rolling(window=window).std() * np.sqrt(252)

def calculate_beta_and_correlation(asset_returns: pd.Series, benchmark_returns: pd.Series, window: int = 60) -> Tuple[pd.Series, pd.Series]:
    df = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    df.columns = ['asset', 'benchmark']
    
    rolling_cov = df['asset'].rolling(window=window).cov(df['benchmark'])
    rolling_var = df['benchmark'].rolling(window=window).var()
    rolling_corr = df['asset'].rolling(window=window).corr(df['benchmark'])
    
    beta = rolling_cov / rolling_var
    return beta.reindex(asset_returns.index).fillna(1.0), rolling_corr.reindex(asset_returns.index).fillna(0.0)

def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Tuple[pd.Series, pd.Series]:
    resistance = df['high'].rolling(window=window).max()
    support = df['low'].rolling(window=window).min()
    return support.fillna(method='bfill'), resistance.fillna(method='bfill')

def calculate_roc(series: pd.Series, window: int = 12) -> pd.Series:
    """Rate of Change (Değişim Oranı) hesaplar."""
    shifted = series.shift(window)
    roc = ((series - shifted) / shifted.replace(0, np.nan)) * 100
    return roc.fillna(0.0)

def calculate_stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator (%K ve %D) hesaplar."""
    low_min = df['low'].rolling(window=k_window).min()
    high_max = df['high'].rolling(window=k_window).max()
    k_line = 100 * ((df['close'] - low_min) / (high_max - low_min).replace(0, np.nan))
    d_line = k_line.rolling(window=d_window).mean()
    return k_line.fillna(50.0), d_line.fillna(50.0)

def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume (Hacim Dengesi) hesaplar (Vektörize)."""
    diff = close.diff()
    direction = np.sign(diff).fillna(0.0)
    obv = (direction * volume).cumsum()
    return obv

def calculate_volume_ratio(volume: pd.Series, window: int = 20) -> pd.Series:
    """Mevcut hacmin 20 günlük hareketli ortalama hacme oranını hesaplar."""
    avg_vol = volume.rolling(window=window).mean()
    vr = volume / avg_vol.replace(0, np.nan)
    return vr.fillna(1.0)

def calculate_all_indicators(df_raw: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Verilen DataFrame üzerinde tüm quant indikatörlerini hesaplayıp yeni kolonlar ekler."""
    df = df_raw.copy().sort_values('timestamp')
    
    # Getiri (returns) hesabı
    df['returns'] = df['close'].pct_change().fillna(0.0)
    
    # Trend
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['sma_50'] = calculate_sma(df['close'], 50)
    df['sma_200'] = calculate_sma(df['close'], 200)
    df['ema_12'] = calculate_ema(df['close'], 12)
    df['ema_26'] = calculate_ema(df['close'], 26)
    
    # Momentum & Hacim
    df['rsi'] = calculate_rsi(df['close'], 14)
    macd_line, signal_line, hist = calculate_macd(df['close'])
    df['macd'] = macd_line
    df['macd_signal'] = signal_line
    df['macd_hist'] = hist
    
    df['roc'] = calculate_roc(df['close'], 12)
    k_line, d_line = calculate_stochastic(df, 14, 3)
    df['stoch_k'] = k_line
    df['stoch_d'] = d_line
    df['obv'] = calculate_obv(df['close'], df['volume'])
    df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)
    
    # Volatilite
    upper, lower, mid, width = calculate_bollinger_bands(df['close'])
    df['bb_upper'] = upper
    df['bb_lower'] = lower
    df['bb_middle'] = mid
    df['bb_width'] = width
    df['atr'] = calculate_atr(df, 14)
    df['volatility'] = calculate_rolling_volatility(df['returns'], 20)
    
    # Destek & Direnç
    sup, res = calculate_support_resistance(df, 20)
    df['support_20'] = sup
    df['resistance_20'] = res
    
    # Benchmark İlişkileri
    if benchmark_df is not None:
        bench_df = benchmark_df.copy().sort_values('timestamp')
        bench_df['bench_returns'] = bench_df['close'].pct_change().fillna(0.0)
        
        asset_rets = df.set_index('timestamp')['returns']
        bench_rets = bench_df.set_index('timestamp')['bench_returns']
        
        beta, corr = calculate_beta_and_correlation(asset_rets, bench_rets)
        
        df['beta'] = df['timestamp'].map(beta)
        df['correlation'] = df['timestamp'].map(corr)
    else:
        df['beta'] = 1.0
        df['correlation'] = 1.0
        
    return df.ffill().bfill()
