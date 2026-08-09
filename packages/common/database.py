import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from packages.common.config import settings

logger = logging.getLogger("axonforge.database")

# Özel Veritabanı Ekişilemez Hatası
class DatabaseUnavailableException(Exception):
    """Veritabanı bağlantısı kurulamadığında fırlatılan özel hata."""
    def __init__(self, message: str = "DATABASE_UNAVAILABLE: PostgreSQL veritabanına erişilemiyor."):
        self.message = message
        super().__init__(self.message)

# Veritabanı bağlantı motorunun oluşturulması (Sadece PostgreSQL)
if not settings.DATABASE_URL.startswith("postgresql"):
    # Hata fırlatarak SQLite veya başka bir veritabanının kullanılmasını engelliyoruz
    raise ValueError("HATA: AxonForge sadece PostgreSQL veritabanını destekler.")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Her sorgudan önce bağlantı durumunu kontrol eder
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def check_db_connection() -> bool:
    """Veritabanı bağlantısını test eder, başarısız olursa DatabaseUnavailableException fırlatır."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except (OperationalError, Exception) as e:
        logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
        raise DatabaseUnavailableException()

def get_db():
    """FastAPI için veritabanı oturum bağımlılığı (dependency)."""
    # Her istek öncesi veritabanı bağlantısını doğrula
    check_db_connection()
    
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        logger.error(f"Veritabanı oturum hatası: {str(e)}")
        raise DatabaseUnavailableException()
    finally:
        db.close()
