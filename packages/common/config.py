import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Sistem Ayarları
    TIMEZONE: str = Field(default="Europe/Istanbul")
    LOG_LEVEL: str = Field(default="INFO")
    DEFAULT_CURRENCY: str = Field(default="TRY")
    AUTO_TRADING: bool = Field(default=False)
    CORS_ALLOWED_ORIGINS: str = Field(default="*")

    # Veritabanı Ayarları

    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/axonforge")

    # Önbellek & Görev Kuyruğu
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Yapay Zeka Ajanı (LLM) Ayarları
    LLM_PROVIDER: str = Field(default="ollama")
    LLM_MODEL: str = Field(default="qwen2.5:14b-instruct")
    OLLAMA_HOST: str = Field(default="http://localhost:11434")

    # Dış Yapay Zeka Sağlayıcıları
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)

    # Finansal Veri Sağlayıcıları Anahtarları
    POLYGON_API_KEY: Optional[str] = Field(default=None)
    TWELVEDATA_API_KEY: Optional[str] = Field(default=None)
    ALPHAVANTAGE_API_KEY: Optional[str] = Field(default=None)
    BIST_PROVIDER_API_KEY: Optional[str] = Field(default=None)
    FRED_API_KEY: Optional[str] = Field(default=None)
    EVDS_API_KEY: Optional[str] = Field(default=None)

    # Aracı Kurum Entegrasyonları
    BROKER_PROVIDER: str = Field(default="paper")
    IB_API_HOST: str = Field(default="127.0.0.1")
    IB_API_PORT: int = Field(default=7497)
    IB_CLIENT_ID: int = Field(default=1)

    # Risk Gate Limitleri
    MAX_POSITION_SIZE_PCT: float = Field(default=0.10)
    MAX_DAILY_LOSS_LIMIT: float = Field(default=50000.0)
    MAX_PORTFOLIO_EXPOSURE_PCT: float = Field(default=0.80)
    DATA_FRESHNESS_LIMIT_SECONDS: int = Field(default=900)

    # Pydantic Settings Yapılandırması
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton Ayarlar Nesnesi
settings = Settings()
