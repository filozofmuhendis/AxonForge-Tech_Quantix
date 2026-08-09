from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Table, Text, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from packages.common.database import Base

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # BIST, NASDAQ, NYSE, FX vb.
    timezone = Column(String(50), nullable=False)
    trading_hours = Column(JSONB, nullable=False)  # {"open": "09:30", "close": "18:00"}
    holidays = Column(JSONB, nullable=True)  # List of dates
    is_active = Column(Boolean, default=True)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_class = Column(String(50), nullable=False, index=True)  # EQUITY, ETF, INDEX, FX, COMMODITY, CRYPTO
    exchange = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True, index=True)
    industry = Column(String(100), nullable=True)
    country = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    prices = relationship("PriceBar", back_populates="asset", cascade="all, delete-orphan")
    intraday_prices = relationship("IntradayBar", back_populates="asset", cascade="all, delete-orphan")

class PriceBar(Base):
    __tablename__ = "price_bars"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=True)
    
    # Sağlayıcı ve Veri Kalitesi Metadatası
    provider_name = Column(String(50), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    latency_ms = Column(Integer, nullable=True)
    freshness_seconds = Column(Integer, nullable=True)
    data_quality_score = Column(Float, nullable=False)  # 0-100 aralığında
    
    asset = relationship("Asset", back_populates="prices")

class IntradayBar(Base):
    __tablename__ = "intraday_bars"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Sağlayıcı ve Veri Kalitesi Metadatası
    provider_name = Column(String(50), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    latency_ms = Column(Integer, nullable=True)
    freshness_seconds = Column(Integer, nullable=True)
    data_quality_score = Column(Float, nullable=False)
    
    asset = relationship("Asset", back_populates="intraday_prices")

class Fundamental(Base):
    __tablename__ = "fundamentals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    metrics = Column(JSONB, nullable=False)  # Gelir, Borç, F/K vb. içeren JSON
    sector_comparison = Column(JSONB, nullable=True)  # Sektörel karşılaştırma metrikleri
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class MacroObservation(Base):
    __tablename__ = "macro_observations"
    id = Column(Integer, primary_key=True, index=True)
    indicator_name = Column(String(100), nullable=False, index=True)  # CPI, Policy Rate, CDS vb.
    category = Column(String(50), nullable=False)  # TCMB, FED
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Float, nullable=False)
    provider_name = Column(String(50), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    data_quality_score = Column(Float, nullable=False)

class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)
    entities = Column(JSONB, nullable=True)  # İlgi şirketler/varlıklar
    event_type = Column(String(50), nullable=True, index=True)  # EARNINGS, M&A vb.
    sentiment = Column(Float, nullable=True)  # -1 ile +1 arası
    impact = Column(String(20), nullable=True)  # HIGH, MEDIUM, LOW
    data_quality_score = Column(Float, nullable=False)

class ModelRegistry(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    algorithm = Column(String(100), nullable=False)
    training_period = Column(JSONB, nullable=False)  # {"start": "...", "end": "..."}
    features = Column(JSONB, nullable=False)  # Liste
    dataset_version = Column(String(50), nullable=False)
    metrics = Column(JSONB, nullable=False)  # {"accuracy": ..., "brier_score": ...}
    status = Column(String(20), default="PRODUCTION")  # PRODUCTION, DEGRADED, RETIRED
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(100), ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    prediction_value = Column(Float, nullable=False)  # Yön veya getiri tahmini
    probability = Column(Float, nullable=True)  # Yön olasılığı (ör. return > threshold)
    confidence = Column(Float, nullable=True)
    horizon = Column(String(20), nullable=False)  # 5D, 20D vb.
    feature_version = Column(String(20), nullable=False)
    dataset_version = Column(String(50), nullable=False)
    calibration_score = Column(Float, nullable=True)  # Brier skoru vb.
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False, index=True)  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    score = Column(Float, nullable=False)  # Kompozit skor (0-100)
    components = Column(JSONB, nullable=False)  # Teknik, temel, ML ağırlıkları
    data_quality_score = Column(Float, nullable=False)
    market_regime_state = Column(String(50), nullable=False)
    analog_similarity = Column(Float, nullable=True)  # Eşleşen tarihlerin benzerlik skoru
    confidence_breakdown = Column(JSONB, nullable=False)  # Ayrıştırılmış güven skoru yapısı
    decision_trace = Column(JSONB, nullable=False)  # Data Lineage izleme günlüğü
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class TradeProposal(Base):
    __tablename__ = "trade_proposals"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id", ondelete="CASCADE"), nullable=True)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # BUY, SELL
    entry_zone = Column(JSONB, nullable=False)  # {"min": ..., "max": ...}
    stop_loss = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float, nullable=False)
    risk_gate_status = Column(String(50), nullable=False)  # PASSED, BLOCKED vb.
    position_size = Column(Float, nullable=False)
    risk_amount = Column(Float, nullable=False)
    holding_horizon = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    invalidation_conditions = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    journal_entry = relationship("DecisionJournal", uselist=False, back_populates="proposal")

