import logging
import sys
from workers.market_data_worker import run_market_data_worker
from workers.news_worker import run_news_worker
from workers.feature_worker import run_feature_worker
from workers.prediction_worker import run_prediction_worker
from workers.maintenance_worker import run_maintenance_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("axonforge.workers_runner")

def run_all_workers():
    logger.info("========================================")
    logger.info("AXONFORGE ARKA PLAN GÖREVLERİ BAŞLATILIYOR")
    logger.info("========================================")
    
    logger.info("Adım 1: Güncel Piyasa Fiyatları Çekiliyor...")
    run_market_data_worker()
    
    logger.info("Adım 2: Güncel Haberler ve Duygu Analizleri Alınıyor...")
    run_news_worker()
    
    logger.info("Adım 3: Makine Öğrenimi Öznitelikleri (Features) Güncelleniyor...")
    run_feature_worker()
    
    logger.info("Adım 4: Yapay Zeka Yön Olasılığı Tahminleri Koşturuluyor...")
    run_prediction_worker()
    
    logger.info("Adım 5: Model Kalibrasyonları ve Bakım İşlemleri Yapılıyor...")
    run_maintenance_worker()
    
    logger.info("========================================")
    logger.info("TÜM ARKA PLAN GÖREVLERİ BAŞARIYLA TAMAMLANDI")
    logger.info("========================================")

if __name__ == "__main__":
    run_all_workers()
