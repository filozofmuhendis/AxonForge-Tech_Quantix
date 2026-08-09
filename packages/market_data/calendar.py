from datetime import datetime, time, date, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, Set

# BIST Resmi Tatil Günleri Tanımlamaları
BIST_HOLIDAYS = {
    date(2026, 1, 1),   # Yılbaşı
    date(2026, 4, 23),  # Ulusal Egemenlik ve Çocuk Bayramı
    date(2026, 5, 1),   # Emek ve Dayanışma Günü
    date(2026, 5, 19),  # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    date(2026, 7, 15),  # Demokrasi ve Milli Birlik Günü
    date(2026, 8, 30),  # Zafer Bayramı
    date(2026, 10, 29), # Cumhuriyet Bayramı
}

# BIST Yarım Gün Seansları (Arife Günleri vb.)
BIST_HALF_DAYS = {
    date(2026, 10, 28), # Cumhuriyet Bayramı Arifesi
}

# US Resmi Tatil Günleri Tanımlamaları
US_HOLIDAYS = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Washington's Birthday (Presidents' Day)
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth National Independence Day
    date(2026, 7, 4),   # Independence Day
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving Day
    date(2026, 12, 25), # Christmas Day
}

# US Yarım Gün Seansları (Thanksgiving Cuma vb. - Kapanış 13:00 EST)
US_HALF_DAYS = {
    date(2026, 11, 27), # Day after Thanksgiving
    date(2026, 12, 24), # Christmas Eve
}

# LSE (Londra) Tatil Günleri Tanımlamaları
LSE_HOLIDAYS = {
    date(2026, 1, 1),   # New Year's Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 6),   # Easter Monday
    date(2026, 5, 4),   # Early May Bank Holiday
    date(2026, 5, 25),  # Spring Bank Holiday
    date(2026, 8, 31),  # Summer Bank Holiday
    date(2026, 12, 25), # Christmas Day
    date(2026, 12, 26), # Boxing Day
}


