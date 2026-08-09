import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable, Tuple
import logging

logger = logging.getLogger("axonforge.backtester")

class BacktestEngine:
    """Look-ahead bias, sızıntı ve seans farklarına karşı dayanıklı olay güdümlü (event-driven) geriye dönük test motoru."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission: float = 0.001,       # Binde 1 komisyon
        slippage: float = 0.0005,         # On binde 5 slippage
        liquidity_cap_pct: float = 0.10   # Bar hacminin en fazla %10'u kadar işlem yapılabilir
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.liquidity_cap = liquidity_cap_pct

    def run_backtest(
        self,
        df_prices: pd.DataFrame,          # 'timestamp', 'open', 'high', 'low', 'close', 'volume' kolonlarını içerir
        signal_generator: Callable[[pd.DataFrame, int], str],  # df ve anlık indeks (t) alıp sinyal döner: BUY, SELL, HOLD
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.15
    ) -> Dict[str, Any]:
        """
        Geçmişe ait barları adım adım (event-driven loop) tarayarak simülasyonu çalıştırır.
        Sinyal üretimi strictly 'T' anına kadar olan veriyle kısıtlıdır, look-ahead bias engellenir.
        """
        df = df_prices.copy().sort_values('timestamp').reset_index(drop=True)
        n_rows = len(df)
        
        if n_rows < 20:
            return {"basari": False, "hata": "Test için yetersiz fiyat geçmişi."}
            
        capital = self.initial_capital
        position_qty = 0.0
        position_cost = 0.0
        trades = []
        portfolio_values = []
        dates = []
        
        active_trade = None # Açık işlem takibi
        
        for t in range(10, n_rows):  # İlk 10 barı warmup (ısınma) için ayır
            row = df.iloc[t]
            bar_date = row['timestamp']
            curr_open = row['open']
            curr_high = row['high']
            curr_low = row['low']
            curr_close = row['close']
            curr_volume = row['volume']
            
            # Gün başı portföy değerleme
            current_portfolio_value = capital + (position_qty * curr_close)
            portfolio_values.append(current_portfolio_value)
            dates.append(bar_date)
            
            # 1. Açık İşlem Varsa Stop Loss veya Take Profit Tetiklendi mi Kontrolü (Bar İçi Çıkış)
            if position_qty > 0 and active_trade:
                sl_triggered = False
                tp_triggered = False
                exit_price_actual = 0.0
                
                # Stop loss kontrolü
                if curr_low <= active_trade["stop_loss"]:
                    sl_triggered = True
                    exit_price_actual = active_trade["stop_loss"]
                # Take profit kontrolü
                elif curr_high >= active_trade["target_price"]:
                    tp_triggered = True
                    exit_price_actual = active_trade["target_price"]
                    
                if sl_triggered or tp_triggered:
                    # Çıkış işlemi ve masraf kesintileri
                    slippage_val = exit_price_actual * self.slippage
                    exit_price_final = exit_price_actual - slippage_val
                    
                    value = position_qty * exit_price_final
                    comm_cost = value * self.commission
                    
                    capital += (value - comm_cost)
                    pnl = value - comm_cost - position_cost
                    pnl_pct = (pnl / position_cost) if position_cost > 0 else 0.0
                    
                    trades.append({
                        "symbol": df.attrs.get("symbol", "ASSET"),
                        "direction": "BUY",
                        "entry_time": active_trade["entry_time"],
                        "exit_time": bar_date,
                        "entry_price": round(active_trade["entry_price"], 2),
                        "exit_price": round(exit_price_final, 2),
                        "quantity": round(position_qty, 2),
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct * 100, 2),
                        "duration_days": (bar_date - active_trade["entry_time"]).days,
                        "exit_reason": "STOP_LOSS" if sl_triggered else "TAKE_PROFIT"
                    })
                    
                    position_qty = 0.0
                    position_cost = 0.0
                    active_trade = None
                    continue
            
            # 2. Sinyal Alımı (Look-Ahead Bias engelleme)
            historical_slice = df.iloc[:t+1]
            signal = signal_generator(historical_slice, t)
            
            # 3. Emir Yönetimi
            if signal == "BUY" and position_qty == 0:
                max_qty_by_liquidity = curr_volume * self.liquidity_cap
                proposed_qty = capital / curr_open
                
                qty_to_buy = min(proposed_qty, max_qty_by_liquidity)
                if qty_to_buy <= 0:
                    continue
                    
                # Slippage
                slippage_val = curr_open * self.slippage
                fill_price = curr_open + slippage_val
                
                value = qty_to_buy * fill_price
                comm_cost = value * self.commission
                
                if (value + comm_cost) <= capital:
                    capital -= (value + comm_cost)
                    position_qty = qty_to_buy
                    position_cost = value + comm_cost
                    
                    active_trade = {
                        "entry_time": bar_date,
                        "entry_price": fill_price,
                        "stop_loss": fill_price * (1.0 - stop_loss_pct),
                        "target_price": fill_price * (1.0 + take_profit_pct)
                    }
                    
            elif signal == "SELL" and position_qty > 0:
                slippage_val = curr_close * self.slippage
                fill_price = curr_close - slippage_val
                
                value = position_qty * fill_price
                comm_cost = value * self.commission
                
                capital += (value - comm_cost)
                pnl = value - comm_cost - position_cost
                pnl_pct = (pnl / position_cost) if position_cost > 0 else 0.0
                
                trades.append({
                    "symbol": df.attrs.get("symbol", "ASSET"),
                    "direction": "BUY",
                    "entry_time": active_trade["entry_time"],
                    "exit_time": bar_date,
                    "entry_price": round(active_trade["entry_price"], 2),
                    "exit_price": round(fill_price, 2),
                    "quantity": round(position_qty, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct * 100, 2),
                    "duration_days": (bar_date - active_trade["entry_time"]).days,
                    "exit_reason": "SIGNAL_EXIT"
                })
                
                position_qty = 0.0
                position_cost = 0.0
                active_trade = None
                
        # Açık pozisyonu en son barda zorunlu kapat
        if position_qty > 0 and active_trade and n_rows > 0:
            final_row = df.iloc[-1]
            fill_price = final_row['close']
            value = position_qty * fill_price
            comm_cost = value * self.commission
            capital += (value - comm_cost)
            pnl = value - comm_cost - position_cost
            pnl_pct = (pnl / position_cost) if position_cost > 0 else 0.0
            
            trades.append({
                "symbol": df.attrs.get("symbol", "ASSET"),
                "direction": "BUY",
                "entry_time": active_trade["entry_time"],
                "exit_time": final_row['timestamp'],
                "entry_price": round(active_trade["entry_price"], 2),
                "exit_price": round(fill_price, 2),
                "quantity": round(position_qty, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct * 100, 2),
                "duration_days": (final_row['timestamp'] - active_trade["entry_time"]).days,
                "exit_reason": "BACKTEST_END_FORCE_CLOSE"
            })
            
        # 4. Geriye Dönük Test Metriklerinin Hesaplanması
        portfolio_series = pd.Series(portfolio_values)
        if portfolio_series.empty:
            return {"basari": False, "hata": "Test boyunca portföy değerlemesi yapılamadı."}
            
        total_return = (portfolio_series.iloc[-1] - self.initial_capital) / self.initial_capital
        
        # CAGR
        years = len(portfolio_series) / 252.0 if len(portfolio_series) > 0 else 1.0
        cagr = ((portfolio_series.iloc[-1] / self.initial_capital) ** (1.0 / years)) - 1.0 if years > 0 else total_return
        
        # Günlük Getiriler, Sharpe & Sortino
        daily_returns = portfolio_series.pct_change().dropna()
        sharpe = 0.0
        sortino = 0.0
        if not daily_returns.empty and daily_returns.std() > 0:
            sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))
            downside_rets = daily_returns[daily_returns < 0]
            if not downside_rets.empty and downside_rets.std() > 0:
                sortino = float((daily_returns.mean() / downside_rets.std()) * np.sqrt(252))
                
        # Drawdown & Calmar
        rolling_max = portfolio_series.cummax()
        drawdowns = (portfolio_series - rolling_max) / rolling_max
        max_dd = abs(float(drawdowns.min()))
        calmar = cagr / max_dd if max_dd > 0 else 0.0
        
        # Kazanma oranı (Win rate), Profit Factor & Expectancy
        winning_trades = [t["pnl"] for t in trades if t["pnl"] > 0]
        losing_trades = [abs(t["pnl"]) for t in trades if t["pnl"] < 0]
        
        wins = len(winning_trades)
        win_rate = (wins / len(trades)) if len(trades) > 0 else 0.0
        
        gross_profits = sum(winning_trades)
        gross_losses = sum(losing_trades)
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
        
        avg_win = sum(winning_trades) / wins if wins > 0 else 0.0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0.0
        expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
        
        # Portföy Devir Hızı (Turnover)
        total_traded_value = sum(t["entry_price"] * t["quantity"] for t in trades)
        turnover = total_traded_value / self.initial_capital
        
        return {
            "basari": True,
            "cagr": round(cagr, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "calmar": round(calmar, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "expectancy": round(expectancy, 2),
            "turnover": round(turnover, 4),
            "total_return": round(total_return, 4),
            "trades_count": len(trades),
            "trades": trades,
            "portfolio_values": portfolio_values,
            "dates": [d.strftime("%Y-%m-%d") for d in dates]
        }

    def run_walk_forward(
        self,
        df_prices: pd.DataFrame,
        signal_generator_factory: Callable[[pd.DataFrame], Callable[[pd.DataFrame, int], str]],
        train_window: int = 252,
        test_window: int = 63
    ) -> List[Dict[str, Any]]:
        """
        Walk-Forward doğrulama döngüsünü çalıştırır.
        Train penceresinde model eğitilir, test penceresinde sızıntısız çalıştırılır.
        Pencere test_window kadar kaydırılarak devam eder.
        """
        df = df_prices.sort_values('timestamp').reset_index(drop=True)
        n_rows = len(df)
        
        steps = []
        start_idx = train_window
        step_count = 0
        
        while start_idx + test_window <= n_rows:
            train_slice = df.iloc[start_idx - train_window : start_idx]
            test_slice = df.iloc[start_idx : start_idx + test_window]
            
            signal_generator = signal_generator_factory(train_slice)
            test_res = self.run_backtest(test_slice, signal_generator)
            
            steps.append({
                "step": step_count,
                "train_range": f"{train_slice['timestamp'].iloc[0].strftime('%Y-%m-%d')} - {train_slice['timestamp'].iloc[-1].strftime('%Y-%m-%d')}",
                "test_range": f"{test_slice['timestamp'].iloc[0].strftime('%Y-%m-%d')} - {test_slice['timestamp'].iloc[-1].strftime('%Y-%m-%d')}",
                "metrics": {
                    "total_return": test_res.get("total_return", 0.0),
                    "max_drawdown": test_res.get("max_drawdown", 0.0),
                    "trades_count": test_res.get("trades_count", 0),
                    "sharpe": test_res.get("sharpe", 0.0)
                }
            })
            
            start_idx += test_window
            step_count += 1
            
        return steps