class DecisionJournal(Base):
    __tablename__ = "decision_journal"
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("trade_proposals.id", ondelete="CASCADE"), nullable=False)
    thesis_text = Column(Text, nullable=False)  # Yatırım tezi
    entry_reasoning = Column(Text, nullable=False)  # Giriş gerekçesi
    exit_reasoning = Column(Text, nullable=True)  # Çıkış gerekçesi (işlem kapandığında doldurulur)
    regime_at_entry = Column(String(50), nullable=False)
    risk_metrics_at_entry = Column(JSONB, nullable=False)  # Giriş anındaki VaR vb. risk metrikleri
    actual_outcome_pnl = Column(Float, nullable=True)  # Gerçekleşen kar zarar
    post_trade_evaluation = Column(Text, nullable=True)  # İşlem kapandıktan sonra yapılan hata analizi (AI)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    proposal = relationship("TradeProposal", back_populates="journal_entry")

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    currency = Column(String(10), default="TRY")
    cash = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    positions = relationship("PortfolioPosition", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("PortfolioTransaction", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)  # Ortalama maliyet
    current_price = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="positions")

class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    type = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    fees = Column(Float, nullable=False)
    slippage = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    portfolio = relationship("Portfolio", back_populates="transactions")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # MARKET, LIMIT, STOP, STOP_LIMIT, BRACKET
    side = Column(String(10), nullable=False)  # BUY, SELL
    status = Column(String(20), default="CREATED")  # CREATED, SUBMITTED, FILLED, REJECTED
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Limit fiyatı
    stop_price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="orders")
    executions = relationship("Execution", back_populates="order", cascade="all, delete-orphan")

class Execution(Base):
    __tablename__ = "executions"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    fill_price = Column(Float, nullable=False)
    commission = Column(Float, nullable=False)
    slippage = Column(Float, nullable=False)
    execution_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    order = relationship("Order", back_populates="executions")

class Backtest(Base):
    __tablename__ = "backtests"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False)
    benchmark_symbol = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    runs = relationship("BacktestRun", back_populates="backtest", cascade="all, delete-orphan")

class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    cagr = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=False)
    sharpe = Column(Float, nullable=False)
    sortino = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    trades_count = Column(Integer, nullable=False)
    walk_forward_step = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    backtest = relationship("Backtest", back_populates="runs")
    trades = relationship("BacktestTrade", back_populates="run", cascade="all, delete-orphan")

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    pnl = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    
    run = relationship("BacktestRun", back_populates="trades")

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan")

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    decision_trace_id = Column(Integer, nullable=True)  # İsteğe bağlı olarak ilgili Sinyal izine bağlanabilir
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    session = relationship("AgentSession", back_populates="messages")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    actor = Column(String(100), nullable=False)  # SYSTEM, USER
    action = Column(String(100), nullable=False)  # ML_PREDICTION, SIGNAL_CHANGE, TRADE_SUBMISSION
    input_params = Column(JSONB, nullable=True)
    output_params = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False)  # SUCCESS, FAIL
