import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from packages.common.celery_app import celery_app
from packages.common.database import SessionLocal
from packages.common.models import Asset, PriceBar, Backtest, BacktestRun, BacktestTrade
from packages.market_data.provider import ProviderRouter
from packages.backtest_engine.backtester import BacktestEngine

logger = logging.getLogger("axonforge.workers.tasks")

def _ingest_single_asset_prices(db, router, symbol: str, days: int) -> Dict[str, Any]:
    try:
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        if not asset:
            return {"status": "FAILED", "symbol": symbol, "error": "Varlık bulunamadı."}
            
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        bars = router.fetch_daily_bars(symbol, start_date, end_date)
        if not bars:
            return {"status": "FAILED", "symbol": symbol, "error": "Fiyat verisi alınamadı."}
            
        from packages.data_quality.quality import calculate_data_quality_score
        quality_res = calculate_data_quality_score(bars)
        
        added_count = 0
        for bar in bars:
            existing = db.query(PriceBar).filter(
                PriceBar.asset_id == asset.id,
                PriceBar.timestamp == bar["timestamp"]
            ).first()
            
            if not existing:
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
                    fetched_at=datetime.now(timezone.utc),
                    latency_ms=bar["latency_ms"],
                    freshness_seconds=bar["freshness_seconds"],
                    data_quality_score=quality_res["score"]
                )
                db.add(db_bar)
                added_count += 1
                
        db.commit()
        return {
            "status": "SUCCESS",
            "symbol": symbol,
            "added_bars": added_count,
            "data_quality_score": quality_res["score"]
        }
    except Exception as e:
        logger.error(f"Fiyat indirme hatası ({symbol}): {str(e)}")
        db.rollback()
        return {"status": "FAILED", "symbol": symbol, "error": str(e)}


@celery_app.task(name="workers.tasks.ingest_prices_task")
def ingest_prices_task(symbol: str = None, days: int = 365) -> Dict[str, Any]:
    """Seçilen sembol (veya None ise tüm aktif semboller) için fiyat verilerini indirir ve kaydeder."""
    db = SessionLocal()
    router = ProviderRouter()
    try:
        if symbol is None:
            assets = db.query(Asset).filter(Asset.is_active == True).all()
            logger.info(f"Tüm aktif varlıklar için asenkron fiyat indirme başlatıldı: {len(assets)} sembol")
            results = []
            for asset in assets:
                res = _ingest_single_asset_prices(db, router, asset.symbol, days)
                results.append(res)
            return {"status": "SUCCESS", "processed_assets": len(results), "details": results}
        else:
            res = _ingest_single_asset_prices(db, router, symbol, days)
            return res
    finally:
        db.close()



