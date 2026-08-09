from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from packages.common.database import get_db
from packages.common.models import Asset, Portfolio, PortfolioPosition, Order, DecisionJournal, TradeProposal
from packages.ai_agent.agent import FinancialAIAgent
from packages.ai_agent.tools import (
    get_asset_info,
    get_historical_prices,
    calculate_technical_indicators,
    get_current_market_regime,
    get_portfolio_status,
    run_stress_test_scenario,
    generate_asset_trade_proposal
)
from packages.backtest_engine.backtester import BacktestEngine
from packages.portfolio_engine.optimization import PortfolioOptimizer
from packages.risk_engine.risk_gate import RiskGate
from packages.common.broker import PaperBroker
from packages.common.journal import JournalManager
import pandas as pd
from datetime import datetime, timezone

api_router = APIRouter()

# 1. Varlık Enformasyon Uç Noktaları (Assets & Prices)

@api_router.get("/assets", response_model=List[Dict[str, Any]])
def list_assets(db: Session = Depends(get_db)):
    """Sistemde kayıtlı olan tüm aktif finansal varlıkları listeler."""
    assets = db.query(Asset).filter(Asset.is_active == True).all()
    return [{
        "id": a.id,
        "symbol": a.symbol,
        "name": a.name,
        "asset_class": a.asset_class,
        "exchange": a.exchange,
        "country": a.country,
        "currency": a.currency
    } for a in assets]

@api_router.get("/prices/{symbol}")
def get_prices(symbol: str, days: int = Query(252, ge=10), db: Session = Depends(get_db)):
    """Belirli bir sembolün geçmiş bar verilerini döndürür."""
    prices = get_historical_prices(db, symbol, days)
    if not prices:
        raise HTTPException(status_code=404, detail=f"{symbol} için fiyat verisi bulunamadı.")
    return prices

@api_router.get("/indicators/{symbol}")
def get_indicators(symbol: str, db: Session = Depends(get_db)):
    """Bir hissenin tüm teknik indikatör istatistiklerini hesaplar."""
    tech = calculate_technical_indicators(db, symbol)
    if "hata" in tech:
        raise HTTPException(status_code=400, detail=tech["hata"])
    return tech

@api_router.get("/regime/{symbol}")
def get_regime(symbol: str, db: Session = Depends(get_db)):
    """Seçilen varlık için anlık piyasa rejimini analiz eder."""
    return get_current_market_regime(db, symbol)


# 2. Portföy ve Risk Yönetim Uç Noktaları (Portfolio & Risk)

@api_router.get("/portfolio")
def get_portfolio(name: str = "Varsayılan", db: Session = Depends(get_db)):
    """Kullanıcının portföy durumunu, açık pozisyonlarını ve maruziyetlerini getirir."""
    return get_portfolio_status(db, name)

@api_router.get("/risk")
def get_risk(portfolio_name: str = "Varsayılan", db: Session = Depends(get_db)):
    """Portföyün güncel Value-at-Risk (VaR) ve diğer risk rasyolarını hesaplar."""
    port_status = get_portfolio_status(db, portfolio_name)
    positions = port_status["positions"]
    
    if not positions:
        return {"mesaj": "Risk hesabı için portföyde en az bir pozisyon bulunmalıdır.", "total_value": port_status["portfoy_toplam_deger"]}
        
    weights = {}
    total_val = port_status["total_value"]
    for pos in positions:
        weights[pos["symbol"]] = pos["value_in_base"] / total_val
        
    # Getiri matrisini çek
    returns_dict = {}
    for pos in positions:
        prices = get_historical_prices(db, pos["symbol"], days=180)
        df_p = pd.DataFrame(prices)
        if not df_p.empty:
            returns_dict[pos["symbol"]] = df_p['close'].pct_change().fillna(0.0)
            
    returns_df = pd.DataFrame(returns_dict)
    
    from packages.risk_engine.risk import RiskEngine
    re = RiskEngine()
    risk_metrics = re.calculate_risk_metrics(weights, returns_df)
    
    return {
        "portfoy_toplam_deger": port_status["portfoy_toplam_deger"],
        "risk_metrikleri": risk_metrics
    }

