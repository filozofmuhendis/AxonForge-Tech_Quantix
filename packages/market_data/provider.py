import time
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import pandas as pd
import yfinance as yf

from packages.common.config import settings

logger = logging.getLogger("axonforge.market_data.provider")

class DataProviderUnavailableException(Exception):
    """Veri sağlayıcısı çevrimdışı veya yetersiz olduğunda fırlatılan istisna."""
    pass

class MarketDataProvider:
    """Finansal veri sağlayıcıları için soyut taban sınıf."""
    
    def get_provider_name(self) -> str:
        raise NotImplementedError

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Günlük bar verilerini çeker."""
        raise NotImplementedError

    def fetch_intraday_bars(self, symbol: str, interval: str = "5m") -> List[Dict[str, Any]]:
        """Gün içi bar verilerini çeker."""
        raise NotImplementedError

    def fetch_fundamental_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Şirket temel analiz finansal özet verilerini çeker."""
        raise NotImplementedError


class YahooProvider(MarketDataProvider):
    """Yahoo Finance kullanarak veri çeken sağlayıcı sınıf."""
    
    def get_provider_name(self) -> str:
        return "YahooFinance"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        start_time = time.time()
        logger.info(f"YahooFinance: {symbol} günlük barlar çekiliyor ({start_date} - {end_date})...")
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            latency_ms = int((time.time() - start_time) * 1000)
            if df.empty:
                return []
            bars = []
            now_utc = datetime.now(timezone.utc)
            for idx, row in df.iterrows():
                timestamp = idx.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                try:
                    open_val = float(row['Open'].iloc[0]) if isinstance(row['Open'], pd.Series) else float(row['Open'])
                    high_val = float(row['High'].iloc[0]) if isinstance(row['High'], pd.Series) else float(row['High'])
                    low_val = float(row['Low'].iloc[0]) if isinstance(row['Low'], pd.Series) else float(row['Low'])
                    close_val = float(row['Close'].iloc[0]) if isinstance(row['Close'], pd.Series) else float(row['Close'])
                    volume_val = float(row['Volume'].iloc[0]) if isinstance(row['Volume'], pd.Series) else float(row['Volume'])
                    adj_close_val = float(row['Adj Close'].iloc[0]) if isinstance(row['Adj Close'], pd.Series) else float(row['Adj Close'])
                except (AttributeError, KeyError):
                    open_val = float(row['Open'])
                    high_val = float(row['High'])
                    low_val = float(row['Low'])
                    close_val = float(row['Close'])
                    volume_val = float(row['Volume'])
                    adj_close_val = float(row['Adj Close']) if 'Adj Close' in row else close_val
                
                freshness_seconds = int((now_utc - timestamp).total_seconds())
                bars.append({
                    "timestamp": timestamp,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "volume": volume_val,
                    "adj_close": adj_close_val,
                    "provider_name": self.get_provider_name(),
                    "fetched_at": now_utc,
                    "latency_ms": latency_ms,
                    "freshness_seconds": freshness_seconds,
                    "data_quality_score": 100.0
                })
            return bars
        except Exception as e:
            logger.error(f"YahooFinance günlük veri çekme hatası ({symbol}): {str(e)}")
            return []

    def fetch_intraday_bars(self, symbol: str, interval: str = "5m") -> List[Dict[str, Any]]:
        start_time = time.time()
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval=interval)
            latency_ms = int((time.time() - start_time) * 1000)
            if df.empty:
                return []
            bars = []
            now_utc = datetime.now(timezone.utc)
            for idx, row in df.iterrows():
                timestamp = idx.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = timestamp.astimezone(timezone.utc)
                freshness_seconds = int((now_utc - timestamp).total_seconds())
                bars.append({
                    "timestamp": timestamp,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": float(row['Volume']),
                    "provider_name": self.get_provider_name(),
                    "fetched_at": now_utc,
                    "latency_ms": latency_ms,
                    "freshness_seconds": freshness_seconds,
                    "data_quality_score": 100.0
                })
            return bars
        except Exception as e:
            logger.error(f"YahooFinance intraday hatası ({symbol}): {str(e)}")
            return []

    def fetch_fundamental_snapshot(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            snapshot = {
                "Revenue": info.get("totalRevenue"),
                "Revenue Growth": info.get("revenueGrowth"),
                "Gross Profit": info.get("grossProfits"),
                "Operating Income": info.get("operatingIncome") or info.get("operatingCashflow"),
                "Net Income": info.get("netIncomeToCommon"),
                "EPS": info.get("trailingEps"),
                "Free Cash Flow": info.get("freeCashflow"),
                "Total Debt": info.get("totalDebt"),
                "Cash": info.get("totalCash"),
                "Equity": info.get("bookValue"),
                "ROE": info.get("returnOnEquity"),
                "ROA": info.get("returnOnAssets"),
                "Margins": info.get("profitMargins"),
                "P/E": info.get("trailingPE"),
                "P/B": info.get("priceToBook"),
                "EV/EBITDA": info.get("enterpriseToEbitda"),
                "EV/Sales": info.get("enterpriseToRevenue"),
                "Dividend Yield": info.get("dividendYield"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country", "US")
            }
            return {k: (v if v is not None else 0.0) for k, v in snapshot.items()}
        except Exception as e:
            logger.error(f"YahooFinance temel veri hatası ({symbol}): {str(e)}")
            return {}


class TwelveDataProvider(MarketDataProvider):
    """Twelve Data API kullanan veri sağlayıcı."""
    
    def get_provider_name(self) -> str:
        return "TwelveData"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        api_key = settings.MARKET_DATA_API_KEY
        if not api_key or settings.MARKET_DATA_PROVIDER != "twelve_data":
            logger.debug("TwelveData kimlik bilgileri eksik veya devre dışı.")
            return []
            
        start_time = time.time()
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&start_date={start_date}&end_date={end_date}&apikey={api_key}"
        try:
            res = requests.get(url, timeout=10)
            latency_ms = int((time.time() - start_time) * 1000)
            data = res.json()
            if "values" not in data:
                logger.warning(f"TwelveData hata döndü: {data.get('message', 'Bilinmeyen Hata')}")
                return []
            
            bars = []
            now_utc = datetime.now(timezone.utc)
            for item in data["values"]:
                dt = datetime.strptime(item["datetime"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                bars.append({
                    "timestamp": dt,
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(item.get("volume", 0)),
                    "provider_name": self.get_provider_name(),
                    "fetched_at": now_utc,
                    "latency_ms": latency_ms,
                    "freshness_seconds": int((now_utc - dt).total_seconds()),
                    "data_quality_score": 100.0
                })
            return bars
        except Exception as e:
            logger.error(f"TwelveData hata ({symbol}): {str(e)}")
            return []

    def fetch_intraday_bars(self, symbol: str, interval: str = "5m") -> List[Dict[str, Any]]:
        api_key = settings.MARKET_DATA_API_KEY
        if not api_key or settings.MARKET_DATA_PROVIDER != "twelve_data":
            return []
        # Benzer istek yapısı gün içi için kurulabilir
        return []


class FinnhubProvider(MarketDataProvider):
    """Finnhub API kullanan veri sağlayıcı (CREDENTIAL REQUIRED)."""
    def get_provider_name(self) -> str:
        return "Finnhub"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        # Ücretsiz Finnhub API Key çevre değişkenlerinde tanımlı olmalıdır
        return []


class PolygonProvider(MarketDataProvider):
    """Polygon.io API kullanan veri sağlayıcı (CREDENTIAL REQUIRED)."""
    def get_provider_name(self) -> str:
        return "Polygon"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return []


class StooqProvider(MarketDataProvider):
    """Stooq CSV indirme altyapısı (EOD fallback)."""
    def get_provider_name(self) -> str:
        return "Stooq"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return []


class BISTProvider(MarketDataProvider):
    """BIST verilerini almak için özel sarmalayıcı (BIST EOD verisi)."""
    def get_provider_name(self) -> str:
        return "BISTProvider"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        # BIST için Yahoo Finance'e fallback yap (varsayılan)
        yp = YahooProvider()
        return yp.fetch_daily_bars(symbol, start_date, end_date)


class SECProvider(MarketDataProvider):
    """SEC EDGAR üzerinden ABD şirket finansallarını alan sağlayıcı."""
    def get_provider_name(self) -> str:
        return "SEC_EDGAR"


class KAPProvider(MarketDataProvider):
    """KAP bildirimlerini çeken veri sağlayıcı."""
    def get_provider_name(self) -> str:
        return "KAP"


class FREDProvider(MarketDataProvider):
    """FRED API (US Macro data) entegrasyonu."""
    def get_provider_name(self) -> str:
        return "FRED"


class TCMBProvider(MarketDataProvider):
    """TCMB EVDS API (TR Macro data) entegrasyonu."""
    def get_provider_name(self) -> str:
        return "TCMB"


class ECBProvider(MarketDataProvider):
    """Avrupa Merkez Bankası API entegrasyonu."""
    def get_provider_name(self) -> str:
        return "ECB"


class ProviderRouter:
    """Sağlayıcı önceliklerini yöneten ve otomatik failover yapan yönlendirici."""
    
    def __init__(self):
        self.providers = {
            "yahoo": YahooProvider(),
            "twelve_data": TwelveDataProvider(),
            "finnhub": FinnhubProvider(),
            "polygon": PolygonProvider(),
            "stooq": StooqProvider(),
            "bist": BISTProvider(),
            "fred": FREDProvider(),
            "tcmb": TCMBProvider(),
            "ecb": ECBProvider()
        }
        
        # Pazar/Varlık türüne göre öncelik yapılandırması
        self.routing_rules = {
            "BIST": ["bist", "yahoo"],
            "US_EQUITY": ["twelve_data", "yahoo", "polygon"],
            "FX": ["twelve_data", "yahoo", "ecb"],
            "COMMODITY": ["fred", "yahoo"],
            "MACRO_US": ["fred"],
            "MACRO_TR": ["tcmb"]
        }

    def _determine_asset_class(self, symbol: str) -> str:
        if symbol.endswith(".IS"):
            return "BIST"
        elif "=X" in symbol or len(symbol) == 6: # FX çiftleri (örn: EURUSD veya USDTRY=X)
            return "FX"
        elif symbol in ["GC=F", "CL=F", "HG=F"]: # Altın, Petrol, Bakır
            return "COMMODITY"
        else:
            return "US_EQUITY"

    def fetch_daily_bars(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        asset_class = self._determine_asset_class(symbol)
        priorities = self.routing_rules.get(asset_class, ["yahoo"])
        
        logger.info(f"Router: {symbol} ({asset_class}) için yönlendirme sıralaması: {priorities}")
        
        for provider_key in priorities:
            provider = self.providers.get(provider_key)
            if not provider:
                continue
                
            try:
                bars = provider.fetch_daily_bars(symbol, start_date, end_date)
                if bars:
                    logger.info(f"Router: {symbol} verisi '{provider.get_provider_name()}' üzerinden çekildi.")
                    return bars
            except Exception as e:
                logger.warning(f"Router: '{provider_key}' sağlayıcısı başarısız oldu: {str(e)}. Fallback'e geçiliyor.")
                continue
                
        # Eğer hiçbir sağlayıcı veri dönemediyse hata fırlat
        logger.error(f"Router: {symbol} için aktif hiçbir veri sağlayıcısından veri alınamadı.")
        raise DataProviderUnavailableException("DATA_PROVIDER_UNAVAILABLE")

    def fetch_fundamental_snapshot(self, symbol: str) -> Dict[str, Any]:
        # Temel veriler için de benzer bir fallback döngüsü kurulabilir
        yp = YahooProvider()
        res = yp.fetch_fundamental_snapshot(symbol)
        if not res:
            raise DataProviderUnavailableException("DATA_PROVIDER_UNAVAILABLE")
        return res
