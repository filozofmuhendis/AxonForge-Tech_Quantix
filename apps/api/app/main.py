import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from packages.common.database import DatabaseUnavailableException, check_db_connection
from packages.ai_agent.agent import AIAgentUnavailableException
from packages.common.config import settings

# Günlük kayıtları yapılandırması
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("axonforge.api")

app = FastAPI(
    title="AxonForge FinTech AI API",
    description="Kişisel finansal zeka, nicel analiz ve portföy risk yönetim platformu API servisi.",
    version="1.0",
    docs_url="/docs"
)

# CORS Ayarları
allowed_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
allow_all = "*" in allowed_origins or not allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if allow_all else allowed_origins,
    allow_origin_regex=".*" if allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# 1. Hata Yakalama Katmanları (Exception Handlers) - Tam Türkçe Mesajlar

@app.exception_handler(DatabaseUnavailableException)
async def database_unavailable_exception_handler(request: Request, exc: DatabaseUnavailableException):
    logger.error("API Hatası: Veritabanı bağlantısı kurulamadı.")
    return JSONResponse(
        status_code=503,
        content={
            "hata_kodu": "DATABASE_UNAVAILABLE",
            "detay": "DATABASE_UNAVAILABLE",
            "mesaj": "Veritabanı bağlantısı kurulamadı. Lütfen PostgreSQL veritabanının çalıştığından emin olun."
        }
    )

@app.exception_handler(AIAgentUnavailableException)
async def ai_agent_unavailable_exception_handler(request: Request, exc: AIAgentUnavailableException):
    logger.error("API Hatası: Yapay Zeka Ajanı (LLM) çevrimdışı.")
    return JSONResponse(
        status_code=503,
        content={
            "hata_kodu": "AI_AGENT_UNAVAILABLE",
            "detay": "AI_AGENT_UNAVAILABLE",
            "mesaj": "Yapay Zeka Ajanı (LLM) servislerine erişilemiyor. Lütfen Ollama sunucusunu veya harici API anahtarlarını kontrol edin."
        }
    )

@app.on_event("startup")
async def startup_event():
    logger.info("AxonForge API başlatılıyor...")
    try:
        check_db_connection()
        logger.info("PostgreSQL veritabanı bağlantısı başarılı.")
    except DatabaseUnavailableException:
        logger.critical("UYARI: Başlangıçta veritabanına erişilemedi! Sistem çalışmaya devam edecek ancak DB sorguları hata döndürecektir.")

# Routers import & mount (Bir sonraki adımda oluşturulacak)
from apps.api.app.api.router import api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    """Sistem bileşenlerinin sağlık durumunu döndürür."""
    db_status = "ONLINE"
    ai_status = "ONLINE"
    
    try:
        check_db_connection()
    except Exception:
        db_status = "OFFLINE"
        
    try:
        from packages.ai_agent.agent import FinancialAIAgent
        agent = FinancialAIAgent()
        agent.check_llm_health()
    except Exception:
        ai_status = "UNAVAILABLE"
        
    return {
        "status": "ONLINE",
        "veritabanı": db_status,
        "yapay_zeka_ajani": ai_status,
        "version": "1.0"
    }

@app.get("/ready")
def readiness_check():
    """DB ve Redis hazır olma (readiness) durumunu doğrular."""
    db_status = "ONLINE"
    redis_status = "ONLINE"
    
    try:
        check_db_connection()
    except Exception:
        db_status = "OFFLINE"
        
    try:
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1)
        r.ping()
    except Exception:
        redis_status = "OFFLINE"
        
    if db_status == "OFFLINE" or redis_status == "OFFLINE":
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "details": {
                    "database": db_status,
                    "redis": redis_status
                }
            }
        )
        
    return {
        "ready": True,
        "details": {
            "database": db_status,
            "redis": redis_status
        }
    }