@celery_app.task(name="workers.tasks.run_backtest_task")
def run_backtest_task(symbol: str, strategy_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Ağır portföy strateji testlerini (backtesting) asenkron olarak çalıştırır."""
    logger.info(f"Asenkron Geriye Dönük Test Başlatıldı: {symbol} - {strategy_name}")
    db = SessionLocal()
    
    try:
        # Fiyat geçmişini çek
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        if not asset:
            return {"status": "FAILED", "error": "Varlık bulunamadı."}
            
        prices = db.query(PriceBar).filter(PriceBar.asset_id == asset.id).order_by(PriceBar.timestamp.asc()).all()
        if len(prices) < 50:
            return {"status": "FAILED", "error": f"Backtest için yetersiz fiyat barı: {len(prices)}/50"}
            
        import pandas as pd
        df_prices = pd.DataFrame([{
            "timestamp": p.timestamp,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
            "returns": p.close / p.open - 1.0
        } for p in prices])
        
        # Teknik indikatörleri hesapla
        from packages.quant_engine.indicators import calculate_all_indicators
        df_ind = calculate_all_indicators(df_prices)
        df_ind.attrs["symbol"] = symbol
        
        # Basit 10/20 SMA Crossover Strateji Mantığı
        def sma_crossover_strategy(historical_data: pd.DataFrame, t: int) -> str:
            if t < 2:
                return "HOLD"
            row = historical_data.iloc[-1]
            prev_row = historical_data.iloc[-2]
            if prev_row['sma_20'] <= prev_row['sma_50'] and row['sma_20'] > row['sma_50']:
                return "BUY"
            elif prev_row['sma_20'] >= prev_row['sma_50'] and row['sma_20'] < row['sma_50']:
                return "SELL"
            return "HOLD"
            
        be = BacktestEngine(
            initial_capital=parameters.get("initial_capital", 100000.0),
            commission=parameters.get("commission", 0.001),
            slippage=parameters.get("slippage", 0.0005)
        )
        
        res = be.run_backtest(df_ind, sma_crossover_strategy)
        if not res.get("basari", False):
            return {"status": "FAILED", "error": res.get("hata", "Bilinmeyen Hata")}
            
        # 3. Sonuçları kalıcı olarak Supabase veritabanına kaydet
        db_backtest = Backtest(
            name=f"{symbol} Crossover Stratejisi",
            strategy_name=strategy_name,
            parameters=parameters,
            benchmark_symbol="XU100.IS" if ".IS" in symbol else "SPY"
        )
        db.add(db_backtest)
        db.commit()
        db.refresh(db_backtest)
        
        db_run = BacktestRun(
            backtest_id=db_backtest.id,
            start_date=df_ind['timestamp'].iloc[0],
            end_date=df_ind['timestamp'].iloc[-1],
            cagr=res["cagr"],
            max_drawdown=res["max_drawdown"],
            sharpe=res["sharpe"],
            sortino=res["sortino"],
            win_rate=res["win_rate"],
            total_return=res["total_return"],
            trades_count=res["trades_count"]
        )
        db.add(db_run)
        db.commit()
        db.refresh(db_run)
        
        # İşlemleri kaydet
        for trade in res["trades"]:
            db_trade = BacktestTrade(
                run_id=db_run.id,
                symbol=symbol,
                direction=trade["direction"],
                entry_time=trade["entry_time"] if isinstance(trade["entry_time"], datetime) else datetime.fromisoformat(str(trade["entry_time"])),
                exit_time=trade["exit_time"] if isinstance(trade["exit_time"], datetime) else datetime.fromisoformat(str(trade["exit_time"])),
                entry_price=trade["entry_price"],
                exit_price=trade["exit_price"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                duration_days=trade["duration_days"]
            )
            db.add(db_trade)
            
        db.commit()
        logger.info(f"Geriye dönük test asenkron kaydı tamamlandı (Run ID: {db_run.id})")
        
        return {
            "status": "SUCCESS",
            "backtest_id": db_backtest.id,
            "run_id": db_run.id,
            "cagr": res["cagr"],
            "max_drawdown": res["max_drawdown"],
            "sharpe": res["sharpe"],
            "win_rate": res["win_rate"],
            "total_return": res["total_return"]
        }
        
    except Exception as e:
        logger.error(f"Backtest asenkron görevi hatası: {str(e)}")
        db.rollback()
        return {"status": "FAILED", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="workers.tasks.run_feature_generation_task")
def run_feature_generation_task(version: str = "v1.0") -> Dict[str, Any]:
    """Tüm aktif varlıklar için ML öznitelik matrislerini asenkron üretir."""
    from workers.feature_worker import run_feature_worker
    try:
        run_feature_worker(version)
        return {"status": "SUCCESS", "message": "Öznitelik üretimi başarıyla tamamlandı."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


@celery_app.task(name="workers.tasks.run_prediction_generation_task")
def run_prediction_generation_task() -> Dict[str, Any]:
    """PRODUCTION'daki ML modelleri ile yön tahminlerini asenkron hesaplar."""
    from workers.prediction_worker import run_prediction_worker
    try:
        run_prediction_worker()
        return {"status": "SUCCESS", "message": "ML tahminleri başarıyla güncellendi."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


@celery_app.task(name="workers.tasks.run_news_ingestion_task")
def run_news_ingestion_task() -> Dict[str, Any]:
    """Haber akışlarını asenkron olarak çeker, NLP sentiment analizi yapar ve kaydeder."""
    from workers.news_worker import run_news_worker
    try:
        run_news_worker()
        return {"status": "SUCCESS", "message": "Finansal haber taraması başarıyla tamamlandı."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}


@celery_app.task(name="workers.tasks.run_maintenance_task")
def run_maintenance_task() -> Dict[str, Any]:
    """Model kalibrasyon skorlarını ve retrospektif P&L tezlerini asenkron günceller."""
    from workers.maintenance_worker import run_maintenance_worker
    try:
        run_maintenance_worker()
        return {"status": "SUCCESS", "message": "Model kalibrasyonu ve işlem tez değerlendirmeleri güncellendi."}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