@api_router.post("/stress-test")
def post_stress_test(shocks: Dict[str, float], portfolio_name: str = "Varsayılan", db: Session = Depends(get_db)):
    """Gelen makro şok senaryolarına göre stres testi simülasyonu çalıştırır."""
    return run_stress_test_scenario(db, shocks, portfolio_name)

@api_router.post("/portfolio/optimize")
def post_optimize_portfolio(symbols: List[str], method: str = "max_sharpe", db: Session = Depends(get_db)):
    """Verilen sembol listesi için portföy optimizasyonu çalıştırır."""
    if len(symbols) < 2:
        raise HTTPException(status_code=400, detail="Optimizasyon için en az iki sembol gereklidir.")
        
    # Getiri ve kovaryans matrisini hazırla
    returns_dict = {}
    for s in symbols:
        prices = get_historical_prices(db, s, days=252)
        df_p = pd.DataFrame(prices)
        if not df_p.empty:
            returns_dict[s] = df_p['close'].pct_change().fillna(0.0)
            
    returns_df = pd.DataFrame(returns_dict)
    cov_matrix = returns_df.cov()
    expected_returns = returns_df.mean() * 252
    
    opt = PortfolioOptimizer()
    
    if method == "min_variance":
        weights = opt.optimize_min_variance(symbols, cov_matrix)
    elif method == "risk_parity":
        weights = opt.optimize_risk_parity(symbols, cov_matrix)
    else:
        weights = opt.optimize_max_sharpe(symbols, expected_returns, cov_matrix)
        
    return {
        "optimizasyon_metodu": method,
        "ağırlıklar": weights
    }


# 3. Geriye Dönük Test Uç Noktaları (Backtesting)

@api_router.post("/backtest")
def post_run_backtest(symbol: str, strategy_name: str = "SMA_Crossover", initial_capital: float = 100000.0, db: Session = Depends(get_db)):
    """
    Belirli bir varlık üzerinde geriye dönük testi Celery asenkron kuyruğuna ekler ve bir job_id döner.
    """
    from workers.tasks import run_backtest_task
    params = {
        "initial_capital": initial_capital,
        "commission": 0.001,
        "slippage": 0.0005
    }
    task = run_backtest_task.delay(symbol, strategy_name, params)
    return {
        "job_id": task.id,
        "status": "QUEUED",
        "mesaj": f"{symbol} için geriye dönük test kuyruğa eklendi."
    }

@api_router.get("/backtest/status/{job_id}")
def get_backtest_status(job_id: str):
    """
    Kuyruktaki geriye dönük test görevinin durumunu sorgular.
    """
    from celery.result import AsyncResult
    from packages.common.celery_app import celery_app
    
    res = AsyncResult(job_id, app=celery_app)
    
    if res.state == "SUCCESS":
        return {
            "status": "SUCCESS",
            "result": res.result
        }
    elif res.state == "FAILURE":
        return {
            "status": "FAILED",
            "error": str(res.result)
        }
    elif res.state == "STARTED":
        return {
            "status": "RUNNING"
        }
    else:
        return {
            "status": "PENDING"
        }



# 4. Yapay Zeka Sohbet Ajanı (AI Agent Chat)

@api_router.post("/agent/chat")
def post_agent_chat(payload: Dict[str, str], db: Session = Depends(get_db)):
    """Yapay zeka ajanı ile sohbet uç noktası."""
    soru = payload.get("soru")
    if not soru:
        raise HTTPException(status_code=400, detail="Sorgu girilmelidir.")
        
    agent = FinancialAIAgent()
    return agent.run_query(db, soru)


# 5. Sanal İşlem ve Günlük Uç Noktaları (Orders & Decision Journal)