class MarketCalendar:
    """BIST, ABD Borsaları, Londra (LSE) ve FX pazarları için seans ve tatil kontrol modülü."""
    
    def __init__(self, market_name: str):
        self.market_name = market_name.upper()
        
        if self.market_name == "BIST":
            self.tz = ZoneInfo("Europe/Istanbul")
            self.open_time = time(10, 0)
            self.close_time = time(18, 0)
            self.half_day_close = time(13, 0)
            self.holidays = BIST_HOLIDAYS
            self.half_days = BIST_HALF_DAYS
            self.is_continuous_24h = False
            
        elif self.market_name in ["NASDAQ", "NYSE", "US"]:
            self.tz = ZoneInfo("America/New_York")
            self.open_time = time(9, 30)
            self.close_time = time(16, 0)
            self.half_day_close = time(13, 0)
            self.holidays = US_HOLIDAYS
            self.half_days = US_HALF_DAYS
            self.is_continuous_24h = False
            
        elif self.market_name in ["LSE", "LONDON"]:
            self.tz = ZoneInfo("Europe/London")
            self.open_time = time(8, 0)
            self.close_time = time(16, 30)
            self.half_day_close = time(12, 30)
            self.holidays = LSE_HOLIDAYS
            self.half_days = set()
            self.is_continuous_24h = False
            
        elif self.market_name in ["FX", "FOREX", "CURRENCY"]:
            self.tz = ZoneInfo("America/New_York") # FX piyasaları pazar 17:00 EST - cuma 17:00 EST arası 24 saat açıktır.
            self.open_time = time(17, 0) # Pazar açılış saati
            self.close_time = time(17, 0) # Cuma kapanış saati
            self.holidays = {date(2026, 1, 1), date(2026, 12, 25)} # Yılbaşı ve Noel'de FX kapalıdır
            self.half_days = set()
            self.is_continuous_24h = True
            
        else:
            # Varsayılan genel piyasa
            self.tz = ZoneInfo("UTC")
            self.open_time = time(0, 0)
            self.close_time = time(23, 59, 59)
            self.half_day_close = time(12, 0)
            self.holidays = set()
            self.half_days = set()
            self.is_continuous_24h = True

    def get_market_time(self, utc_dt: datetime) -> datetime:
        """UTC zamanını piyasanın yerel saatine çevirir."""
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
        return utc_dt.astimezone(self.tz)

    def is_trading_day(self, check_date: date) -> bool:
        """Tarihin hafta sonu veya resmi tatil olmadığını kontrol eder."""
        if self.market_name in ["FX", "FOREX", "CURRENCY"]:
            # FX hafta sonu pazar 17:00 öncesi ve cumartesi gün boyu kapalıdır.
            # Günlük bazda cumartesi tamamen kapalı sayılır.
            if check_date.weekday() == 5: # Cumartesi
                return False
            if check_date in self.holidays:
                return False
            return True
            
        if check_date.weekday() >= 5: # Cumartesi & Pazar
            return False
        if check_date in self.holidays:
            return False
        return True

    def is_market_open(self, utc_dt: datetime) -> bool:
        """Piyasanın verilen UTC zamanında açık olup olmadığını kontrol eder."""
        local_dt = self.get_market_time(utc_dt)
        local_date = local_dt.date()
        local_time = local_dt.time()
        
        # FX 24 Saatlik seans kontrolü
        if self.is_continuous_24h:
            # Yılbaşı ve Noel tatil günü ise kapalı
            if local_date in self.holidays:
                return False
                
            # Cumartesi kapalı
            if local_date.weekday() == 5:
                return False
                
            # Pazar günü seans 17:00 EST'den sonra açılır
            if local_date.weekday() == 6:
                return local_time >= self.open_time
                
            # Cuma günü seans 17:00 EST'de kapanır
            if local_date.weekday() == 4:
                return local_time < self.close_time
                
            # Diğer günler (Pazartesi, Salı, Çarşamba, Perşembe) 24 saat açıktır
            return True
            
        # Standart Hisse Senedi seans kontrolleri
        if not self.is_trading_day(local_date):
            return False
            
        # Yarım gün seans kontrolü
        if local_date in self.half_days:
            return self.open_time <= local_time <= self.half_day_close
            
        return self.open_time <= local_time <= self.close_time

    def get_market_state(self, utc_dt: datetime) -> str:
        """Piyasanın durumunu döndürür: ACIK, KAPALI, HAFTASONU, TATIL, YARIMGUN."""
        local_dt = self.get_market_time(utc_dt)
        local_date = local_dt.date()
        local_time = local_dt.time()
        
        if self.is_market_open(utc_dt):
            return "ACIK"
            
        if self.is_continuous_24h:
            if local_date.weekday() == 5 or (local_date.weekday() == 6 and local_time < self.open_time):
                return "HAFTASONU"
            if local_date in self.holidays:
                return "TATIL"
            return "KAPALI"

        if local_date.weekday() >= 5:
            return "HAFTASONU"
        if local_date in self.holidays:
            return "TATIL"
        if local_date in self.half_days:
            return "YARIMGUN_KAPALI" if local_time > self.half_day_close else "ACIK"
            
        if local_time < self.open_time:
            return "KAPALI_ACILIS_ONCESI"
        else:
            return "KAPALI_KAPANIS_SONRASI"

    def get_session_info(self, utc_dt: datetime) -> Dict[str, Any]:
        """Piyasa seansı hakkında detaylı bilgi döndürür."""
        local_dt = self.get_market_time(utc_dt)
        return {
            "piyasa": self.market_name,
            "yerel_saat": local_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "durum": self.get_market_state(utc_dt),
            "islem_gunu_mu": self.is_trading_day(local_dt.date()),
            "acik_mi": self.is_market_open(utc_dt)
        }
