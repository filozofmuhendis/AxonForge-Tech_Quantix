import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from packages.common.models import Asset, PriceBar, Fundamental, MacroObservation, NewsArticle, Portfolio, PortfolioPosition
from packages.market_data.provider import YahooProvider
from packages.quant_engine.indicators import calculate_all_indicators
from packages.quant_engine.regime import MarketRegimeDetector
from packages.portfolio_engine.portfolio import PortfolioManager
from packages.portfolio_engine.optimization import PortfolioOptimizer
from packages.risk_engine.risk import RiskEngine
from packages.risk_engine.stress import StressTestEngine
from packages.signal_engine.signals import SignalEngine
from packages.signal_engine.analog_analysis import HistoricalAnalogAnalyzer
import pandas as pd

logger = logging.getLogger("axonforge.ai_agent.tools")

def get_asset_info(db: Session, symbol: str) -> Dict[str, Any]:
    """Varlık temel künye bilgilerini getirir."""
    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    if not asset:
        # Eğer DB'de yoksa yfinance ile bilgiyi çekip kaydetmeyi dene
        try:
            prov = YahooProvider()
            info = prov.fetch_fundamental_snapshot(symbol)
            if info:
                asset = Asset(
                    symbol=symbol,
                    name=symbol, # fallback
                    asset_class="EQUITY" if ".IS" in symbol or len(symbol) <= 5 else "FX",
                    exchange="BIST" if ".IS" in symbol else "US",
                    sector=info.get("sector", "Bilinmeyen"),
                    industry=info.get("industry", "Bilinmeyen"),
                    country=info.get("country", "US"),
                    currency="TRY" if ".IS" in symbol else "USD"
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
        except Exception:
            return {"hata": f"Varlık bulunamadı: {symbol}"}
            
    return {
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_class": asset.asset_class,
        "exchange": asset.exchange,
        "sector": asset.sector,
        "industry": asset.industry,
        "country": asset.country,
        "currency": asset.currency
    }

def get_historical_prices(db: Session, symbol: str, days: int = 252) -> List[Dict[str, Any]]:
    """Belirli bir sembol için geçmiş fiyat verilerini çeker."""
    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    if not asset:
        get_asset_info(db, symbol) # kayıt etmeyi dene
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        
    if not asset:
        return []
        
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    prices = db.query(PriceBar).filter(
        PriceBar.asset_id == asset.id,
        PriceBar.timestamp >= cutoff_date
    ).order_by(PriceBar.timestamp.asc()).all()
    
    if not prices:
        # DB'de veri yoksa YahooProvider ile çekip kaydet
        prov = YahooProvider()
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        bars = prov.fetch_daily_bars(symbol, start_date, end_date)
        
        for bar in bars:
            db_bar = PriceBar(
                asset_id=asset.id,
                timestamp=bar["timestamp"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
                adj_close=bar["adj_close"],
                provider_name=bar["provider_name"],
                fetched_at=bar["fetched_at"],
                latency_ms=bar["latency_ms"],
                freshness_seconds=bar["freshness_seconds"],
                data_quality_score=bar["data_quality_score"]
            )
            db.add(db_bar)
        db.commit()
        
        # Tekrar oku
        prices = db.query(PriceBar).filter(
            PriceBar.asset_id == asset.id,
            PriceBar.timestamp >= cutoff_date
        ).order_by(PriceBar.timestamp.asc()).all()
        
    return [{
        "timestamp": p.timestamp.strftime("%Y-%m-%d"),
        "open": p.open,
        "high": p.high,
        "low": p.low,
        "close": p.close,
        "volume": p.volume,
        "adj_close": p.adj_close,
        "quality_score": p.data_quality_score
    } for p in prices]

def calculate_technical_indicators(db: Session, symbol: str) -> Dict[str, Any]:
    """Bir hissenin tüm teknik indikatörlerini hesaplar."""
    prices = get_historical_prices(db, symbol, days=365)
    if not prices:
        return {"hata": "Fiyat verisi bulunamadı."}
        
    df = pd.DataFrame(prices)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df_indicators = calculate_all_indicators(df)
    latest = df_indicators.iloc[-1]
    
    return {
        "symbol": symbol,
        "timestamp": latest['timestamp'].strftime("%Y-%m-%d"),
        "close": latest['close'],
        "sma_20": latest['sma_20'],
        "sma_50": latest['sma_50'],
        "sma_200": latest['sma_200'],
        "rsi": latest['rsi'],
        "macd": latest['macd'],
        "macd_signal": latest['macd_signal'],
        "volatility": latest['volatility'],
        "atr": latest['atr'],
        "support": latest['support_20'],
        "resistance": latest['resistance_20']
    }

def get_current_market_regime(db: Session, symbol: str) -> Dict[str, Any]:
    """Seçilen varlık için anlık piyasa rejimini analiz eder."""
    prices = get_historical_prices(db, symbol, days=365)
    if not prices:
        return {"regime": "TRANSITION", "confidence": 0.50}
        
    df = pd.DataFrame(prices)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_ind = calculate_all_indicators(df)
    
    detector = MarketRegimeDetector()
    return detector.detect_current_regime(df_ind)

def get_portfolio_status(db: Session, portfolio_name: str = "Varsayılan") -> Dict[str, Any]:
    """Kullanıcının portföyündeki varlıkları, maliyetlerini ve güncel dağılımını analiz eder."""
    port = db.query(Portfolio).filter(Portfolio.name == portfolio_name).first()
    if not port:
        # Portföy yoksa oluştur
        port = Portfolio(name=portfolio_name, currency="TRY", cash=1000000.0)
        db.add(port)
        db.commit()
        db.refresh(port)
        
    positions_db = db.query(PortfolioPosition).filter(PortfolioPosition.portfolio_id == port.id).all()
    
    positions = []
    current_prices = {}
    
    # Her pozisyon için güncel fiyatı al
    for p in positions_db:
        # En son fiyat barını bul
        asset = db.query(Asset).filter(Asset.symbol == p.symbol).first()
        latest_price = p.cost_basis
        if asset:
            last_bar = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.timestamp.desc()).first()
            if last_bar:
                latest_price = last_bar.close
                
        current_prices[p.symbol] = latest_price
        
        positions.append({
            "symbol": p.symbol,
            "quantity": p.quantity,
            "cost_basis": p.cost_basis,
            "currency": p.currency,
            "sector": asset.sector if asset else "Genel",
            "country": asset.country if asset else "TR",
            "asset_class": asset.asset_class if asset else "EQUITY"
        })
        
    pm = PortfolioManager(port.id, base_currency="TRY")
    fx_rates = {"USDTRY": 33.20, "EURTRY": 35.80} # Örnek kurlar
    
    result = pm.calculate_position_details(positions, current_prices, fx_rates)
    result["nakit"] = port.cash
    result["portfoy_toplam_deger"] = round(result["total_value"] + port.cash, 2)
    
    return result

def run_stress_test_scenario(db: Session, shocks: Dict[str, float], portfolio_name: str = "Varsayılan") -> Dict[str, Any]:
    """Kullanıcının portföyüne stres testi senaryolarını uygular."""
    port_status = get_portfolio_status(db, portfolio_name)
    positions = port_status["positions"]
    
    # Pozisyon listesini formatla
    formatted_pos = []
    for pos in positions:
        formatted_pos.append({
            "symbol": pos["symbol"],
            "value_in_base": pos["value_in_base"],
            "currency": pos["currency"],
            "sector": pos["sector"],
            "country": pos["country"],
            "asset_class": pos["asset_class"]
        })
        
    # Basit örnek beta sözlüğü
    betas = {pos["symbol"]: 1.0 for pos in positions}
    
    ste = StressTestEngine()
    return ste.simulate_scenario(formatted_pos, betas, shocks, base_currency="TRY")

def generate_asset_trade_proposal(db: Session, symbol: str, portfolio_name: str = "Varsayılan") -> Dict[str, Any]:
    """Sinyal ve risk parametrelerini değerlendirerek bir işlem önerisi (Trade Proposal) oluşturur."""
    # 1. Teknik İndikatörleri Hesapla
    tech = calculate_technical_indicators(db, symbol)
    if "hata" in tech:
        return tech
        
    # 2. Piyasa Rejimini Al
    regime = get_current_market_regime(db, symbol)
    
    # 3. Portföy Bakiye Bilgilerini Al
    port = get_portfolio_status(db, portfolio_name)
    
    # Basit sinyal ve olasılık skorları simülasyonu (Gerçek ML prediction ile bağlanacak)
    se = SignalEngine()
    
    # Kompozit Sinyal Skoru Hesaplama
    # Burada basitleştirilmiş veri kalitesi ve analog değerler kullanılmıştır
    signal_res = se.calculate_composite_signal(
        symbol=symbol,
        technical_score=75.0 if tech["rsi"] < 70 else 45.0,
        momentum_score=80.0 if tech["macd"] > tech["macd_signal"] else 40.0,
        ml_probability=0.65, # Örnek ML tahmini
        fundamental_score=70.0,
        news_sentiment=0.2, # Olumlu haber akışı
        macro_score=60.0,
        market_regime=regime["regime"],
        data_quality_score=95.0,
        model_calibration=0.85,
        analog_similarity=0.78,
        regime_stability=regime["stability_score"],
        risk_confidence=0.80
    )
    
    # İşlem önerisi oluştur
    proposal = se.generate_trade_proposal(
        signal_result=signal_res,
        current_price=tech["close"],
        atr=tech["atr"],
        portfolio_value=port["portfoy_toplam_deger"]
    )
    
    if not proposal:
        return {
            "symbol": symbol,
            "sinyal": signal_res["signal_type"],
            "skor": signal_res["score"],
            "islem_onerisi": "YOK",
            "gerekce": f"Sinyal skoru ({signal_res['score']}) işleme girmek için yeterince güçlü değil ({signal_res['signal_type']})."
        }
        
    return {
        "symbol": symbol,
        "sinyal": signal_res["signal_type"],
        "skor": signal_res["score"],
        "islem_onerisi": "VAR",
        "teklif": proposal,
        "guven_ayrisimi": signal_res["confidence_breakdown"],
        "karar_izi": signal_res["decision_trace"]
    }

def get_asset_price(db: Session, symbol: str) -> float:
    """Belirtilen sembolün en güncel kapanış fiyatını döndürür."""
    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    if asset:
        last_bar = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.timestamp.desc()).first()
        if last_bar:
            return last_bar.close
    # Fallback to provider
    try:
        prov = YahooProvider()
        bars = prov.fetch_daily_bars(symbol, (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
        if bars:
            return bars[-1]["close"]
    except Exception:
        pass
    return 0.0

def get_fundamentals(db: Session, symbol: str) -> Dict[str, Any]:
    """Varlığın en güncel temel analiz rasyolarını döndürür."""
    f = db.query(Fundamental).filter(Fundamental.symbol == symbol).order_by(Fundamental.snapshot_date.desc()).first()
    return f.metrics if f else {}

def get_news(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """En son kaydedilmiş haber başlıklarını ve sentiment değerlerini getirir."""
    articles = db.query(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit).all()
    return [{
        "title": a.title,
        "source": a.source,
        "published_at": a.published_at.strftime("%Y-%m-%d %H:%M"),
        "sentiment": a.sentiment,
        "event_type": a.event_type
    } for a in articles]

def get_macro(db: Session, indicator_name: str) -> List[Dict[str, Any]]:
    """Makroekonomik indikatör gözlemlerini listeler."""
    obs = db.query(MacroObservation).filter(
        MacroObservation.indicator_name == indicator_name.upper()
    ).order_by(MacroObservation.timestamp.desc()).limit(10).all()
    return [{
        "timestamp": o.timestamp.strftime("%Y-%m-%d"),
        "value": o.value,
        "category": o.category
    } for o in obs]

def calculate_correlation(db: Session, symbol1: str, symbol2: str, days: int = 100) -> Dict[str, Any]:
    """İki varlığın günlük getirileri arasındaki korelasyonu hesaplar."""
    p1 = get_historical_prices(db, symbol1, days)
    p2 = get_historical_prices(db, symbol2, days)
    
    if not p1 or not p2:
        return {"korelasyon": 0.0, "mesaj": "Veri yetersiz."}
        
    df1 = pd.DataFrame(p1).set_index("timestamp")["close"].pct_change().dropna()
    df2 = pd.DataFrame(p2).set_index("timestamp")["close"].pct_change().dropna()
    
    df = pd.concat([df1, df2], axis=1).dropna()
    if df.empty:
        return {"korelasyon": 0.0, "mesaj": "Tarihsel hizalama başarısız."}
        
    corr = float(df.iloc[:, 0].corr(df.iloc[:, 1]))
    return {
        "symbol1": symbol1,
        "symbol2": symbol2,
        "gun_sayisi": len(df),
        "korelasyon": round(corr, 4)
    }

def run_backtest_tool(db: Session, symbol: str) -> Dict[str, Any]:
    """Belirtilen varlık üzerinde basit 10/20 SMA Crossover stratejisiyle backtest koşturur."""
    prices = get_historical_prices(db, symbol, days=365)
    if not prices:
        return {"basari": False, "hata": "Fiyat geçmişi yok."}
        
    df = pd.DataFrame(prices)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Teknik indikatörleri hesapla
    df_ind = calculate_all_indicators(df)
    df_ind.attrs["symbol"] = symbol
    
    from packages.backtest_engine.backtester import BacktestEngine
    
    # Basit SMA Crossover Sinyal Üreteci
    def sma_crossover_strategy(historical_data: pd.DataFrame, t: int) -> str:
        if t < 2:
            return "HOLD"
        row = historical_data.iloc[-1]
        prev_row = historical_data.iloc[-2]
        
        # SMA 20, SMA 50'yi yukarı keserse BUY, aşağı keserse SELL
        if prev_row['sma_20'] <= prev_row['sma_50'] and row['sma_20'] > row['sma_50']:
            return "BUY"
        elif prev_row['sma_20'] >= prev_row['sma_50'] and row['sma_20'] < row['sma_50']:
            return "SELL"
        return "HOLD"
        
    be = BacktestEngine()
    return be.run_backtest(df_ind, sma_crossover_strategy)

def optimize_portfolio_tool(db: Session, portfolio_name: str = "Varsayılan") -> Dict[str, Any]:
    """Portföy ağırlıklarını maksimum Sharpe oranı hedefiyle optimize eder."""
    port_status = get_portfolio_status(db, portfolio_name)
    positions = port_status["positions"]
    
    if len(positions) < 2:
        return {"hata": "Optimizasyon için portföyde en az 2 varlık olmalıdır."}
        
    symbols = [p["symbol"] for p in positions]
    
    # Getiri matrisini oluştur
    returns_dict = {}
    for sym in symbols:
        prices = get_historical_prices(db, sym, days=150)
        if prices:
            returns_dict[sym] = pd.DataFrame(prices).set_index("timestamp")["close"].pct_change().dropna()
            
    df_returns = pd.DataFrame(returns_dict).dropna()
    if df_returns.empty:
        return {"hata": "Tarihsel getiri verileri hizalanamadı."}
        
    opt = PortfolioOptimizer()
    weights_max_sharpe = opt.optimize_max_sharpe(symbols, df_returns, risk_free_rate=0.05)
    
    return {
        "portfolio": portfolio_name,
        "assets": symbols,
        "optimized_weights": {s: round(float(w), 4) for s, w in zip(symbols, weights_max_sharpe)}
    }