@api_router.post("/orders")
def post_submit_order(
    portfolio_name: str,
    symbol: str,
    side: str,  # BUY, SELL
    quantity: float,
    price: float,
    order_type: str = "MARKET",
    db: Session = Depends(get_db)
):
    """
    Emri alır, risk geçidinden (Risk Gate) geçirir ve onaylanırsa 
    paper broker üzerinden sanal portföye işler.
    """
    port = db.query(Portfolio).filter(Portfolio.name == portfolio_name).first()
    if not port:
        raise HTTPException(status_code=404, detail="Portföy bulunamadı.")
        
    pos = db.query(PortfolioPosition).filter(
        PortfolioPosition.portfolio_id == port.id,
        PortfolioPosition.symbol == symbol
    ).first()
    
    existing_qty = pos.quantity if pos else 0.0
    
    # Risk Gate Kontrolü
    rg = RiskGate()
    
    # En son bar zamanı
    market_price_time = datetime.now(timezone.utc)
    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    if asset:
        last_bar = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.timestamp.desc()).first()
        if last_bar:
            market_price_time = last_bar.timestamp
            
    passed, reason = rg.validate_order(
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        portfolio_value=port.cash + (existing_qty * price),
        cash=port.cash,
        existing_qty=existing_qty,
        daily_realized_loss=0.0,  # Örnek
        market_price_time=market_price_time,
        avg_daily_volume=1000000.0, # Örnek
        market_open=True
    )
    
    if not passed:
        return {"durum": "ENGELLENDI", "gerekce": reason}
        
    # Emir nesnesini veritabanına ekle
    db_order = Order(
        portfolio_id=port.id,
        symbol=symbol,
        type=order_type,
        side=side,
        status="SUBMITTED",
        quantity=quantity,
        price=price,
        created_at=datetime.utcnow()
    )
    db.add(db_order)
    db.commit()
    
    # PaperBroker ile eşleştir
    pb = PaperBroker()
    exec_res = pb.process_order_execution(
        order={"side": side, "type": order_type, "quantity": quantity, "price": price},
        current_price=price,
        cash=port.cash,
        existing_qty=existing_qty
    )
    
    if exec_res["status"] == "FILLED":
        db_order.status = "FILLED"
        # Bakiye ve pozisyon güncelleme
        port.cash += exec_res["cash_change"]
        
        if pos:
            pos.quantity += exec_res["qty_change"]
            if pos.quantity <= 0:
                db.delete(pos)
        else:
            if exec_res["qty_change"] > 0:
                new_pos = PortfolioPosition(
                    portfolio_id=port.id,
                    symbol=symbol,
                    quantity=exec_res["qty_change"],
                    cost_basis=price,
                    current_price=price,
                    currency="TRY" if ".IS" in symbol else "USD"
                )
                db.add(new_pos)
                
        db.commit()
        return {"durum": "GERCEKLESTI", "detay": exec_res}
        
    return {"durum": "REDDEDILDI", "gerekce": "Emir gerçekleştirilemedi."}

@api_router.get("/journal")
def get_journal(db: Session = Depends(get_db)):
    """Kullanıcının geçmiş işlem ve karar günlüğü kayıtlarını getirir."""
    jm = JournalManager()
    return jm.get_journal_history(db)

@api_router.post("/journal")
def post_journal_entry(
    proposal_id: int,
    thesis: str,
    reasoning: str,
    regime: str,
    db: Session = Depends(get_db)
):
    """Yeni bir işlem tezi ve karar günlüğü kaydı ekler."""
    jm = JournalManager()
    entry = jm.create_journal_entry(
        db=db,
        proposal_id=proposal_id,
        thesis_text=thesis,
        entry_reasoning=reasoning,
        regime_at_entry=regime,
        risk_metrics={"var_tarihsel": 0.02} # Örnek
    )
    return {"durum": "KAYDEDILDI", "id": entry.id}

@api_router.get("/system/status")
def get_system_status(db: Session = Depends(get_db)):
    """Tüm sistem bileşenlerinin, workerların ve harici sağlayıcıların durumunu Türkçe raporlar."""
    from packages.common.config import settings
    from packages.common.database import check_db_connection
    from packages.common.models import ModelRegistry, NewsArticle
    import redis
    
    # 1. API Status
    api_status = "ONLINE"
    
    # 2. Database Status
    db_status = "ONLINE"
    try:
        check_db_connection()
    except Exception:
        db_status = "OFFLINE"
        
    # 3. Redis Status
    redis_status = "ONLINE"
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1)
        r.ping()
    except Exception:
        redis_status = "OFFLINE"
        
    # 4. Celery Workers Status
    workers_status = "OFFLINE"
    try:
        from packages.common.celery_app import celery_app
        insp = celery_app.control.inspect(timeout=1.0)
        active_nodes = insp.active() if insp else None
        if active_nodes:
            workers_status = "ONLINE"
    except Exception:
        workers_status = "OFFLINE"
        
    # 5. Harici Veri Sağlayıcıları
    yahoo_status = "ONLINE"
    twelvedata_status = "ONLINE" if settings.TWELVEDATA_API_KEY else "NOT_CONFIGURED"
    finnhub_status = "ONLINE" if settings.FINNHUB_API_KEY else "NOT_CONFIGURED"
    fred_status = "ONLINE" if settings.FRED_API_KEY else "NOT_CONFIGURED"
    tcmb_status = "ONLINE" if settings.BIST_PROVIDER_API_KEY or settings.POLYGON_API_KEY else "NOT_CONFIGURED"
    
    # 6. ML & AI Status
    ai_status = "ONLINE"
    try:
        from packages.ai_agent.agent import FinancialAIAgent
        agent = FinancialAIAgent()
        agent.check_llm_health()
    except Exception:
        ai_status = "UNAVAILABLE"
        
    ml_status = "UNAVAILABLE"
    try:
        prod_models = db.query(ModelRegistry).filter(ModelRegistry.status == "PRODUCTION").all()
        if prod_models:
            ml_status = "ONLINE"
    except Exception:
        ml_status = "OFFLINE"
        
    # 7. Broker Mode
    broker_mode = "PAPER_TRADING"
    if settings.AUTO_TRADING:
        broker_mode = "REAL_TRADING_ACTIVE"
    if not settings.PAPER_TRADING and not settings.AUTO_TRADING:
        broker_mode = "DISABLED"
        
    # 8. News Sentiment Status
    news_status = "OFFLINE"
    try:
        articles_count = db.query(NewsArticle).count()
        if articles_count > 0:
            news_status = "ONLINE"
        else:
            news_status = "DEGRADED"
    except Exception:
        news_status = "OFFLINE"

    return {
        "api": api_status,
        "database": db_status,
        "redis": redis_status,
        "workers": workers_status,
        "ml_models": ml_status,
        "ai_agent": ai_status,
        "broker_mode": broker_mode,
        "news_feed": news_status,
        "providers": {
            "yahoo": yahoo_status,
            "twelvedata": twelvedata_status,
            "finnhub": finnhub_status,
            "fred": fred_status,
            "tcmb": tcmb_status
        }
    }


@api_router.post("/system/ingest/prices")
def trigger_price_ingestion():
    """Tüm aktif varlıklar için fiyat barlarını asenkron çekmeye başlar."""
    from workers.tasks import ingest_prices_task
    task = ingest_prices_task.delay()
    return {"job_id": task.id, "status": "QUEUED", "mesaj": "Fiyat çekme görevi kuyruğa eklendi."}


@api_router.post("/system/ingest/news")
def trigger_news_ingestion():
    """Haberleri ve yapay zeka sentiment analizini asenkron çekmeye başlar."""
    from workers.tasks import run_news_ingestion_task
    task = run_news_ingestion_task.delay()
    return {"job_id": task.id, "status": "QUEUED", "mesaj": "Haber çekme görevi kuyruğa eklendi."}


@api_router.post("/system/features")
def trigger_feature_generation():
    """Öznitelik matrislerini asenkron hesaplamaya başlar."""
    from workers.tasks import run_feature_generation_task
    task = run_feature_generation_task.delay()
    return {"job_id": task.id, "status": "QUEUED", "mesaj": "Öznitelik hesaplama görevi kuyruğa eklendi."}


@api_router.post("/system/predict")
def trigger_prediction_generation():
    """ML yön tahminlerini asenkron hesaplamaya başlar."""
    from workers.tasks import run_prediction_generation_task
    task = run_prediction_generation_task.delay()
    return {"job_id": task.id, "status": "QUEUED", "mesaj": "ML yön tahmini görevi kuyruğa eklendi."}


@api_router.post("/system/maintenance")
def trigger_maintenance():
    """Model kalibrasyonu ve işlem tez değerlendirmelerini asenkron güncellemeye başlar."""
    from workers.tasks import run_maintenance_task
    task = run_maintenance_task.delay()
    return {"job_id": task.id, "status": "QUEUED", "mesaj": "Bakım ve drift takibi görevi kuyruğa eklendi."}


